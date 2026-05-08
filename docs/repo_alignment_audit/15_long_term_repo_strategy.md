# 15 Long Term Repo Strategy

**Purpose:** Prevent semantic entropy while preserving research survivability.

## Strategic Position

LyraOS is drifting toward a behavioral measurement instrument with a productivity
interface. That direction can survive only if measurement governance remains
stronger than feature generation.

## Prevent Semantic Entropy

1. Keep a small canonical metric vocabulary.
2. Treat docs as hypotheses until code-backed.
3. Freeze speculative concepts before they reach UI.
4. Maintain an ontology registry.
5. Require clean-data profiles for learning queries.
6. Keep raw substrate stable and boring.

## Preserve Falsifiability

- Every hypothesis has a falsifier.
- Every exposure is logged before adaptive inference.
- Every confidence claim states its basis.
- Every model declares excluded data.
- Every user-facing claim can be traced to a query and profile.

## Scale Ontology Carefully

Admit new constructs only after:

1. observation source exists,
2. contamination path is understood,
3. clean-data profile exists,
4. falsifier exists,
5. at least one rejected interpretation is documented.

## Contain Speculative Research

Use zones:

- `docs/parked_ideas.md`: raw ideas.
- `docs/jarvis_hypothesis_log.md`: operator-generated hypotheses.
- `docs/repo_alignment_audit/`: governance findings.
- `backend/app/services/inference_engine.py`: only promoted shared primitives.
- user-facing frontend: only calibrated, exposure-aware claims.

## Avoid AI-Generated Sediment

JARVIS and Codex can produce large amounts of plausible language. The repo must
not let plausible language become architecture.

Rules:

- no new concept without registry update,
- no JARVIS hypothesis promotion without negative evidence,
- no "smart" copy that hides uncertainty,
- no generated docs without evidence anchors.

## Preserve Architectural Intimacy

The operator must be able to answer:

- where does this signal originate?
- where is it transformed?
- where is uncertainty lost?
- where does the user see it?
- can the user seeing it change future measurements?

If a subsystem makes these answers hard, it should be frozen or simplified.

## Suggested Next Three Months

1. Freeze inference expansion.
2. Finish Cortex clean-data ownership.
3. Design Phase 1 exposure ledger.
4. Audit old analytics against Cortex profiles.
5. Migrate naming gradually, not explosively.
6. Keep JARVIS operator-only and reduce duplicate aggregations.
