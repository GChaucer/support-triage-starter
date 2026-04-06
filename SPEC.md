# Support Triage Starter -- SPEC

Version: 1.0
Status: Approved for Phase 1 build

---

## What This Is

A local triage workflow. It takes a customer message,
classifies the issue, calls a mock tool, and returns
a structured response. It escalates when it should.

This is a reference implementation, not a production system.
It demonstrates: workflow design, integration pattern,
structured outputs, and human escalation logic.

---

## Runtime

Rule-based. Phase 1 triage logic lives in `src/agent.py`
and uses deterministic keyword and field rules.
There are no provider calls in Phase 1.

---

## Phase 1 Scope

**Issue types:** order_not_received, duplicate_charge, cancellation_request

**Tools:**
- lookup_customer_record(identifier, identifier_type)
- lookup_order_status(order_id)
- create_support_ticket(issue_type, customer_id, summary, priority)
- route_to_human_queue(reason, priority, context)

**Interface:** FastAPI backend, single-file HTML frontend (no build step)

**Output:** Structured JSON on every session exit. No silent omissions.
Logging output is written to `logs/support_triage.log`.

---

## One-follow-up rule

The agent asks at most one clarifying question per session.
If the required field is still missing after one follow-up, the agent
calls route_to_human_queue and exits. This is enforced in code,
not left to prompt instruction.

---

## Escalation triggers

| Trigger | Condition | Priority |
|---|---|---|
| Low confidence | Classification confidence is low | normal |
| Human requested | Customer explicitly asks for a human | normal |
| Tool failure | ToolError raised or status: not_found | high |
| Duplicate charge ambiguity | recent_charges missing, sparse, or ambiguous | high |
| Missing required info | Required field still missing after one follow-up | normal |
| Threat / legal / frustration | Detected in customer message | high |

---

## JSON output schema

```json
{
  "session_id": "string",
  "timestamp": "ISO 8601",
  "issue_type": "order_not_received | duplicate_charge | cancellation_request | unknown",
  "classification_confidence": "high | medium | low",
  "fields_collected": {
    "customer_id": "string | null",
    "order_id": "string | null",
    "charge_id": "string | null"
  },
  "tool_called": "string | null",
  "tool_result": "object | null",
  "resolution_status": "resolved | escalated",
  "customer_response": "string",
  "escalation": {
    "triggered": "boolean",
    "reason": "string | null",
    "recommended_team": "billing | fulfillment | general | null",
    "summary": "string | null"
  }
}
```

---

## Phase 2 (backlog)

Add: appointment_change, product_issue.
Requires human gate approval before any Phase 2 work begins.

---

## How this was built

Claude wrote the spec, prompts, output schema, and escalation logic.
Codex wrote the implementation.
The human approved before implementation began
and before this repo entered any portfolio context.

Commit prefixes: spec(claude) feat(codex) fix(codex) review(human)
