from __future__ import annotations

from typing import Any


class ToolError(RuntimeError):
    """Raised when a mock tool cannot complete successfully."""


CUSTOMER_RECORDS = {
    "alice@example.com": {
        "customer_id": "cust_1001",
        "email": "alice@example.com",
        "recent_charges": [
            {"charge_id": "ch_2001", "amount": "24.99", "posted_at": "2026-04-02"},
            {"charge_id": "ch_2002", "amount": "24.99", "posted_at": "2026-04-02"},
        ],
    },
    "cust_1001": {
        "customer_id": "cust_1001",
        "email": "alice@example.com",
        "recent_charges": [
            {"charge_id": "ch_2001", "amount": "24.99", "posted_at": "2026-04-02"},
            {"charge_id": "ch_2002", "amount": "24.99", "posted_at": "2026-04-02"},
        ],
    },
    "bob@example.com": {
        "customer_id": "cust_1002",
        "email": "bob@example.com",
        "recent_charges": [{"charge_id": "ch_3001", "amount": "48.00", "posted_at": "2026-04-01"}],
    },
    "cust_1002": {
        "customer_id": "cust_1002",
        "email": "bob@example.com",
        "recent_charges": [{"charge_id": "ch_3001", "amount": "48.00", "posted_at": "2026-04-01"}],
    },
    "cust_1003": {
        "customer_id": "cust_1003",
        "email": "casey@example.com",
        "recent_charges": [],
    },
}

ORDER_STATUSES = {
    "ord_5001": {
        "order_id": "ord_5001",
        "fulfillment_status": "in_transit",
        "estimated_delivery": "2026-04-08",
        "delivered_at": None,
    },
    "ord_5003": {
        "order_id": "ord_5003",
        "fulfillment_status": "delivered",
        "estimated_delivery": None,
        "delivered_at": "2026-04-04",
    },
}


def lookup_customer_record(identifier: str, identifier_type: str) -> dict[str, Any]:
    # MOCK -- local in-memory customer lookup used instead of a real customer system.
    if identifier_type not in {"email", "customer_id"}:
        raise ToolError(f"unsupported identifier_type={identifier_type}")

    record = CUSTOMER_RECORDS.get(identifier.lower() if identifier_type == "email" else identifier)
    if not record:
        return {
            "status": "not_found",
            "identifier": identifier,
            "identifier_type": identifier_type,
            "customer_id": None,
            "email": None,
            "recent_charges": [],
        }

    return {
        "status": "found",
        "identifier": identifier,
        "identifier_type": identifier_type,
        "customer_id": record["customer_id"],
        "email": record["email"],
        "recent_charges": record["recent_charges"],
    }


def lookup_order_status(order_id: str) -> dict[str, Any]:
    # MOCK -- local order-status lookup used instead of a real fulfillment system.
    result = ORDER_STATUSES.get(order_id)
    if not result:
        return {
            "status": "not_found",
            "order_id": order_id,
            "fulfillment_status": None,
            "estimated_delivery": None,
            "delivered_at": None,
        }
    return {"status": "found", **result}


def create_support_ticket(issue_type: str, customer_id: str, summary: str, priority: str) -> dict[str, Any]:
    # MOCK -- local ticket creation used instead of a real support platform.
    return {
        "status": "created",
        "ticket_id": f"ticket_{customer_id}_{issue_type}",
        "issue_type": issue_type,
        "customer_id": customer_id,
        "priority": priority,
        "summary": summary,
    }


def route_to_human_queue(reason: str, priority: str, context: dict[str, Any]) -> dict[str, Any]:
    # MOCK -- local human-routing action used instead of a real queueing system.
    return {
        "status": "queued",
        "queue_name": "human_support_queue",
        "reason": reason,
        "priority": priority,
        "context": context,
    }
