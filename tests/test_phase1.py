import unittest

from src.agent import TriageAgent
from src.schemas import FinalResponse, FollowUpResponse, TriageRequest


class Phase1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = TriageAgent()

    def test_requests_follow_up_then_escalates_when_order_id_still_missing(self) -> None:
        first = self.agent.handle(TriageRequest(message="My order has not arrived."))
        self.assertIsInstance(first, FollowUpResponse)
        self.assertIn("order ID", first.follow_up_question)

        second = self.agent.handle(
            TriageRequest(
                message="I still do not have it.",
                session_id=first.follow_up_state.session_id,
                follow_up_state=first.follow_up_state,
            )
        )
        self.assertIsInstance(second, FinalResponse)
        self.assertEqual(second.session_output.resolution_status.value, "escalated")
        self.assertEqual(second.session_output.tool_called, "route_to_human_queue")
        self.assertEqual(second.session_output.escalation.reason, "Missing required info after one follow-up")

    def test_duplicate_charge_ambiguity_routes_to_human_queue(self) -> None:
        response = self.agent.handle(
            TriageRequest(message="I was charged twice on bob@example.com and need help.")
        )
        self.assertIsInstance(response, FinalResponse)
        self.assertEqual(response.session_output.issue_type.value, "duplicate_charge")
        self.assertEqual(response.session_output.resolution_status.value, "escalated")
        self.assertEqual(response.session_output.escalation.reason, "Lookup ambiguity / insufficient evidence")
        self.assertEqual(response.session_output.tool_called, "route_to_human_queue")

    def test_order_not_received_happy_path_resolves(self) -> None:
        response = self.agent.handle(TriageRequest(message="My order ord_5001 has not arrived yet."))
        self.assertIsInstance(response, FinalResponse)
        self.assertEqual(response.session_output.resolution_status.value, "resolved")
        self.assertEqual(response.session_output.tool_called, "lookup_order_status")
        self.assertEqual(response.session_output.tool_result["fulfillment_status"], "in_transit")

    def test_cancellation_request_creates_support_ticket(self) -> None:
        response = self.agent.handle(TriageRequest(message="Please cancel alice@example.com"))
        self.assertIsInstance(response, FinalResponse)
        self.assertEqual(response.session_output.issue_type.value, "cancellation_request")
        self.assertEqual(response.session_output.resolution_status.value, "resolved")
        self.assertEqual(response.session_output.tool_called, "create_support_ticket")
        self.assertEqual(response.session_output.fields_collected.customer_id, "cust_1001")

    def test_human_request_language_escalates(self) -> None:
        response = self.agent.handle(TriageRequest(message="I want a human agent to review this billing issue."))
        self.assertIsInstance(response, FinalResponse)
        self.assertEqual(response.session_output.resolution_status.value, "escalated")
        self.assertEqual(response.session_output.escalation.reason, "Human requested")
        self.assertEqual(response.session_output.tool_called, "route_to_human_queue")

    def test_order_lookup_not_found_escalates(self) -> None:
        response = self.agent.handle(TriageRequest(message="My order ord_5002 has not arrived yet."))
        self.assertIsInstance(response, FinalResponse)
        self.assertEqual(response.session_output.resolution_status.value, "escalated")
        self.assertEqual(response.session_output.escalation.reason, "Lookup ambiguity / insufficient evidence")
        self.assertEqual(response.session_output.tool_called, "route_to_human_queue")


if __name__ == "__main__":
    unittest.main()
