"""
Generate system design PNGs (high-DPI, dark theme).

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
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

OUT = Path(__file__).resolve().parent

# Design tokens — documentation / product-diagram style
BG = "#0a0c10"
SURFACE = "#12161c"
SURFACE_EDGE = "#2a3342"
TEXT = "#eef1f6"
TEXT_MUTED = "#8b95a8"
ACCENT = "#5b9fd4"
ACCENT_SOFT = "#3d6d94"
LINE = "#4a5a70"
LINE_FAINT = "#343d4d"
MUTABLE_BORDER = "#5b9fd4"
TERMINAL_BORDER = "#5c6575"
GREEN = "#4db383"
AMBER = "#d4a24b"
VIOLET = "#9b7ed9"
ROSE = "#d67a9a"
CYAN = "#4db8d4"

DPI = 280

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"],
        "font.size": 9,
    }
)


def _save(fig, name: str) -> None:
    fig.savefig(
        OUT / name,
        dpi=DPI,
        facecolor=BG,
        edgecolor="none",
        bbox_inches="tight",
        pad_inches=0.5,
    )
    plt.close(fig)


def _node(ax, x, y, w, h, title, subtitle, *, edge, fill=SURFACE):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.03,rounding_size=0.14",
            facecolor=fill,
            edgecolor=edge,
            linewidth=1.2,
        )
    )
    ax.text(x + w / 2, y + h * 0.58, title, ha="center", va="center", fontsize=10, fontweight="600", color=TEXT)
    ax.text(x + w / 2, y + h * 0.28, subtitle, ha="center", va="center", fontsize=7.4, color=TEXT_MUTED)


def _seg_arrow(ax, points, color=LINE, dashed=False, lw=1.25):
    """Draw polyline with arrowhead at end. points: list of (x,y)."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ax.plot(
        xs,
        ys,
        color=color,
        linewidth=lw,
        linestyle="--" if dashed else "-",
        solid_capstyle="round",
        dash_capstyle="round",
        zorder=3,
    )
    x0, y0 = points[-2]
    x1, y1 = points[-1]
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=8),
        zorder=4,
    )


def draw_architecture() -> None:
    """C4-inspired container view: clear lanes, minimal crossing."""
    fig, ax = plt.subplots(figsize=(16, 9.4), dpi=DPI, facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis("off")

    ax.text(8, 9.55, "System architecture", ha="center", va="top", fontsize=18, fontweight="700", color=TEXT)
    ax.text(
        8,
        8.95,
        "Lyra Secretary — containers and primary dependencies",
        ha="center",
        va="top",
        fontsize=10,
        color=TEXT_MUTED,
    )

    # Legend (top right, compact)
    leg_x, leg_y = 11.85, 9.42
    items = [
        ("User-facing", CYAN),
        ("AI agent", VIOLET),
        ("Backend", AMBER),
        ("Storage", GREEN),
        ("Sync / UI", ROSE),
    ]
    ax.text(leg_x, leg_y + 0.28, "Layer", fontsize=8, fontweight="600", color=TEXT_MUTED)
    for i, (lab, c) in enumerate(items):
        yy = leg_y - i * 0.22
        ax.add_patch(mpatches.Rectangle((leg_x, yy), 0.28, 0.14, facecolor=c, edgecolor=SURFACE_EDGE, lw=0.4))
        ax.text(leg_x + 0.38, yy + 0.07, lab, ha="left", va="center", fontsize=7.5, color=TEXT_MUTED)

    # Swimlane labels (left rail)
    rail_x = 0.35
    for yy, cap in [(7.85, "Clients"), (5.55, "Data plane")]:
        ax.text(rail_x, yy, cap, ha="left", va="center", fontsize=8, fontweight="600", color=TEXT_MUTED, rotation=90)

    # Row 1 — external + API
    _node(ax, 1.05, 7.35, 2.05, 1.0, "Telegram", "User messaging", edge=CYAN, fill="#0e1820")
    _node(ax, 3.55, 7.35, 2.05, 1.0, "OpenClaw", "Agent & HTTP skills", edge=VIOLET, fill="#151020")
    _node(ax, 6.05, 7.25, 2.65, 1.2, "FastAPI", "REST API · /v1", edge=AMBER, fill="#1c1610")
    _node(ax, 9.15, 7.25, 2.65, 1.2, "TaskManager", "Domain writes · state machine", edge=AMBER, fill="#1c1610")

    # Backend process outline (subtle grouping)
    ax.add_patch(
        FancyBboxPatch(
            (5.75, 6.85),
            6.55,
            1.85,
            boxstyle="round,pad=0.02,rounding_size=0.25",
            facecolor="none",
            edgecolor=LINE_FAINT,
            linewidth=1,
            linestyle=(0, (4, 4)),
        )
    )
    ax.text(9.02, 8.52, "Python process · main.py lifespan", ha="center", fontsize=7, color=TEXT_MUTED)

    # Row 2 — persistence
    _node(ax, 1.15, 4.15, 2.0, 0.92, "SQLite", "Alembic · tasks & sessions", edge=GREEN, fill="#0e1814")
    _node(ax, 3.55, 4.15, 2.0, 0.92, "Redis", "Stopwatch · undo · idempotency", edge="#45b586", fill="#0e1814")
    _node(ax, 6.05, 4.05, 2.5, 1.02, "APScheduler", "Jobs: reminders · retry · overflow", edge=AMBER, fill="#1c1610")
    _node(ax, 9.05, 4.15, 2.15, 0.92, "Notion API", "Calendar database", edge=ROSE, fill="#1a1018")

    y_rail = 7.85
    _seg_arrow(ax, [(3.1, y_rail), (3.55, y_rail)], color=ACCENT)
    ax.text(3.32, y_rail + 0.14, "chat", ha="center", fontsize=7, color=TEXT_MUTED)
    _seg_arrow(ax, [(5.6, y_rail), (6.05, y_rail)], color=ACCENT)
    ax.text(5.82, y_rail + 0.14, "HTTP", ha="center", fontsize=7, color=TEXT_MUTED)
    _seg_arrow(ax, [(8.7, y_rail), (9.15, y_rail)], color=ACCENT)
    ax.text(8.92, y_rail + 0.14, "services", ha="center", fontsize=7, color=TEXT_MUTED)

    # TaskManager → SQLite / Redis / Notion only (TaskManager does not invoke APScheduler)
    tcx, tcy = 10.47, 7.25
    stem_y = 5.95
    _seg_arrow(ax, [(tcx, tcy), (tcx, stem_y)], color=LINE)

    targets = [
        (2.15, 5.08, 4.15 + 0.46),
        (4.55, 4.92, 4.15 + 0.46),
        (10.12, 5.08, 4.15 + 0.46),
    ]
    bus_levels = [5.52, 5.35, 5.58]
    labels = ["SQLAlchemy", "redis client", "Notion API"]
    for (tx, _mid, ty), bus_y, lab in zip(targets, bus_levels, labels):
        _seg_arrow(ax, [(tcx, stem_y), (tcx, bus_y), (tx, bus_y), (tx, ty)], color=LINE)
        ax.text((tcx + tx) / 2, bus_y + 0.1, lab, ha="center", fontsize=6.8, color=TEXT_MUTED)

    # APScheduler jobs (same process): poll DB / Redis, retry Notion — separate from TaskManager
    sx = 7.3
    _seg_arrow(ax, [(sx, 4.05), (2.15, 4.55)], color=ACCENT_SOFT, dashed=True, lw=1.05)
    _seg_arrow(ax, [(sx, 4.05), (4.55, 4.55)], color=ACCENT_SOFT, dashed=True, lw=1.05)
    _seg_arrow(ax, [(sx, 4.05), (10.12, 4.55)], color=ACCENT_SOFT, dashed=True, lw=1.05)
    ax.text(sx, 3.72, "APScheduler → stores", ha="center", fontsize=7, color=TEXT_MUTED)

    ax.text(
        8,
        1.05,
        "NotionClient.sync_task() · archive_page()   |   "
        "router mounts: parse, tasks, stopwatch, query, undo, notifications, health",
        ha="center",
        fontsize=7.6,
        color=TEXT_MUTED,
    )

    _save(fig, "architecture.png")


def draw_state_machine() -> None:
    """UML-style: initial pseudostate, orthogonal spacing, reference table."""
    fig, ax = plt.subplots(figsize=(13.5, 8.4), dpi=DPI, facecolor=BG)
    ax.set_facecolor(BG)
    ax.axis("off")
    ax.set_xlim(-0.5, 12.8)
    ax.set_ylim(-0.5, 9.5)

    ax.text(6.15, 9.05, "Task state machine", ha="center", va="top", fontsize=18, fontweight="700", color=TEXT)
    ax.text(
        6.15,
        8.45,
        "state_machine.py (TRANSITIONS) · task_manager.py (callers)",
        ha="center",
        va="top",
        fontsize=10,
        color=TEXT_MUTED,
    )

    def st(x, y, name, *, terminal=False):
        ed = TERMINAL_BORDER if terminal else MUTABLE_BORDER
        ls = "--" if terminal else "-"
        fill = "#151a22" if terminal else SURFACE
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                2.45,
                1.0,
                boxstyle="round,pad=0.03,rounding_size=0.16",
                facecolor=fill,
                edgecolor=ed,
                linewidth=1.25,
                linestyle=ls,
            )
        )
        ax.text(x + 1.225, y + 0.62, name, ha="center", va="center", fontsize=11.5, fontweight="600", color=TEXT)
        ax.text(
            x + 1.225,
            y + 0.28,
            "terminal" if terminal else "mutable",
            ha="center",
            va="center",
            fontsize=7.5,
            color=TEXT_MUTED,
            style="italic",
        )

    # Initial → PLANNED
    init_x, init_y = 0.55, 5.05
    ax.add_patch(Circle((init_x, init_y), 0.12, facecolor=TEXT, edgecolor=TEXT, zorder=5))
    st(1.15, 4.55, "PLANNED", terminal=False)
    _seg_arrow(ax, [(init_x + 0.12, init_y), (1.15, 5.05)], color=LINE, lw=1.2)
    ax.text(0.85, 5.45, "new Task", ha="center", fontsize=7, color=TEXT_MUTED)

    st(4.95, 6.75, "EXECUTING", terminal=False)
    st(8.85, 4.55, "EXECUTED", terminal=True)
    st(1.15, 1.35, "SKIPPED", terminal=True)
    st(4.85, 1.35, "DELETED", terminal=True)

    def trans(x1, y1, x2, y2, label, rad=0.18):
        arr = FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=1.25,
            color=LINE,
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=3,
            shrinkB=3,
        )
        ax.add_patch(arr)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx + rad * 1.4, my + 0.35, label, ha="center", fontsize=8.2, color=TEXT, fontweight="500")

    trans(3.6, 5.25, 4.95, 7.5, "start_task()", rad=0.2)
    trans(6.2, 5.45, 8.85, 5.45, "complete_task()", rad=0.05)
    trans(2.37, 4.55, 2.37, 2.35, "skip_task()", rad=0)
    trans(3.5, 4.75, 5.1, 2.35, "delete_task()", rad=-0.12)
    trans(7.4, 7.35, 8.85, 5.55, "complete_task()", rad=0.1)

    # Reference table in a panel
    ax.add_patch(
        FancyBboxPatch(
            (0.55, 0.15),
            11.2,
            0.95,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            facecolor=SURFACE,
            edgecolor=SURFACE_EDGE,
            linewidth=1,
        )
    )
    ax.text(6.15, 0.92, "Transition summary", ha="center", fontsize=8, fontweight="600", color=TEXT_MUTED)
    lines = (
        "PLANNED → EXECUTING   start_task()          |  PLANNED → SKIPPED     skip_task()\n"
        "PLANNED → EXECUTED    complete_task()       |  PLANNED → DELETED    delete_task()\n"
        "EXECUTING → EXECUTED  complete_task()  (StopwatchManager.stop)"
    )
    ax.text(6.15, 0.48, lines, ha="center", va="center", fontsize=8, color=TEXT, family="monospace")

    _save(fig, "state-machine.png")


def draw_sequence() -> None:
    """Six actors; phased bands; Redis explicit."""
    fig, ax = plt.subplots(figsize=(17, 12), dpi=DPI, facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 17)
    ax.set_ylim(0, 12.5)
    ax.axis("off")

    ax.text(8.5, 12.05, "Task lifecycle sequence", ha="center", va="top", fontsize=18, fontweight="700", color=TEXT)
    ax.text(
        8.5,
        11.45,
        "Create → start stopwatch → stop (incl. Notion sync on write paths)",
        ha="center",
        va="top",
        fontsize=10,
        color=TEXT_MUTED,
    )

    actors = ["User", "OpenClaw", "FastAPI", "SQLite", "Redis", "Notion"]
    xs = [1.2, 3.15, 5.4, 8.0, 10.6, 13.2]
    y_top, y_bot = 10.85, 1.55

    for x, name in zip(xs, actors):
        ax.add_patch(
            FancyBboxPatch(
                (x - 0.72, y_top + 0.08),
                1.44,
                0.5,
                boxstyle="round,pad=0.02,rounding_size=0.22",
                facecolor=SURFACE,
                edgecolor=SURFACE_EDGE,
                linewidth=1,
            )
        )
        ax.text(x, y_top + 0.33, name, ha="center", va="center", fontsize=9.5, fontweight="600", color=TEXT)
        ax.plot([x, x], [y_top, y_bot], color=SURFACE_EDGE, lw=1.1)

    # Phase bands
    bands = [(10.75, 9.05, "1  Create"), (8.85, 6.35, "2  Start stopwatch"), (6.15, 1.85, "3  Stop & sync")]
    for y_hi, y_lo, title in bands:
        ax.axhspan(y_lo, y_hi, facecolor=SURFACE, alpha=0.4, zorder=0, edgecolor="none")
        ax.text(0.38, (y_hi + y_lo) / 2, title, ha="center", va="center", fontsize=8.5, fontweight="700", color=TEXT_MUTED, rotation=90)

    # (from, to, label, return?)
    steps = [
        (0, 1, "message", False),
        (1, 2, "POST /v1/create", False),
        (2, 3, "INSERT task", False),
        (2, 5, "sync_task() · create page", False),
        (2, 1, "TaskCreateResponse", True),
        (1, 0, "reply", True),
        (1, 2, "POST /v1/stopwatch/start", False),
        (2, 3, "start_task() · INSERT session", False),
        (2, 4, "SET active stopwatch", False),
        (2, 5, "sync_task() · update", False),
        (2, 1, "StopwatchStartResponse", True),
        (1, 2, "POST /v1/stopwatch/stop", False),
        (2, 3, "complete_task() · close session", False),
        (2, 5, "sync_task() · update", False),
        (2, 1, "StopwatchStopResponse", True),
        (1, 0, "summary", True),
    ]

    y0 = 10.35
    dy = 0.505
    for i, (a, b, msg, is_ret) in enumerate(steps):
        ya = y0 - i * dy
        x1, x2 = xs[a], xs[b]
        col = TEXT_MUTED if is_ret else ACCENT
        arr = FancyArrowPatch(
            (x1, ya),
            (x2, ya),
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=1.25 if not is_ret else 1.05,
            color=col,
            linestyle="--" if is_ret else "-",
            shrinkA=5,
            shrinkB=5,
        )
        ax.add_patch(arr)
        ax.text(
            0.32,
            ya,
            str(i + 1),
            ha="center",
            va="center",
            fontsize=7,
            fontweight="700",
            color=BG,
            bbox=dict(boxstyle="circle,pad=0.22", facecolor=ACCENT_SOFT, edgecolor="none"),
        )
        ax.text((x1 + x2) / 2, ya + 0.17, msg, ha="center", fontsize=7.7, color=TEXT if not is_ret else TEXT_MUTED)

    custom = [
        Line2D([0], [0], color=ACCENT, lw=2, label="Request / async call"),
        Line2D([0], [0], color=TEXT_MUTED, lw=1.5, linestyle="--", label="Response"),
    ]
    ax.legend(
        handles=custom,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.03),
        ncol=2,
        frameon=True,
        facecolor=SURFACE,
        edgecolor=SURFACE_EDGE,
        fontsize=8,
        labelcolor=TEXT_MUTED,
    )

    ax.text(
        8.5,
        0.72,
        "tasks.py · create  ·  stopwatch.py · /stopwatch/start · /stopwatch/stop",
        ha="center",
        fontsize=7.8,
        color=TEXT_MUTED,
    )

    _save(fig, "data-flow.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw_architecture()
    draw_state_machine()
    draw_sequence()
    print("Wrote:", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
