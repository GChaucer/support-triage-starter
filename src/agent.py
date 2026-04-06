from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from uuid import uuid4

from src.escalation import detect_language_escalation, team_for_issue
from src.schemas import (
    ConfidenceLevel,
    EscalationPayload,
    FieldsCollected,
    FinalResponse,
    FollowUpResponse,
    FollowUpState,
    IssueType,
    ResolutionStatus,
    SessionOutput,
    TriageRequest,
    TriageResponse,
)
from src.tools import (
    ToolError,
    create_support_ticket,
    lookup_customer_record,
    lookup_order_status,
    route_to_human_queue,
)


LOGGER = logging.getLogger(__name__)
EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w+")
ORDER_RE = re.compile(r"\b(ord_[a-z0-9]+)\b", re.IGNORECASE)
CHARGE_RE = re.compile(r"\b(ch_[a-z0-9]+)\b", re.IGNORECASE)
CUSTOMER_RE = re.compile(r"\b(cust_[a-z0-9]+)\b", re.IGNORECASE)


class TriageAgent:
    def handle(self, request: TriageRequest) -> TriageResponse:
        session_id = request.session_id or str(uuid4())
        state = request.follow_up_state
        issue_type, confidence = self._classify(request.message, state)
        fields = self._extract_fields(request.message, state.fields_collected if state else None)
        email_identifier = self._extract_email(request.message)

        escalation_reason, escalation_priority, escalation_team = detect_language_escalation(request.message)
        if escalation_reason:
            return self._escalate(
                session_id=session_id,
                issue_type=issue_type,
                confidence=confidence,
                fields=fields,
                reason=escalation_reason,
                priority=escalation_priority,
                recommended_team=escalation_team,
                customer_response="I’m routing this to a human support specialist now so they can help directly.",
            )

        missing_field = self._required_missing_field(issue_type, fields, email_identifier)
        if missing_field:
            follow_up_count = 0 if state is None else state.follow_up_count
            if follow_up_count >= 1:
                return self._escalate(
                    session_id=session_id,
                    issue_type=issue_type,
                    confidence=confidence,
                    fields=fields,
                    reason="Missing required info after one follow-up",
                    priority="normal",
                    recommended_team=team_for_issue(issue_type),
                    customer_response="I’m escalating this to a human support specialist because I still need one required detail to finish triage.",
                )

            follow_up_state = FollowUpState(
                session_id=session_id,
                issue_type=issue_type,
                classification_confidence=confidence,
                fields_collected=fields,
                follow_up_count=1,
            )
            return FollowUpResponse(
                follow_up_question=self._follow_up_question(issue_type, missing_field),
                follow_up_state=follow_up_state,
            )

        if confidence == ConfidenceLevel.LOW or issue_type == IssueType.UNKNOWN:
            return self._escalate(
                session_id=session_id,
                issue_type=issue_type,
                confidence=confidence,
                fields=fields,
                reason="Low confidence",
                priority="normal",
                recommended_team=team_for_issue(issue_type),
                customer_response="I’m routing this to a human support specialist so they can review the details directly.",
            )

        try:
            if issue_type == IssueType.ORDER_NOT_RECEIVED:
                return self._resolve_order_not_received(session_id, confidence, fields)
            if issue_type == IssueType.DUPLICATE_CHARGE:
                return self._resolve_duplicate_charge(session_id, confidence, fields, email_identifier)
            return self._resolve_cancellation_request(session_id, confidence, fields, email_identifier)
        except ToolError:
            LOGGER.exception("tool failure during triage")
            return self._escalate(
                session_id=session_id,
                issue_type=issue_type,
                confidence=confidence,
                fields=fields,
                reason="Tool failure",
                priority="high",
                recommended_team=team_for_issue(issue_type),
                customer_response="I’m routing this to a human support specialist because I could not complete the lookup needed for triage.",
            )

    def _classify(
        self,
        message: str,
        state: FollowUpState | None,
    ) -> tuple[IssueType, ConfidenceLevel]:
        normalized = message.lower()

        if state is not None and state.issue_type != IssueType.UNKNOWN:
            return state.issue_type, state.classification_confidence

        if "cancel" in normalized or "cancellation" in normalized:
            return IssueType.CANCELLATION_REQUEST, ConfidenceLevel.HIGH
        if "charged twice" in normalized or "duplicate charge" in normalized or "double charged" in normalized:
            return IssueType.DUPLICATE_CHARGE, ConfidenceLevel.HIGH
        if "order" in normalized and any(phrase in normalized for phrase in ("not received", "hasn't arrived", "has not arrived")):
            return IssueType.ORDER_NOT_RECEIVED, ConfidenceLevel.HIGH
        if "where is my order" in normalized or "missing order" in normalized:
            return IssueType.ORDER_NOT_RECEIVED, ConfidenceLevel.MEDIUM
        if "charged" in normalized or "billing" in normalized:
            return IssueType.DUPLICATE_CHARGE, ConfidenceLevel.MEDIUM
        if "refund" in normalized:
            return IssueType.CANCELLATION_REQUEST, ConfidenceLevel.LOW
        return IssueType.UNKNOWN, ConfidenceLevel.LOW

    def _extract_email(self, message: str) -> str | None:
        email_match = EMAIL_RE.search(message)
        if not email_match:
            return None
        return email_match.group(0).lower()

    def _extract_fields(self, message: str, existing: FieldsCollected | None) -> FieldsCollected:
        fields = existing.model_copy() if existing else FieldsCollected()

        order_match = ORDER_RE.search(message)
        charge_match = CHARGE_RE.search(message)
        customer_match = CUSTOMER_RE.search(message)

        if customer_match:
            fields.customer_id = customer_match.group(1).lower()
        if order_match:
            fields.order_id = order_match.group(1).lower()
        if charge_match:
            fields.charge_id = charge_match.group(1).lower()

        return fields

    def _required_missing_field(
        self,
        issue_type: IssueType,
        fields: FieldsCollected,
        email_identifier: str | None,
    ) -> str | None:
        if issue_type == IssueType.ORDER_NOT_RECEIVED and not fields.order_id:
            return "order_id"
        if issue_type == IssueType.DUPLICATE_CHARGE and not (fields.customer_id or fields.charge_id or email_identifier):
            return "charge_lookup_identifier"
        if issue_type == IssueType.CANCELLATION_REQUEST and not (fields.customer_id or email_identifier):
            return "customer_id"
        return None

    def _follow_up_question(self, issue_type: IssueType, missing_field: str) -> str:
        if issue_type == IssueType.ORDER_NOT_RECEIVED:
            return "Please share the order ID so I can check the shipment status."
        if issue_type == IssueType.DUPLICATE_CHARGE:
            return "Please share either your customer ID, the charge ID, or the email used on the account so I can review the recent charges."
        return "Please share your customer ID or the email used on the account so I can place the cancellation request."

    def _lookup_customer_context(
        self,
        fields: FieldsCollected,
        email_identifier: str | None,
    ) -> tuple[FieldsCollected, dict | None]:
        if fields.customer_id:
            lookup_result = lookup_customer_record(fields.customer_id, "customer_id")
            return fields, lookup_result

        if email_identifier:
            lookup_result = lookup_customer_record(email_identifier, "email")
            if lookup_result["status"] == "found":
                fields = fields.model_copy(update={"customer_id": lookup_result["customer_id"]})
            return fields, lookup_result

        return fields, None

    def _charges_plausibly_indicate_duplicate(
        self,
        recent_charges: list[dict],
        charge_id: str | None,
    ) -> bool:
        if len(recent_charges) < 2:
            return False

        charge_groups: dict[tuple[str | None, str | None], list[dict]] = {}
        for charge in recent_charges:
            key = (charge.get("amount"), charge.get("posted_at"))
            charge_groups.setdefault(key, []).append(charge)

        for grouped_charges in charge_groups.values():
            if len(grouped_charges) < 2:
                continue
            if not charge_id:
                return True
            if any(charge.get("charge_id") == charge_id for charge in grouped_charges):
                return True

        return False

    def _resolve_order_not_received(
        self,
        session_id: str,
        confidence: ConfidenceLevel,
        fields: FieldsCollected,
    ) -> FinalResponse:
        tool_result = lookup_order_status(fields.order_id)
        if tool_result.get("status") == "not_found":
            return self._escalate(
                session_id=session_id,
                issue_type=IssueType.ORDER_NOT_RECEIVED,
                confidence=confidence,
                fields=fields,
                reason="Lookup ambiguity / insufficient evidence",
                priority="normal",
                recommended_team=team_for_issue(IssueType.ORDER_NOT_RECEIVED),
                customer_response="I’m escalating this to our fulfillment team because I could not confirm the order status from the order ID provided.",
                source_tool="lookup_order_status",
                source_result=tool_result,
            )

        if tool_result["fulfillment_status"] == "delivered":
            customer_response = (
                f"I checked order {fields.order_id}. It shows as delivered on {tool_result['delivered_at']}."
            )
        else:
            customer_response = (
                f"I checked order {fields.order_id}. It is currently {tool_result['fulfillment_status'].replace('_', ' ')}"
                f" and the estimated delivery is {tool_result['estimated_delivery']}."
            )
        return self._final_response(
            session_id=session_id,
            issue_type=IssueType.ORDER_NOT_RECEIVED,
            confidence=confidence,
            fields=fields,
            customer_response=customer_response,
            tool_called="lookup_order_status",
            tool_result=tool_result,
        )

    def _resolve_duplicate_charge(
        self,
        session_id: str,
        confidence: ConfidenceLevel,
        fields: FieldsCollected,
        email_identifier: str | None,
    ) -> FinalResponse:
        fields, customer_lookup = self._lookup_customer_context(fields, email_identifier)
        if customer_lookup and customer_lookup["status"] == "not_found":
            return self._escalate(
                session_id=session_id,
                issue_type=IssueType.DUPLICATE_CHARGE,
                confidence=confidence,
                fields=fields,
                reason="Lookup ambiguity / insufficient evidence",
                priority="high",
                recommended_team=team_for_issue(IssueType.DUPLICATE_CHARGE),
                customer_response="I’m escalating this to billing because I could not match the account details to a customer record.",
                source_tool="lookup_customer_record",
                source_result=customer_lookup,
            )

        recent_charges = customer_lookup["recent_charges"] if customer_lookup else []
        if not customer_lookup or not self._charges_plausibly_indicate_duplicate(recent_charges, fields.charge_id):
            return self._escalate(
                session_id=session_id,
                issue_type=IssueType.DUPLICATE_CHARGE,
                confidence=confidence,
                fields=fields,
                reason="Lookup ambiguity / insufficient evidence",
                priority="high",
                recommended_team=team_for_issue(IssueType.DUPLICATE_CHARGE),
                customer_response="I’m escalating this to billing because the charge evidence is incomplete or ambiguous.",
                source_tool="lookup_customer_record" if customer_lookup else None,
                source_result=customer_lookup,
            )

        ticket = create_support_ticket(
            issue_type=IssueType.DUPLICATE_CHARGE.value,
            customer_id=fields.customer_id,
            summary="Customer reported a possible duplicate charge. Review recent charges manually.",
            priority="high",
        )
        customer_response = (
            "I found charge activity that plausibly indicates a duplicate and opened a billing ticket for manual review."
            f" Your reference is {ticket['ticket_id']}."
        )
        return self._final_response(
            session_id=session_id,
            issue_type=IssueType.DUPLICATE_CHARGE,
            confidence=confidence,
            fields=fields,
            customer_response=customer_response,
            tool_called="create_support_ticket",
            tool_result=ticket,
        )

    def _resolve_cancellation_request(
        self,
        session_id: str,
        confidence: ConfidenceLevel,
        fields: FieldsCollected,
        email_identifier: str | None,
    ) -> FinalResponse:
        fields, customer_lookup = self._lookup_customer_context(fields, email_identifier)
        if not customer_lookup or customer_lookup["status"] == "not_found":
            return self._escalate(
                session_id=session_id,
                issue_type=IssueType.CANCELLATION_REQUEST,
                confidence=confidence,
                fields=fields,
                reason="Lookup ambiguity / insufficient evidence",
                priority="normal",
                recommended_team=team_for_issue(IssueType.CANCELLATION_REQUEST),
                customer_response="I’m escalating this to the support team because I could not confirm the account details needed to place the cancellation request.",
                source_tool="lookup_customer_record" if customer_lookup else None,
                source_result=customer_lookup,
            )

        ticket = create_support_ticket(
            issue_type=IssueType.CANCELLATION_REQUEST.value,
            customer_id=fields.customer_id,
            summary="Customer requested cancellation.",
            priority="normal",
        )
        customer_response = (
            "I created a cancellation support ticket so the team can process your request."
            f" Your reference is {ticket['ticket_id']}."
        )
        return self._final_response(
            session_id=session_id,
            issue_type=IssueType.CANCELLATION_REQUEST,
            confidence=confidence,
            fields=fields,
            customer_response=customer_response,
            tool_called="create_support_ticket",
            tool_result=ticket,
        )

    def _escalate(
        self,
        *,
        session_id: str,
        issue_type: IssueType,
        confidence: ConfidenceLevel,
        fields: FieldsCollected,
        reason: str,
        priority: str,
        recommended_team,
        customer_response: str,
        source_tool: str | None = None,
        source_result: dict | None = None,
    ) -> FinalResponse:
        route_context = {
            "session_id": session_id,
            "issue_type": issue_type.value,
            "recommended_team": recommended_team.value if recommended_team else None,
            "fields": fields.model_dump(),
        }
        if source_tool:
            route_context["source_tool"] = source_tool
        if source_result:
            route_context["source_result"] = source_result

        queue_result = route_to_human_queue(
            reason=reason,
            priority=priority,
            context=route_context,
        )

        output = SessionOutput(
            session_id=session_id,
            timestamp=datetime.now(timezone.utc),
            issue_type=issue_type,
            classification_confidence=confidence,
            fields_collected=fields,
            tool_called="route_to_human_queue",
            tool_result=queue_result,
            resolution_status=ResolutionStatus.ESCALATED,
            customer_response=customer_response,
            escalation=EscalationPayload(
                triggered=True,
                reason=reason,
                recommended_team=recommended_team,
                summary=f"Escalated {issue_type.value} to {recommended_team.value if recommended_team else 'general'} due to {reason.lower()}.",
            ),
        )
        LOGGER.info(
            "session=%s resolution=%s issue=%s reason=%s",
            session_id,
            output.resolution_status.value,
            issue_type.value,
            reason,
        )
        return FinalResponse(session_output=output)

    def _final_response(
        self,
        *,
        session_id: str,
        issue_type: IssueType,
        confidence: ConfidenceLevel,
        fields: FieldsCollected,
        customer_response: str,
        tool_called: str,
        tool_result: dict,
    ) -> FinalResponse:
        output = SessionOutput(
            session_id=session_id,
            timestamp=datetime.now(timezone.utc),
            issue_type=issue_type,
            classification_confidence=confidence,
            fields_collected=fields,
            tool_called=tool_called,
            tool_result=tool_result,
            resolution_status=ResolutionStatus.RESOLVED,
            customer_response=customer_response,
            escalation=EscalationPayload(
                triggered=False,
                reason=None,
                recommended_team=None,
                summary=None,
            ),
        )
        LOGGER.info("session=%s resolution=%s issue=%s", session_id, output.resolution_status.value, issue_type.value)
        return FinalResponse(session_output=output)
