# CLAUDE.md -- Support Triage Starter

## Roles

Claude: spec, prompts, output schema, escalation logic, critique.
Codex: all src/ implementation and tests/.
Human: approval gates.

No phase starts without human sign-off.
No implementation changes the spec without Claude flagging it first.

---

## What Claude Owns

SPEC.md, REVIEW.md, this file.
Everything in prompts/.
The JSON output schema.
The escalation matrix.
The tool contracts (signatures and mock shapes).
The sample_output.json fixture.

## What Codex Owns

src/, tests/, frontend/.
Codex follows the tool contracts and prompt files as written.
Any deviation gets flagged to Claude before merging.

---

## Hard Constraints

Do not add issue types beyond Phase 1 scope without human approval.
Do not add tools beyond the four in the contracts.
Do not introduce a frontend build step.
Do not add any external dependency without flagging it first.
Every mock boundary is labeled # MOCK in code.
route_to_human_queue must be called on every escalation path.
No silent resolution. Every session exits with a populated JSON output.

The one-follow-up rule is enforced in code, not prompt:
- ask at most one clarifying question per session
- if required field is still missing, escalate

---

## Gate Process

Claude updates REVIEW.md before each gate.
Claude states one of: approve / hold / rework.
Human makes the final call.

---

## Scope Protection

If a new idea comes up during build, add it to the Phase 2 backlog in SPEC.md.
Do not implement without human approval.
