# LLM Enrichment Maxinstances Alert

**Date:** 2026-05-17.
**Subsystem:** `scheduler.health / llm_enrichment`.
**Severity:** warning.
**Status:** mitigated in code.

## Alert

```text
APScheduler job llm_enrichment hit maxinstances; a prior run is still active.
```

## Classification

This is not a provider-auth failure and not a data-integrity incident. It is a
scheduler reliability warning: an auxiliary enrichment job was still running
when the next tick arrived.

Required alert context:

- affected provider/subsystem: `scheduler.health / llm_enrichment`
- affected user scope: unknown from scheduler event alone
- retry behavior: skipped tick; scheduler retries on the next interval
- user action needed: no student action
- data integrity risk: low unless repeated across intervals

## Root Cause

The enrichment job ran every 5 seconds with `max_instances=1`, while one
enrichment cycle could call hosted NIM with the longer foreground JARVIS
timeout. A slow provider call could therefore make the next scheduled tick hit
`max_instances`.

## Mitigation

- Treat LLM enrichment as auxiliary, not critical path.
- Run `llm_enrichment` every 60 seconds.
- Claim 1 task per cycle.
- Keep `max_instances=1`.
- Add a separate short hosted-NIM enrichment timeout.

## Invariants

- Provider slowness must degrade enrichment, not scheduler reliability.
- LLM enrichment must not own scheduling truth.
- Provider failure must degrade functionality, not weaken authentication or
  user scoping.

## Regression Coverage

- `backend/tests/test_llm_enrichment_scheduler_contract.py`
- `backend/tests/test_nvidia_nim_client.py`
