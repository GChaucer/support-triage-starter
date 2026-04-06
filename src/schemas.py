from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IssueType(str, Enum):
    ORDER_NOT_RECEIVED = "order_not_received"
    DUPLICATE_CHARGE = "duplicate_charge"
    CANCELLATION_REQUEST = "cancellation_request"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class RecommendedTeam(str, Enum):
    BILLING = "billing"
    FULFILLMENT = "fulfillment"
    GENERAL = "general"


class FieldsCollected(BaseModel):
    customer_id: str | None = None
    order_id: str | None = None
    charge_id: str | None = None


class EscalationPayload(BaseModel):
    triggered: bool
    reason: str | None = None
    recommended_team: RecommendedTeam | None = None
    summary: str | None = None


class SessionOutput(BaseModel):
    session_id: str
    timestamp: datetime
    issue_type: IssueType
    classification_confidence: ConfidenceLevel
    fields_collected: FieldsCollected
    tool_called: str
    tool_result: dict[str, Any]
    resolution_status: ResolutionStatus
    customer_response: str
    escalation: EscalationPayload


class FollowUpState(BaseModel):
    session_id: str
    issue_type: IssueType
    classification_confidence: ConfidenceLevel
    fields_collected: FieldsCollected
    follow_up_count: int = 0


class TriageRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None
    follow_up_state: FollowUpState | None = None


class FollowUpResponse(BaseModel):
    needs_follow_up: bool = True
    follow_up_question: str
    follow_up_state: FollowUpState
    session_output: None = None


class FinalResponse(BaseModel):
    needs_follow_up: bool = False
    follow_up_question: None = None
    follow_up_state: None = None
    session_output: SessionOutput


TriageResponse = FollowUpResponse | FinalResponse
