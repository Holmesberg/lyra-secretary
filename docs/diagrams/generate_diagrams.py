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
    """Clients · backend runtime (incl. APScheduler) · data & integrations."""
    fig, ax = plt.subplots(figsize=(16, 10.5), dpi=DPI, facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10.8)
    ax.axis("off")

    ax.text(8, 10.35, "System architecture", ha="center", va="top", fontsize=18, fontweight="700", color=TEXT)
    ax.text(
        8,
        9.72,
        "Lyra Secretary — containers and dependencies",
        ha="center",
        va="top",
        fontsize=10,
        color=TEXT_MUTED,
    )

    # Legend (top right)
    leg_x, leg_y = 11.9, 10.18
    items = [
        ("User-facing", CYAN),
        ("AI agent", VIOLET),
        ("Backend", AMBER),
        ("Storage", GREEN),
        ("External sync", ROSE),
    ]
    ax.text(leg_x, leg_y + 0.28, "Layer", fontsize=8, fontweight="600", color=TEXT_MUTED)
    for i, (lab, c) in enumerate(items):
        yy = leg_y - i * 0.22
        ax.add_patch(mpatches.Rectangle((leg_x, yy), 0.28, 0.14, facecolor=c, edgecolor=SURFACE_EDGE, lw=0.4))
        ax.text(leg_x + 0.38, yy + 0.07, lab, ha="left", va="center", fontsize=7.5, color=TEXT_MUTED)

    # Swimlane labels — three tiers
    rail_x = 0.32
    lanes = [(8.35, "Clients"), (6.55, "Backend\nruntime"), (3.55, "Data &\nintegrations")]
    for yy, cap in lanes:
        ax.text(rail_x, yy, cap, ha="left", va="center", fontsize=8, fontweight="600", color=TEXT_MUTED, rotation=90)

    # --- Clients ---
    _node(ax, 1.2, 7.85, 2.1, 1.0, "Telegram", "User messaging", edge=CYAN, fill="#0e1820")
    _node(ax, 3.85, 7.85, 2.1, 1.0, "OpenClaw", "Agent & HTTP skills", edge=VIOLET, fill="#151020")

    # --- Backend runtime (single process): FastAPI + TaskManager + APScheduler ---
    bx, by, bw, bh = 5.15, 5.05, 10.35, 3.65
    ax.add_patch(
        FancyBboxPatch(
            (bx, by),
            bw,
            bh,
            boxstyle="round,pad=0.03,rounding_size=0.28",
            facecolor="#0d1016",
            edgecolor=LINE_FAINT,
            linewidth=1.15,
            linestyle=(0, (5, 4)),
        )
    )
    ax.text(bx + bw / 2, by + bh - 0.28, "Backend process · Uvicorn + main.py lifespan", ha="center", fontsize=7.8, color=TEXT_MUTED)

    _node(ax, 5.55, 7.35, 2.75, 1.15, "FastAPI", "REST · /v1/*", edge=AMBER, fill="#1c1610")
    _node(ax, 8.85, 7.35, 2.85, 1.15, "TaskManager", "Mutations · state machine", edge=AMBER, fill="#1c1610")
    _node(ax, 6.85, 5.35, 3.4, 1.05, "APScheduler", "Reminders · Notion retry · timer overflow", edge=AMBER, fill="#1c1610")

    y_entry = 8.35
    # Telegram → OpenClaw → FastAPI → TaskManager (horizontal spine)
    _seg_arrow(ax, [(3.3, y_entry), (3.85, y_entry)], color=ACCENT)
    _seg_arrow(ax, [(5.95, y_entry), (5.55, y_entry)], color=ACCENT)
    ax.text(4.75, y_entry + 0.15, "chat", ha="center", fontsize=7, color=TEXT_MUTED)
    _seg_arrow(ax, [(8.3, y_entry), (8.85, y_entry)], color=ACCENT)
    ax.text(7.15, y_entry + 0.15, "in-process", ha="center", fontsize=7, color=TEXT_MUTED)

    # --- Data plane (spaced) ---
    _node(ax, 1.35, 2.35, 2.35, 1.0, "SQLite", "ORM · source of truth", edge=GREEN, fill="#0e1814")
    _node(ax, 4.55, 2.35, 2.35, 1.0, "Redis", "Stopwatch · undo · idempotency", edge="#45b586", fill="#0e1814")
    _node(ax, 11.05, 2.35, 2.35, 1.0, "Notion API", "External calendar DB", edge=ROSE, fill="#1a1018")

    # TaskManager → stores (writes / reads on request path)
    tcx = 10.25
    stem_top = 7.35
    stem_y = 4.85
    _seg_arrow(ax, [(tcx, stem_top), (tcx, stem_y)], color=LINE)
    ax.text(tcx + 0.42, 6.0, "request path", ha="left", fontsize=7, color=TEXT_MUTED, rotation=90, va="center")

    targets = [(2.52, 5.0, 3.35), (6.0, 4.85, 3.35), (12.22, 5.0, 3.35)]
    bus_y = [5.15, 4.95, 5.25]
    labs = ["SQLAlchemy", "redis-py", "HTTPS"]
    for (tx, mid, ty), by, lb in zip(targets, bus_y, labs):
        _seg_arrow(ax, [(tcx, stem_y), (tcx, by), (tx, by), (tx, ty)], color=LINE)
        ax.text((tcx + tx) / 2, by + 0.12, lb, ha="center", fontsize=7, color=TEXT_MUTED)

    # APScheduler → same infrastructure (read-only / retry jobs — does not own data)
    sx, sy = 8.55, 5.35
    _seg_arrow(ax, [(sx, sy), (2.52, 3.35)], color=ACCENT_SOFT, dashed=True, lw=1.1)
    _seg_arrow(ax, [(sx, sy - 0.15), (6.0, 3.35)], color=ACCENT_SOFT, dashed=True, lw=1.1)
    _seg_arrow(ax, [(sx + 0.4, sy), (12.22, 3.35)], color=ACCENT_SOFT, dashed=True, lw=1.1)
    ax.text(8.55, 4.72, "scheduled jobs: query tasks · scan queues · retry sync", ha="center", fontsize=7, color=TEXT_MUTED)

    _save(fig, "architecture.png")


def draw_state_machine() -> None:
    """PLANNED center-left (entry); EXECUTING mid-flow; no PLANNED→EXECUTED shortcut."""
    fig, ax = plt.subplots(figsize=(13.5, 7.8), dpi=DPI, facecolor=BG)
    ax.set_facecolor(BG)
    ax.axis("off")
    ax.set_xlim(-0.2, 12.5)
    ax.set_ylim(0.5, 8.8)

    ax.text(6.2, 8.35, "Task state machine", ha="center", va="top", fontsize=18, fontweight="700", color=TEXT)
    ax.text(
        6.2,
        7.75,
        "PLANNED → EXECUTING → EXECUTED is the completion path (stopwatch). "
        "PLANNED → EXECUTED is not allowed.",
        ha="center",
        va="top",
        fontsize=9,
        color=TEXT_MUTED,
    )

    def st(x, y, name, *, terminal=False):
        ed = TERMINAL_BORDER if terminal else MUTABLE_BORDER
        ls = "--" if terminal else "-"
        fill = "#151a22" if terminal else SURFACE
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                2.35,
                0.95,
                boxstyle="round,pad=0.03,rounding_size=0.16",
                facecolor=fill,
                edgecolor=ed,
                linewidth=1.25,
                linestyle=ls,
            )
        )
        ax.text(x + 1.175, y + 0.58, name, ha="center", va="center", fontsize=11, fontweight="600", color=TEXT)
        ax.text(
            x + 1.175,
            y + 0.28,
            "terminal" if terminal else "mutable",
            ha="center",
            va="center",
            fontsize=7.5,
            color=TEXT_MUTED,
            style="italic",
        )

    # Initial → PLANNED (center-left hub)
    init_x, init_y = 0.65, 4.85
    ax.add_patch(Circle((init_x, init_y), 0.11, facecolor=TEXT, edgecolor=TEXT, zorder=5))
    st(1.35, 4.35, "PLANNED", terminal=False)
    _seg_arrow(ax, [(init_x + 0.11, init_y), (1.35, 4.82)], color=LINE, lw=1.2)
    ax.text(0.95, 5.35, "new Task", ha="center", fontsize=7, color=TEXT_MUTED)

    # Middle state to the right — same band as PLANNED (not elevated as “primary”)
    st(4.45, 4.35, "EXECUTING", terminal=False)
    st(7.55, 4.35, "EXECUTED", terminal=True)
    st(1.35, 1.45, "SKIPPED", terminal=True)
    st(4.35, 1.45, "DELETED", terminal=True)

    def trans(x1, y1, x2, y2, label, rad=0.0):
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
        ax.text(mx, my + 0.28, label, ha="center", fontsize=8.2, color=TEXT, fontweight="500")

    trans(3.7, 4.82, 4.45, 4.82, "start_task()", rad=0)
    trans(6.8, 4.82, 7.55, 4.82, "complete_task()", rad=0)
    trans(2.52, 4.35, 2.52, 2.4, "skip_task()", rad=0)
    trans(3.55, 4.35, 4.55, 2.4, "delete_task()", rad=-0.08)

    _save(fig, "state-machine.png")


def draw_sequence() -> None:
    """Full path: create, start, stop (Redis GET/DEL), optional undo. Step # column has left margin."""
    fig, ax = plt.subplots(figsize=(18.5, 14.5), dpi=DPI, facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(-0.8, 18.2)
    ax.set_ylim(0, 14.2)
    ax.axis("off")

    ax.text(9.1, 13.65, "Task lifecycle sequence", ha="center", va="top", fontsize=18, fontweight="700", color=TEXT)
    ax.text(
        9.1,
        13.05,
        "Create → start stopwatch → stop (Redis GET/DEL) → optional undo (within 30s)",
        ha="center",
        va="top",
        fontsize=10,
        color=TEXT_MUTED,
    )

    actors = ["User", "OpenClaw", "FastAPI", "SQLite", "Redis", "Notion"]
    xs = [2.15, 4.05, 6.05, 8.75, 11.05, 13.65]
    y_top, y_bot = 12.45, 1.35

    for x, name in zip(xs, actors):
        ax.add_patch(
            FancyBboxPatch(
                (x - 0.78, y_top + 0.06),
                1.56,
                0.52,
                boxstyle="round,pad=0.02,rounding_size=0.22",
                facecolor=SURFACE,
                edgecolor=SURFACE_EDGE,
                linewidth=1,
            )
        )
        ax.text(x, y_top + 0.32, name, ha="center", va="center", fontsize=9.5, fontweight="600", color=TEXT)
        ax.plot([x, x], [y_top, y_bot], color=SURFACE_EDGE, lw=1.1)

    # Phase bands (y_hi, y_lo, label)
    bands = [
        (12.35, 10.55, "1  Create"),
        (10.35, 8.35, "2  Start"),
        (8.15, 3.85, "3  Stop"),
        (3.65, 1.45, "4  Undo (opt.)"),
    ]
    for y_hi, y_lo, title in bands:
        ax.axhspan(y_lo, y_hi, facecolor=SURFACE, alpha=0.38, zorder=0)
        ax.text(0.55, (y_hi + y_lo) / 2, title, ha="center", va="center", fontsize=9, fontweight="700", color=TEXT_MUTED, rotation=90)

    # (from, to, label, is_return)
    steps = [
        (0, 1, "message", False),
        (1, 2, "POST /v1/create", False),
        (2, 3, "INSERT task", False),
        (2, 5, "sync_task() · create page", False),
        (2, 1, "TaskCreateResponse", True),
        (1, 0, "reply", True),
        (1, 2, "POST /v1/stopwatch/start", False),
        (2, 3, "start_task() · INSERT session", False),
        (2, 4, "SET stopwatch:active:{user}", False),
        (2, 5, "sync_task() · update", False),
        (2, 1, "StopwatchStartResponse", True),
        (1, 2, "POST /v1/stopwatch/stop", False),
        (2, 4, "GET stopwatch:active (resolve session)", False),
        (2, 3, "complete_task() · close StopwatchSession", False),
        (2, 4, "DEL stopwatch:active:{user}", False),
        (2, 5, "sync_task() · update", False),
        (2, 1, "StopwatchStopResponse", True),
        (1, 0, "summary", True),
        (0, 1, "undo intent", False),
        (1, 2, "POST /v1/undo", False),
        (2, 4, "GET/DEL undo:{task_id}", False),
        (2, 3, "delete_task (undo create) or restore row", False),
        (2, 5, "archive_page / sync (undo path)", False),
        (2, 1, "UndoResponse", True),
        (1, 0, "ack", True),
    ]

    y0 = 12.05
    dy = 0.42
    step_x = 1.15
    for i, (a, b, msg, is_ret) in enumerate(steps):
        ya = y0 - i * dy
        x1, x2 = xs[a], xs[b]
        col = TEXT_MUTED if is_ret else ACCENT
        arr = FancyArrowPatch(
            (x1, ya),
            (x2, ya),
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=1.2 if not is_ret else 1.0,
            color=col,
            linestyle="--" if is_ret else "-",
            shrinkA=5,
            shrinkB=5,
        )
        ax.add_patch(arr)
        ax.text(
            step_x,
            ya,
            str(i + 1),
            ha="center",
            va="center",
            fontsize=8,
            fontweight="700",
            color=TEXT,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#1e2a38", edgecolor=ACCENT_SOFT, linewidth=0.8),
        )
        ax.text((x1 + x2) / 2, ya + 0.16, msg, ha="center", fontsize=7.6, color=TEXT if not is_ret else TEXT_MUTED)

    custom = [
        Line2D([0], [0], color=ACCENT, lw=2, label="Call"),
        Line2D([0], [0], color=TEXT_MUTED, lw=1.5, linestyle="--", label="Return"),
    ]
    ax.legend(
        handles=custom,
        loc="lower center",
        bbox_to_anchor=(0.52, 0.02),
        ncol=2,
        frameon=True,
        facecolor=SURFACE,
        edgecolor=SURFACE_EDGE,
        fontsize=8,
        labelcolor=TEXT_MUTED,
    )

    ax.text(
        9.1,
        0.75,
        "undo.py · POST /v1/undo  ·  redis_client.py · stopwatch + undo keys",
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
