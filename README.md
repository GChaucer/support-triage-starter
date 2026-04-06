# support-triage-starter

A small proof-of-work project for support workflow implementation.

It takes a customer message, classifies the issue, calls a mock backend tool,
returns a plain-language reply, and produces structured JSON output.
It escalates to a human queue when criteria are met.

This is a proof-of-work project, not a production system.
It demonstrates workflow design, integration thinking, structured outputs,
and human escalation logic.

---

## How to run

Python 3.11+ is required.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn src.server:app --reload
# open http://localhost:8000
```

To deploy on Railway, connect this repo and Railway will use the Procfile automatically.
No environment variables are required for Phase 1.

---

## Issue types (Phase 1)

- order_not_received
- duplicate_charge
- cancellation_request

---

## How this was built

Claude handled spec, review, and workflow guardrails.
Codex handled implementation.
I kept final approval over scope and publish readiness.

Commit prefixes reflect role boundaries:
`spec(claude)` `feat(codex)` `fix(codex)` `review(human)`

See SPEC.md, REVIEW.md, and CLAUDE.md for full context.

---

## Build workflow

This project was built using the operating pattern from my
[AI Operator System](https://github.com/GChaucer/ai-operator-system) repo.

That means spec before build, clear role boundaries, human approval gates,
and honest documentation of what was built and what was deferred.

This repo is a standalone project. It is not a fork or a template instance.
It just follows the same method.
