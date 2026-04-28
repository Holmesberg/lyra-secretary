"""Brain-dump edge-case battery v2 (post-parser-fixes, 2026-04-29).

Targets the bugs surfaced in the v1 battery:
  - Action-verb-wins classification (study-for-midterm)
  - Trailing-preposition title leak (call advisor at)
  - DATE_HINTS regex extensions (the 15th, this weekend, May 16)
  - Leading-bullet stripping
  - Plus the exact dump from the operator's screenshot.

Runs as moriartyholmesberg (X-User-Id: 15). Does NOT void afterward.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime

BASE = "http://localhost:8000"
USER_ID = "15"


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-User-Id": USER_ID},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode()}


# Cases focused on the bugs we fixed + the operator's screenshot dump.
CASES: list[tuple[str, str]] = [
    (
        "operator_screenshot",
        "BCI paper deadline friday, read research paper 4 today, "
        "initiate contract workflow, CO final 16/5 10 am, CO Lec 4 today",
    ),
    ("study_for_midterm_binds", "midterm Wednesday\nstudy for midterm tomorrow"),
    ("call_advisor_at_3pm", "call advisor at 3pm"),
    ("submit_form_on_16_5", "submit form on 16/5"),
    ("exam_on_friday_10am_caps", "EXAM ON FRIDAY 10AM"),
    ("exam_on_the_15th", "exam on the 15th"),
    ("do_laundry_this_weekend", "do laundry this weekend"),
    ("submit_X_by_may_16", "submit X by May 16"),
    ("call_at_3_30pm_tomorrow", "call professor at 3:30pm tomorrow"),
    ("bullet_list", "- read chapter 3\n- write essay\n- review notes"),
    ("numbered_list", "1. read book\n2. write notes\n3. review"),
    ("plus_separator", "read chapter 3 + write essay + review notes"),
    ("test_as_verb", "test the API tomorrow"),
    ("complex_realistic", "presentation Tuesday 2pm, prepare slides Sunday, email professor about extension monday"),
    ("clean_binding", "BCI paper due Friday\nread BCI paper tomorrow"),
]


def now_local_iso():
    """Container clock is UTC; emit a USER_TIMEZONE (Cairo, UTC+3 in
    summer) ISO so default-when calculations don't drift into the
    past when TaskManager re-interprets via to_utc()."""
    from zoneinfo import ZoneInfo
    d = datetime.now(ZoneInfo("Africa/Cairo")).replace(tzinfo=None)
    return d.replace(microsecond=0).isoformat()


def short(s, n=44):
    s = s.replace("\n", " ⏎ ")
    return s if len(s) <= n else s[: n - 1] + "…"


def fmt_items(items):
    parts = []
    for i in items:
        when = (i.get("when_local") or "—")
        if when != "—":
            when = when[:16]
        parts.append(
            f"{i['kind'][:1].upper()}:{short(i['title'], 22)}@{when}"
        )
    return " │ ".join(parts) if parts else "—"


def fmt_bindings(bindings):
    if not bindings:
        return "—"
    return " │ ".join(
        f"{b['tier'][:5]}({b['confidence']:.2f}→{short(b['deadline_title'], 14)})"
        for b in bindings
    )


def main():
    now_iso = now_local_iso()
    print(f"now_local_iso = {now_iso}")
    print()
    rows = []
    for label, text in CASES:
        parse_res = post("/v1/brain-dump/parse", {
            "raw_text": text, "current_local_iso": now_iso
        })
        if "_error" in parse_res:
            rows.append((label, text, f"PARSE HTTP {parse_res['_error']}", "—", "—"))
            continue
        items = parse_res.get("items", [])
        bindings = parse_res.get("bindings", [])

        commit_res = post("/v1/brain-dump/commit", {
            "items": [
                {k: i[k] for k in ("item_id", "kind", "title", "when_local", "duration_minutes")}
                for i in items
            ],
            "bindings": [
                {"task_item_id": b["task_item_id"], "deadline_item_id": b["deadline_item_id"]}
                for b in bindings if b["tier"] in ("tier1_auto", "tier2_ask")
            ],
        })
        if "_error" in commit_res:
            commit_summary = f"COMMIT HTTP {commit_res['_error']}"
        else:
            commit_summary = (
                f"T={commit_res['tasks_created']} "
                f"D={commit_res['deadlines_created']} "
                f"B={commit_res['bindings_applied']}"
            )
        rows.append((label, text, fmt_items(items), fmt_bindings(bindings), commit_summary))

    # Table
    print("| # | Case | Input | Parsed Items | Bindings | Commit |")
    print("|---|------|-------|--------------|----------|--------|")
    for idx, (label, text, items, bindings, commit) in enumerate(rows, 1):
        print(f"| {idx} | {label} | `{short(text, 60)}` | {items} | {bindings} | {commit} |")


if __name__ == "__main__":
    main()
