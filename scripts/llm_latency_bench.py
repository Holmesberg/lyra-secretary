"""LLM latency benchmark for deadline discovery prompts.

Times Ollama qwen2.5:3b cold + warm latency for realistic Lyra task-
creation prompts. Reports per-trial timing, JSON validity, and the
extracted deadline_name + sub_items so we can eyeball whether the
output is actually useful at the achieved latency.

Calibrates the OLLAMA_TIMEOUT_SECONDS=10 setting from C1.
"""
import json
import sys
import time
from statistics import median

import requests

OLLAMA_URL = "http://172.24.96.1:11434"
MODEL = "qwen2.5:3b"

# Mirror app/services/llm_parser.py:_build_prompt structure
PROMPT_TEMPLATE = """You are a structured-output parser for a productivity scheduler. Given the task title and description below, extract structured fields. Respond with ONLY a single JSON object matching the schema. No prose, no markdown, no commentary.

Schema fields:
  - priority: integer 1-5 (1=critical, 5=low), or null
  - deadline_name: string referencing a deadline the user wrote, or null
  - sub_items: array of strings (sub-tasks; empty if none)
  - scope_estimate_minutes: integer (your estimate of total task minutes), or null

Task title: {title}
Task description:
{description}

Available deadlines (match deadline_name semantically, by intent — use natural-language fragments the user wrote):
{deadline_list}
"""

# Fixed deadline list — same shape the operator's actual database has
DEADLINE_LIST = """  - id=d1: "BCI Paper"
  - id=d2: "Neurotech Hackathon"
  - id=d3: "Aibdaya AI Course Module 4"
  - id=d4: "Spring School Application"
  - id=d5: "Lyra Alpha Launch"
"""

# Realistic task scenarios — varying complexity
SCENARIOS = [
    {
        "label": "title-only deadline (operator's Q1 case)",
        "title": "BCI paper writeup intro",
        "description": "",
    },
    {
        "label": "title + bullet desc + deadline keyword",
        "title": "BCI paper writeup",
        "description": "- intro section, like 800 words\n- citations cleanup\n- run plagiarism scan\n(due Friday for BCI paper deadline)",
    },
    {
        "label": "no deadline reference",
        "title": "Read Russell & Norvig ch. 7",
        "description": "Just the agent architectures section",
    },
    {
        "label": "ambiguous abbreviation",
        "title": "Hackathon prep",
        "description": "Test the qualia decoder pipeline end-to-end before submission deadline",
    },
    {
        "label": "casual single-line",
        "title": "Submit spring school app by tomorrow",
        "description": "",
    },
    {
        "label": "long brain-dump",
        "title": "Lyra alpha — wrap-up sprint",
        "description": "- finish W3 task-end predictor\n- ship resume banner UI\n- write retention notebook\n- ping omar + medo for week 1 feedback\n- alembic 039 migration to Supabase\n- update MANIFESTO Rule 18 for v1.16 bump\nMust ship by Lyra Alpha Launch deadline.",
    },
]


def build_prompt(title: str, description: str) -> str:
    return PROMPT_TEMPLATE.format(
        title=title,
        description=description or "(empty)",
        deadline_list=DEADLINE_LIST,
    )


def call_ollama(prompt: str, timeout: float = 30.0) -> tuple[float, dict | None, str]:
    """Returns (elapsed_seconds, parsed_json | None, error_or_empty)."""
    t0 = time.time()
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 512},
                "keep_alive": "30m",
            },
            timeout=timeout,
        )
        r.raise_for_status()
        elapsed = time.time() - t0
        body = r.json()
        raw = body.get("response", "").strip()
        # Strip markdown fence (matches llm_parser._strip_markdown_fence)
        if raw.startswith("```"):
            nl = raw.find("\n")
            if nl > 0:
                raw = raw[nl + 1:]
            if raw.rstrip().endswith("```"):
                raw = raw.rstrip()[:-3].rstrip()
        try:
            parsed = json.loads(raw)
            return elapsed, parsed, ""
        except json.JSONDecodeError as e:
            return elapsed, None, f"JSON parse error: {e} | raw: {raw[:200]}"
    except requests.Timeout:
        return time.time() - t0, None, "TIMEOUT"
    except Exception as e:
        return time.time() - t0, None, f"{type(e).__name__}: {e}"


def main() -> int:
    # Smoke check
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        print(f"Ollama reachable. Models: {models}")
        if MODEL not in models:
            print(f"⚠️  Model {MODEL} not pulled. Run: ollama pull {MODEL}")
            return 1
    except Exception as e:
        print(f"Ollama unreachable at {OLLAMA_URL}: {e}")
        return 1

    print(f"\n{'─' * 78}")
    print(f"LLM Latency Benchmark — model={MODEL} url={OLLAMA_URL}")
    print(f"{'─' * 78}\n")

    all_latencies: list[float] = []
    cold_latencies: list[float] = []
    warm_latencies: list[float] = []

    for sci, sc in enumerate(SCENARIOS):
        print(f"[{sci+1}/{len(SCENARIOS)}] {sc['label']}")
        prompt = build_prompt(sc["title"], sc["description"])

        # 3 calls per scenario: 1st = warm-or-cold, 2nd-3rd = warm
        scenario_latencies = []
        for trial in range(3):
            elapsed, parsed, err = call_ollama(prompt)
            scenario_latencies.append(elapsed)
            all_latencies.append(elapsed)
            if trial == 0 and sci == 0:
                cold_latencies.append(elapsed)
            else:
                warm_latencies.append(elapsed)
            json_ok = parsed is not None
            deadline = parsed.get("deadline_name") if parsed else None
            n_sub = len(parsed.get("sub_items", [])) if parsed else 0
            priority = parsed.get("priority") if parsed else None
            scope = parsed.get("scope_estimate_minutes") if parsed else None
            print(f"   trial {trial+1}: {elapsed:5.2f}s  json={'✓' if json_ok else '✗'}  "
                  f"deadline={deadline!r:25s}  sub_items={n_sub}  priority={priority}  scope={scope}")
            if err:
                print(f"      err: {err}")
        print(f"   median: {median(scenario_latencies):.2f}s\n")

    print(f"{'─' * 78}")
    print(f"SUMMARY (n={len(all_latencies)} trials)")
    print(f"{'─' * 78}")
    if cold_latencies:
        print(f"  Cold call (1st of session):  {cold_latencies[0]:.2f}s")
    if warm_latencies:
        wl = sorted(warm_latencies)
        p50 = wl[len(wl)//2]
        p95 = wl[int(len(wl) * 0.95)] if len(wl) >= 5 else wl[-1]
        print(f"  Warm — n={len(wl)}, min={min(wl):.2f}s  p50={p50:.2f}s  p95={p95:.2f}s  max={max(wl):.2f}s")
    print(f"  All trials median:           {median(all_latencies):.2f}s")
    print(f"  All trials max:              {max(all_latencies):.2f}s")
    print()

    # Calibration verdict re: OLLAMA_TIMEOUT_SECONDS=10
    over_10s = [t for t in all_latencies if t > 10.0]
    over_8s = [t for t in all_latencies if t > 8.0]
    print(f"Calibration vs OLLAMA_TIMEOUT_SECONDS=10:")
    print(f"  trials > 10s: {len(over_10s)}/{len(all_latencies)}")
    print(f"  trials > 8s:  {len(over_8s)}/{len(all_latencies)}")
    if over_10s:
        print(f"  → 10s timeout is TIGHT; consider 12-15s for cold-load headroom")
    elif over_8s:
        print(f"  → 10s leaves <2s margin on slowest cases; acceptable but tracked")
    else:
        print(f"  → 10s is comfortable; current setting is correct")

    return 0


if __name__ == "__main__":
    sys.exit(main())
