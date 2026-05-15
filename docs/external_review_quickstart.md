# External Review Quickstart

This is the short path for professors, recruiters, and technical reviewers who
need to understand LyraOS before reading the full doctrine stack.

## One-Sentence Description

LyraOS is a planning and execution app whose core contribution is a
rule-governed behavioral measurement system: users plan and work normally, the
system preserves the trace, and later insights must pass provenance,
clean-data, exposure, and uncertainty gates.

## What Is Shipped

- Google sign-in
- brain-dump onboarding
- task planning and quick capture
- start/pause/resume/stop/switch timers
- overdue and missed-plan recovery
- calendar and deadline views
- Moodle iCal import and submission detection
- read-only Google Calendar context
- Pulse dashboard
- Insights page with descriptive synthesis and confidence-tiered cards
- pause and resume prediction surfaces
- archetype survey/proximity as a cold-start prior, not an identity claim
- account export/deletion and alpha feedback

## What Is Not Claimed

- No autonomous scheduling is shipped.
- No hidden calendar mutation is shipped.
- No validated adaptive scheduling claim is made.
- No stable personality or identity labels are treated as truth.
- No AI-generated behavioral interpretation is promoted to product truth.
- No exposed/intervened behavior is allowed to silently become baseline
  evidence.

## What To Look At First

1. [README.md](../README.md) for the product/architecture overview.
2. [MANIFESTO.md](../MANIFESTO.md) for top-level doctrine.
3. [docs/behavioral_instrumentation_doctrine.md](behavioral_instrumentation_doctrine.md)
   for the rule-based/probabilistic framing.
4. [docs/cortex_contract_v0.md](cortex_contract_v0.md) for canonical metrics
   and clean-data profiles.
5. [docs/cortex_product_research_contract_v0.md](cortex_product_research_contract_v0.md)
   for the product/research and exposure-ledger boundary.
6. [archive/appstore/summary_of_app.md](../archive/appstore/summary_of_app.md)
   for the comprehensive current-state summary.

## How To Verify The Repo Shape

Frontend build:

```bash
cd frontend
npm ci
npm run build
```

Backend tests:

```bash
cd backend
python -m pip install -r requirements.txt
python -m pip install pytest
$env:PYTHONPATH="."
pytest tests/
```

Static topology contract:

```bash
node scripts/test_runtime_topology_contract.mjs
```

Public runtime topology, when the public stack is up:

```bash
node scripts/verify_runtime_topology.mjs --topology public
```

## Current Limits

- Pre-alpha dogfood with a small alpha cohort.
- Not an IRB-approved human-subjects study unless a future institutional
  protocol says otherwise.
- Public privacy/terms copy exists but still needs production-grade legal
  review.
- Google refresh tokens and Moodle iCal URLs remain known plaintext credential
  debts.
- Frontend automated tests are still thin; CI now proves the production
  frontend build, but Playwright coverage should be added next.
