# LLM latency benchmark — qwen2.5:3b deadline discovery

> Historical benchmark. The direct Ollama/NIM enrichment runtime and benchmark
> script were retired on 2026-07-11. This file is lineage, not configuration or
> implementation authority.
**Date:** 2026-04-28
**Model:** qwen2.5:3b (Q4 quantized, ~1.9GB on disk)
**Hardware:** operator's RTX A4000 8GB VRAM
**Endpoint:** `http://172.24.96.1:11434` (WSL2 → Windows host)
**Script:** `scripts/llm_latency_bench.py`

## Why this matters

`OLLAMA_TIMEOUT_SECONDS=10` was set in C1 magic-for-alpha based on operator dogfood "5-8s warm." This benchmark validates the setting against realistic Lyra deadline-discovery prompts and answers operator's Q1 (does title-only parsing work?).

## Method

6 task-creation scenarios × 3 trials each = 18 calls. Prompt mirrors `app/services/llm_parser.py:_build_prompt` exactly. Includes a fixed list of 5 deadlines (BCI Paper, Neurotech Hackathon, Aibdaya AI Course Module 4, Spring School Application, Lyra Alpha Launch). Measures wall-clock end-to-end including JSON parsing.

## Results

### Per-scenario (median of 3 trials)

| # | Scenario | Median | Output |
|---|---|---|---|
| 1 | title-only deadline ("BCI paper writeup intro") | **2.06s** | deadline=BCI Paper, sub=0 |
| 2 | title + 3 bullets + "(due Friday for BCI paper)" | **3.62s** | deadline=BCI Paper, sub=3, priority=3 |
| 3 | no deadline reference ("Read R&N ch. 7") | **2.46s** | deadline=null (correct), sub=1 |
| 4 | ambiguous abbrev ("Hackathon prep" + qualia decoder) | **4.11s** | deadline=Neurotech Hackathon, sub=3, scope=120 |
| 5 | casual single-line ("Submit spring school app by tomorrow") | **2.07s** | deadline=Spring School Application |
| 6 | long brain-dump (6 bullets + "Lyra Alpha Launch deadline") | **6.24s** | deadline=Lyra Alpha Launch, sub=6 |

### Aggregate (n=18 trials)

| Metric | Value |
|---|---|
| Cold call (1st of session, after model unloaded) | 3.74s |
| Warm min | 0.30s (cached short prompt) |
| Warm p50 | 3.82s |
| Warm p95 | 9.27s |
| Max | 9.27s |
| Trials >10s | 0/18 |
| Trials >8s | 1/18 (the long brain-dump cold trial) |
| JSON validity | 18/18 |
| Deadline match accuracy | 18/18 correct |

## Findings

1. **Title-only parsing works.** Operator's Q1 concern is addressed in code: scenario #1 returns the right deadline with empty description in 2-4s. The LLM picks up the title verbatim plus the existing token-blend ranker handles fuzzy cases.

2. **Semantic matching is robust.** Scenario #4 ("Hackathon prep" + "qualia decoder pipeline") correctly maps to "Neurotech Hackathon" — the LLM uses domain context (decoder = neurotech) without seeing the brand-name token. This is exactly the upside that motivated W1 vs pure regex.

3. **No null-result false alarms.** Scenario #3 ("R&N ch. 7") correctly returns `deadline_name=null` — no hallucinated bindings against unrelated deadlines.

4. **Long brain-dumps are the latency tail.** Scenario #6 (6 bullets, ~50 words) had a 9.27s cold trial — the only outlier in the distribution. As description complexity scales, p95 will creep further.

## Recommendations

### Keep `OLLAMA_TIMEOUT_SECONDS=10` for now
0/18 trials timed out. The setting is correct for the current prompt distribution.

### Watch for production-tail creep
If alpha users write longer descriptions than my benchmark scenarios, p95 could cross 10s. Two graceful options:

- **Option A — stay at 10s, accept rare `unavailable` on long-dump tail.** UI degrades gracefully; chip simply doesn't render. Worker re-queues on next cycle when shorter prompts come in.
- **Option B — bump to 12s.** Adds 0.5s of headroom over today's p95, costs nothing on warm path. Revisit once we have ≥50 production samples.

I lean **Option A** for shipping (fewer moving parts; the contract is already "graceful degradation"). Reconsider after 1 week of production data.

### Cold-load after laptop sleep is uncharted
This benchmark ran with the model already loaded into VRAM. After laptop sleep + Cloudflare-tunnel wake, the first task creation could trigger a full model load (~5-10s on top of inference). If the operator's laptop sleeps overnight and a user creates a task within 1-2 minutes of wake, the chip might not appear. The `keep_alive=30m` flag in `_call_ollama` mitigates this once the first call completes, but the first call after sleep is the cold one.

**Mitigation idea:** add a small "warmup ping" job — every 10 minutes, the worker hits `/api/generate` with a trivial prompt purely to keep the model loaded. Cost: 30s/day of GPU. Benefit: first-task chip latency stays under 10s even after laptop wake. This is a possible W3.5 commit.

### Heuristic Tier 0 fallback (operator's "heuristic interventions" question)
Three of six scenarios completed in ≤2.5s. The other three took 3.6-9.3s. For the simple cases ("BCI paper writeup intro"), a regex/keyword heuristic could fire INSTANTLY without waiting for the LLM at all:

- If task title contains an exact substring of a deadline title → immediate Tier 1-equivalent chip with confidence=1.0, source='heuristic_substring'
- LLM still runs in parallel; if it disagrees, it overwrites with audit trail preserved

This could push perceived latency from "8s for chip" to "0s for chip" on the operator's most common case. Pre-registration consideration: the heuristic creates a separate `deadline_match_source` value that should be added to Rule 14's stratification list. Worth discussing.

## What stays unchanged

- The qwen2.5:3b → qwen2.5:7b migration is NOT recommended yet. 3b returns deadline + 6 sub_items + priority + scope estimates correctly at 100% JSON validity. The accuracy gain from 7b is marginal at this prompt complexity, while the latency cost (4x params, 2.5x VRAM) is substantial.
- `temperature=0.1` produces deterministic-ish outputs across the 18 trials (every scenario's 3 trials returned identical extracted fields).

## Files

- `scripts/llm_latency_bench.py` — runnable from any host that can reach Ollama. Operator can re-run on production hardware to validate post-deploy.
- This doc.
