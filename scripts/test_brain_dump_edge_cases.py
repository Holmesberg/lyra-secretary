"""Brain-dump edge-case battery (manual test runner, 2026-04-28).

Runs a series of realistic brain-dump inputs through the live deployed
/v1/brain-dump endpoints as moriartyholmesberg (user_id=15) and reports
the result table.

Usage (from inside the backend container):
    docker-compose exec backend python /workspace/scripts/test_brain_dump_edge_cases.py

Or from host:
    docker-compose exec -T backend python -c "$(cat scripts/test_brain_dump_edge_cases.py)"

Does NOT void anything afterwards — operator wants to see the rows in
the account.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000"
USER_ID = "15"  # moriartyholmesberg


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "X-User-Id": USER_ID,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"_error": e.code, "_body": body}


CASES: list[tuple[str, str]] = [
    ("simple_deadline", "midterm Friday 10am"),
    ("simple_task_dated", "read chapter 3 tomorrow"),
    ("clean_binding", "BCI paper due Friday\nread BCI paper tomorrow"),
    (
        "multi_items_with_binding",
        "midterm Wednesday\nessay due Friday\nstudy for midterm tomorrow\ndraft essay this weekend",
    ),
    ("undated_task", "do laundry"),
    ("multi_undated_stagger", "clean room, organize desk, water plants"),
    ("then_split", "finish homework then watch lecture then take notes"),
    (
        "compound_mixed_verbs",
        "study chapter 4 and review chapter 3 tomorrow at 8pm",
    ),
    ("all_caps", "EXAM ON FRIDAY 10AM"),
    ("apostrophe", "don't forget mom's birthday tuesday"),
    ("date_slash_format", "submit form on 16/5"),
    ("time_no_date", "call advisor at 3pm"),
    ("past_time", "submit by yesterday at 5pm"),
    ("implicit_day", "exam on the 15th"),
    (
        "brittle_no_bind",
        "paper due Friday\nfinish other work tonight",
    ),
    (
        "semicolon_split",
        "groceries; laundry; gym tomorrow morning",
    ),
    ("vague_no_anchor", "stuff to do this week"),
    (
        "long_phrase",
        "write a really long detailed presentation for the marketing class about consumer behavior next monday",
    ),
    ("bullet_list", "- read chapter\n- write essay\n- study"),
    (
        "complex_realistic",
        "presentation Tuesday 2pm, prepare slides Sunday, email professor about extension monday",
    ),
    ("number_in_title", "30 push-ups daily"),
    # dateparser supports Arabic; test with a simple phrase.
    ("foreign_language_arabic", "اقرأ الكتاب غدا"),
]


def short(s, n=40):
    s = s.replace("\n", " ⏎ ")
    return s if len(s) <= n else s[: n - 1] + "…"


def fmt_kind(items):
    parts = []
    for i in items:
        when = i.get("when_local") or "—"
        if when != "—":
            when = when[:16]  # YYYY-MM-DDTHH:MM
        parts.append(
            f"{i['kind'][:1].upper()}:{short(i['title'], 24)}@{when}({i['confidence']:.2f})"
        )
    return " | ".join(parts) if parts else "—"


def fmt_bindings(bindings):
    if not bindings:
        return "—"
    return " | ".join(
        f"{b['tier']}({b['confidence']:.2f}→{short(b['deadline_title'], 16)})"
        for b in bindings
    )


def main():
    rows = []
    for label, text in CASES:
        parse_res = post("/v1/brain-dump/parse", {"raw_text": text})
        if "_error" in parse_res:
            rows.append(
                {
                    "label": label,
                    "input": text,
                    "parse_status": f"HTTP {parse_res['_error']}",
                    "parsed_items": "—",
                    "parsed_bindings": "—",
                    "commit": "skipped",
                    "verified": "—",
                }
            )
            continue

        items = parse_res.get("items", [])
        bindings = parse_res.get("bindings", [])

        commit_payload = {
            "items": [
                {
                    "item_id": i["item_id"],
                    "kind": i["kind"],
                    "title": i["title"],
                    "description": i.get("description"),
                    "when_local": i.get("when_local"),
                    "duration_minutes": i.get("duration_minutes"),
                }
                for i in items
            ],
            "bindings": [
                {
                    "task_item_id": b["task_item_id"],
                    "deadline_item_id": b["deadline_item_id"],
                }
                for b in bindings
                if b["tier"] in ("tier1_auto", "tier2_ask")
            ],
        }
        commit_res = post("/v1/brain-dump/commit", commit_payload)
        if "_error" in commit_res:
            commit_summary = f"HTTP {commit_res['_error']}"
        else:
            commit_summary = (
                f"T={commit_res['tasks_created']} "
                f"D={commit_res['deadlines_created']} "
                f"B={commit_res['bindings_applied']}"
            )

        rows.append(
            {
                "label": label,
                "input": text,
                "parse_status": parse_res.get("parser_status", "?"),
                "parsed_items": fmt_kind(items),
                "parsed_bindings": fmt_bindings(bindings),
                "commit": commit_summary,
                "verified": "",  # filled in DB check below
            }
        )

    # Print table
    print(
        "| # | Case | Input | Parsed Items (kind:title@when(conf)) | Bindings | Commit | Notes |"
    )
    print(
        "|---|------|-------|---------------------------------------|----------|--------|-------|"
    )
    for idx, r in enumerate(rows, 1):
        print(
            f"| {idx} | {r['label']} | `{short(r['input'], 50)}` | {r['parsed_items']} | "
            f"{r['parsed_bindings']} | {r['commit']} | {r['parse_status']} |"
        )

    print()
    print("Test cases run:", len(rows))


if __name__ == "__main__":
    main()
