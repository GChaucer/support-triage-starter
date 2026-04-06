# REVIEW.md

Claude's critique log. One entry per review point.
Not a changelog. Not marketing copy.

---

## Pre-Build Critique

### Strengths of this scope

Three issue types is the right constraint. Covers the pattern without padding.
Four tools reflects a real support operation: identify, investigate, act, hand off.
Text-first keeps the scope honest.
Structured JSON on every exit path is the right engineering choice.
Separating escalation.py makes the trigger logic independently readable and testable.

### Risks going into Phase 1

**Classifier accuracy on edge cases.**
"I was charged twice and want to cancel" spans two issue types.
The classifier rules must have a clear rule for this.
Recommendation: pick the primary issue by first intent signal.

**Duplicate charge handling without a billing tool.**
The agent can only surface what recent_charges shows in the customer record.
It cannot confirm refund eligibility. The escalation trigger for ambiguity must fire reliably.
If it does not, the agent will produce a confident-sounding response that is not backed by evidence.

**One-follow-up rule must be enforced in code.**
If this lives only in comments or docs, it will not hold under adversarial or meandering inputs.
Codex must implement a hard state flag in agent.py.

### What was cut and why

- Five issue types: dilutes Phase 1 focus, adds no new patterns
- Frontend build step: no value for a local demo
- Billing lookup tool: honest scope limit, handled by escalation
- Multi-turn memory: not being built, not claimed

---

## Phase 1 Review

Status: approve

### What landed

FastAPI backend, single-file HTML frontend, Pydantic schemas, four mock tools,
one-follow-up enforcement in code, escalation routing through `route_to_human_queue`,
file and console logging, and 6 passing tests covering the full critical path.

### What is strong

**One-follow-up rule is enforced in code.**
`follow_up_count >= 1` is a hard state check in `agent.py`. Not a prompt instruction.
It holds under adversarial and meandering inputs. This was the most important
constraint in the spec and it is correctly implemented.

**Every exit path produces a populated `SessionOutput`.**
Resolved and escalated sessions both return a fully typed JSON object.
No silent exits. No partial outputs.

**Duplicate charge handling is honest.**
`_charges_plausibly_indicate_duplicate` checks for matching amount and date
without claiming refund eligibility. The customer response says "plausibly indicates."
Ambiguous evidence escalates instead of resolving with false confidence.

**escalation.py is an independent, readable policy layer.**
Trigger logic is isolated from the agent loop. It can be read, tested,
and modified without touching `agent.py`.

**schemas.py is clean and fully typed.**
The `TriageResponse = FollowUpResponse | FinalResponse` union correctly models
the two exit states. All fields are required or explicitly optional.

**Runtime framing is honest.**
Phase 1 is rule-based. README, SPEC, and `.env.example` all say so plainly.
No provider calls, no dead code, no misleading references.

**6 of 6 tests pass on Python 3.11.**

### What remains intentionally limited

- Classifier is keyword and regex matching. A real deployment would use an LLM.
  The architecture supports it. `_classify()` in `agent.py` is the only method
  that would change. This is a documented Phase 2 path, not a gap.
- Structured output is returned in the HTTP response only.
  Operational logs go to `logs/support_triage.log`.
- All tools are mock. Every boundary is labeled `# MOCK` in code.
- No session persistence, no auth, no multi-turn memory.
- Frontend carries follow-up state in-browser. Sessions are local and short-lived.

### Open risks

Mixed-intent messages collapse to one issue type. "I was charged twice and want
to cancel" will classify as duplicate_charge on the first signal matched.
Acceptable for Phase 1. Will surface quickly in any extended demo.

`_charges_plausibly_indicate_duplicate` groups by amount and posted date.
Two legitimate same-day charges at the same amount would trigger it.
Known false-positive risk at the mock data layer.

### Recommendation

Approve.

Phase 1 is complete. Scope held. Implementation matches the spec.
Tests cover the critical path. The repo is honest about what it is
and what it defers. Ready for portfolio use and Phase 2 gate.
