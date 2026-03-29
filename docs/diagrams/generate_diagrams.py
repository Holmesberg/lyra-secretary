"""
Generate system design PNGs (2x scale, dark theme).
Verified against:
  - backend/app/services/state_machine.py (TRANSITIONS)
  - backend/app/api/v1/router.py (route prefixes)
  - backend/app/services/notion_client.py (sync_task, archive_page)
  - backend/app/services/task_manager.py (transition callers)
  - backend/app/services/stopwatch_manager.py (start/stop flow)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).resolve().parent
BG = "#12141a"
TEXT = "#e8eaef"
SUB = "#9aa3b2"
DPI = 240  # ~2× crisp PNG export


def _save(fig, name: str) -> None:
    fig.savefig(
        OUT / name,
        dpi=DPI,
        facecolor=BG,
        edgecolor="none",
        bbox_inches="tight",
        pad_inches=0.35,
    )
    plt.close(fig)


def draw_architecture() -> None:
    """Layer-colored components; arrows show primary data flow."""
    fig, ax = plt.subplots(figsize=(14, 9), dpi=DPI, facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")

    layers = [
        ("User-facing", "#38bdf8"),
        ("AI agent", "#c084fc"),
        ("Backend", "#fb923c"),
        ("Storage", "#4ade80"),
        ("Presentation", "#f472b6"),
    ]
    ax.text(
        7,
        9.5,
        "Lyra Secretary — system architecture",
        ha="center",
        va="top",
        fontsize=16,
        fontweight="bold",
        color=TEXT,
    )
    lx = 0.4
    for label, c in layers:
        ax.add_patch(
            mpatches.Rectangle((lx, 9.05), 2.4, 0.32, facecolor=c, alpha=0.35, edgecolor=c)
        )
        ax.text(lx + 1.2, 9.21, label, ha="center", va="center", fontsize=8, color=TEXT)
        lx += 2.55

    def box(x, y, w, h, label, sub, color):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.02,rounding_size=0.15",
                facecolor=color,
                edgecolor=color,
                linewidth=1.8,
                alpha=0.22,
            )
        )
        ax.text(x + w / 2, y + h * 0.62, label, ha="center", va="center", fontsize=10, fontweight="bold", color=TEXT)
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center", fontsize=7.5, color=SUB)

    # Positions (x, y, w, h, color from layer)
    box(0.6, 6.8, 2.2, 1.1, "Telegram", "chat UI", "#38bdf8")
    box(3.4, 6.8, 2.2, 1.1, "OpenClaw", "AI agent / skills", "#c084fc")
    box(6.2, 6.5, 3.0, 1.6, "FastAPI", "REST /v1", "#fb923c")
    box(10.0, 6.8, 2.2, 1.1, "TaskManager", "single mutation authority", "#fb923c")

    box(0.8, 4.0, 2.4, 1.1, "SQLite", "tasks, sessions", "#4ade80")
    box(3.6, 4.0, 2.2, 1.1, "Redis", "stopwatch, undo, queues", "#22c55e")
    box(6.4, 4.0, 2.4, 1.1, "APScheduler", "reminders, Notion retry, overflow", "#fb923c")
    box(9.6, 4.0, 2.4, 1.1, "Notion", "calendar DB sync", "#f472b6")

    def arrow(x1, y1, x2, y2, label=None, style="-"):
        arr = FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.4,
            color="#94a3b8",
            linestyle=style,
            connectionstyle="arc3,rad=0",
        )
        ax.add_patch(arr)
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx, my + 0.15, label, ha="center", fontsize=7, color=SUB)

    # Request path: Telegram → OpenClaw → FastAPI → TaskManager
    arrow(2.8, 7.35, 3.4, 7.35, "chat")
    arrow(5.4, 7.35, 6.2, 7.35, "HTTP /v1")
    arrow(9.2, 7.35, 10.0, 7.35, "service layer")
    # TaskManager → persistence (single hub)
    arrow(11.0, 6.8, 2.0, 5.1, "SQLAlchemy")
    arrow(11.0, 6.8, 4.7, 5.1, "Redis client")
    arrow(11.0, 6.8, 10.8, 5.1, "NotionClient.sync_task()")
    # APScheduler (same app process): jobs read DB / Redis; retry pushes Notion sync
    arrow(7.4, 4.85, 2.0, 4.85, "query tasks", style="--")
    arrow(7.4, 4.55, 4.7, 4.55, "queues / TTL", style="--")
    arrow(7.4, 4.85, 10.8, 4.85, "retry_failed_syncs", style="--")

    ax.text(
        7,
        2.3,
        "Notion: NotionClient.sync_task() / archive_page() — see notion_client.py",
        ha="center",
        fontsize=8,
        color=SUB,
    )
    ax.text(
        7,
        1.7,
        "API routes: router.py mounts health, parse, query, tasks, stopwatch, undo, notifications under /v1",
        ha="center",
        fontsize=8,
        color=SUB,
    )

    _save(fig, "architecture.png")


def draw_state_machine() -> None:
    """
    Matches StateMachine.TRANSITIONS in state_machine.py.
    Call sites: TaskManager (task_manager.py), StopwatchManager.stop → complete_task.
    """
    fig, ax = plt.subplots(figsize=(12, 8), dpi=DPI, facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(-1, 11)
    ax.set_ylim(-1, 9)
    ax.axis("off")

    ax.text(
        5,
        8.4,
        "Task state machine (valid transitions + TaskManager methods)",
        ha="center",
        fontsize=15,
        fontweight="bold",
        color=TEXT,
    )

    def state(x, y, name):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                2.2,
                0.85,
                boxstyle="round,pad=0.02,rounding_size=0.12",
                facecolor="#1e293b",
                edgecolor="#60a5fa",
                linewidth=1.6,
            )
        )
        ax.text(x + 1.1, y + 0.42, name, ha="center", va="center", fontsize=10, fontweight="bold", color=TEXT)

    # Layout
    state(1.0, 4.5, "PLANNED")
    state(5.0, 6.5, "EXECUTING")
    state(7.5, 4.5, "EXECUTED")
    state(1.0, 1.5, "SKIPPED")
    state(4.0, 1.5, "DELETED")

    def tarrow(x1, y1, x2, y2, label, rad=0.0):
        arr = FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=1.3,
            color="#94a3b8",
            connectionstyle=f"arc3,rad={rad}",
        )
        ax.add_patch(arr)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx + rad * 2, my + 0.25, label, ha="center", fontsize=7.5, color="#cbd5e1")

    # PLANNED -> *
    tarrow(2.2, 5.25, 5.0, 6.5, "start_task()", rad=0.15)
    tarrow(3.1, 4.9, 7.5, 5.25, "complete_task()", rad=0.2)
    tarrow(2.1, 4.5, 2.1, 2.35, "skip_task()", rad=0)
    tarrow(2.8, 4.5, 4.0, 2.35, "delete_task()", rad=-0.12)
    # EXECUTING -> EXECUTED
    tarrow(7.2, 6.8, 7.8, 5.35, "complete_task()", rad=0.05)

    ax.text(
        5,
        0.55,
        "Terminal states EXECUTED, SKIPPED, DELETED are immutable (is_mutable=False). "
        "StateMachine.transition() enforces rules.",
        ha="center",
        fontsize=8,
        color=SUB,
    )

    _save(fig, "state-machine.png")


def draw_sequence() -> None:
    """Lifecycle: create → start stopwatch → stop → Notion sync (code paths)."""
    fig, ax = plt.subplots(figsize=(14, 10), dpi=DPI, facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 11)
    ax.axis("off")

    ax.text(
        7,
        10.5,
        "Task lifecycle — sequence (create → stopwatch start → stop → Notion)",
        ha="center",
        fontsize=15,
        fontweight="bold",
        color=TEXT,
    )

    actors = ["User", "OpenClaw", "FastAPI", "SQLite", "Notion"]
    xs = [1.2, 3.6, 6.0, 9.0, 11.4]
    y0, y1 = 1.0, 9.8

    for x, name in zip(xs, actors):
        ax.plot([x, x], [y0, y1], color="#334155", linewidth=1.2)
        ax.text(x, y1 + 0.15, name, ha="center", fontsize=10, fontweight="bold", color=TEXT)

    # (from_actor, to_actor, label, is_return) — indices match actors list
    steps = [
        (0, 1, "message", False),
        (1, 2, "POST /v1/create", False),
        (2, 3, "INSERT task", False),
        (2, 4, "NotionClient.sync_task() pages.create", False),
        (2, 1, "TaskCreateResponse", True),
        (1, 0, "reply", True),
        (1, 2, "POST /v1/stopwatch/start", False),
        (2, 3, "start_task + StopwatchSession; Redis active session", False),
        (2, 4, "NotionClient.sync_task() pages.update", False),
        (2, 1, "StopwatchStartResponse", True),
        (1, 2, "POST /v1/stopwatch/stop (?confirmed=…)", False),
        (2, 3, "complete_task → EXECUTED; close session", False),
        (2, 4, "NotionClient.sync_task() pages.update", False),
        (2, 1, "StopwatchStopResponse (notion_synced)", True),
        (1, 0, "summary", True),
    ]

    y = 9.35
    dy = 0.48

    for i, (a, b, msg, is_ret) in enumerate(steps):
        ya = y - i * dy
        x1, x2 = xs[a], xs[b]
        col = "#94a3b8" if is_ret else "#60a5fa"
        arr = FancyArrowPatch(
            (x1, ya),
            (x2, ya),
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=1.2,
            color=col,
            linestyle="--" if is_ret else "-",
        )
        ax.add_patch(arr)
        mx = (x1 + x2) / 2
        ax.text(mx, ya + 0.14, msg, ha="center", fontsize=6.9, color=SUB)

    ax.text(
        7,
        0.45,
        "Endpoints: tasks.py /create; stopwatch.py /stopwatch/start, /stopwatch/stop — router.py",
        ha="center",
        fontsize=8,
        color=SUB,
    )

    _save(fig, "data-flow.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw_architecture()
    draw_state_machine()
    draw_sequence()
    print("Wrote:", [p.name for p in OUT.glob("*.png")])


if __name__ == "__main__":
    main()
