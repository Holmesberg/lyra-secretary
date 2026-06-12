# External Review Quickstart

This is the short path for professors, recruiters, and technical reviewers who
need to understand LyraOS before reading the full doctrine stack.

## One-Sentence Description

LyraOS is a planning and execution app whose core contribution is a
rule-governed behavioral measurement system: users plan and work normally, the
system preserves the trace, and later insights must pass provenance,
clean-data, exposure, and uncertainty gates.

Current paper-direction shorthand:

```text
Measurement Integrity Before Agency Claims
```

LyraOS should be read as a case study in delaying claims about productivity,
focus, motivation, avoidance, discipline, recovery, or agency until the
underlying variables survive clean-data, provenance, exposure, and
slice-invariance checks.

## Evolution Of The App

LyraOS started from a broader question about whether planning failure could be
measured rather than guessed at. Early framing included productivity automation,
AI assistance, and possible BCI/cognitive-state signals. The current repo is
more conservative and, scientifically, stronger: the core system is not BCI-led
and not AI-led. It is a rule-based/probabilistic behavioral instrument that
uses ordinary planning and timer traces as its primary substrate.

The current architecture treats those earlier directions as bounded layers:

- **BCI/cognitive-state sensing:** historical and future research context, not
  a shipped input stream.
- **AI:** enrichment, operator tooling, implementation support, and interface
  glue; not the source of behavioral truth.
- **Adaptive scheduling:** a future-gated evidence loop, not autonomous
  rescheduling.
- **Current core:** longitudinal traces, clean-data profiles, exposure state,
  explicit uncertainty, and conservative synthesis.

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
6. [docs/measurement_integrity_before_agency_claims.md](measurement_integrity_before_agency_claims.md)
   for the current methods-paper direction.
7. [archive/appstore/summary_of_app.md](../archive/appstore/summary_of_app.md)
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
- The current paper direction is methodological; it does not claim LyraOS has
  already validated focus, motivation, avoidance, discipline, recovery, or
  agency constructs.
