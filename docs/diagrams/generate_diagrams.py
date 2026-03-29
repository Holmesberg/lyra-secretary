"""
Generate system design PNGs (high-DPI, dark theme).

Layout rules (project convention):
- No nested boxes overlapping component boundaries
- Every arrow has a visible label
- ≤3 levels of visual hierarchy (title → swimlane → nodes)
- Architecture: flat rows + horizontal swimlanes only
- State machine: happy path horizontal; terminal states in a lower band
- Main sequence: ≤15 steps; undo is data-flow-undo.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

OUT = Path(__file__).resolve().parent

BG = "#0a0c10"
SURFACE = "#12161c"
LANE_BG = "#0e1218"
TEXT = "#eef1f6"
TEXT_MUTED = "#8b95a8"
ACCENT = "#5b9fd4"
ACCENT_SOFT = "#3d6d94"
LINE = "#4a5a70"
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
    fig.savefig(OUT / name, dpi=DPI, facecolor=BG, edgecolor="none", bbox_inches="tight", pad_inches=0.45)
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
    ax.text(x + w / 2, y + h * 0.28, subtitle, ha="center", va="center", fontsize=7.2, color=TEXT_MUTED)


def _arrow_labeled(ax, x1, y1, x2, y2, label, *, color=LINE, dashed=False, lw=1.15):
    ls = "--" if dashed else "-"
    arr = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle="-|>",
        mutation_scale=8,
        linewidth=lw,
        color=color,
        linestyle=ls,
        connectionstyle="arc3,rad=0",
        shrinkA=2,
        shrinkB=2,
    )
    ax.add_patch(arr)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    ax.text(mx, my + 0.16, label, ha="center", fontsize=6.7, color=TEXT_MUTED)


def _seg_arrow(ax, points, color=LINE, dashed=False, lw=1.15):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ax.plot(
        xs,
        ys,
        color=color,
        linewidth=lw,
        linestyle="--" if dashed else "-",
        solid_capstyle="round",
        zorder=3,
    )
    ax.annotate(
        "",
        xy=(points[-1][0], points[-1][1]),
        xytext=(points[-2][0], points[-2][1]),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=7),
        zorder=4,
    )


def draw_architecture() -> None:
    """
    Flat v1-style: 3 horizontal swimlanes, no nested group boxes.
    Row 2 = FastAPI + TaskManager + APScheduler only; row 3 = SQLite + Redis + Notion.
    Every edge has a label.
    """
    fig, ax = plt.subplots(figsize=(15.5, 8.4), dpi=DPI, facecolor=BG)
    ax.set_xlim(0, 15.5)
    ax.set_ylim(0, 8.4)
    ax.axis("off")

    ax.text(7.75, 8.1, "System architecture", ha="center", va="top", fontsize=17, fontweight="700", color=TEXT)

    for y_lo, y_hi in [(6.25, 8.0), (3.55, 6.05), (0.85, 3.25)]:
        ax.axhspan(y_lo, y_hi, facecolor=LANE_BG, alpha=0.5, zorder=0)
    ax.text(0.45, 7.12, "Clients", ha="left", va="center", fontsize=8.5, fontweight="600", color=TEXT_MUTED)
    ax.text(0.45, 4.85, "Backend", ha="left", va="center", fontsize=8.5, fontweight="600", color=TEXT_MUTED)
    ax.text(0.45, 2.05, "Data & external", ha="left", va="center", fontsize=8.5, fontweight="600", color=TEXT_MUTED)

    _node(ax, 2.0, 6.45, 2.1, 0.92, "Telegram", "User chat", edge=CYAN, fill="#0e1820")
    _node(ax, 4.75, 6.45, 2.1, 0.92, "OpenClaw", "Agent / skills", edge=VIOLET, fill="#151020")
    _node(ax, 1.55, 3.95, 2.45, 0.92, "FastAPI", "REST /v1", edge=AMBER, fill="#1c1610")
    _node(ax, 4.45, 3.95, 2.55, 0.92, "TaskManager", "Domain writes", edge=AMBER, fill="#1c1610")
    _node(ax, 7.55, 3.95, 2.75, 0.92, "APScheduler", "Background jobs", edge=AMBER, fill="#1c1610")
    _node(ax, 2.0, 1.05, 2.2, 0.88, "SQLite", "Persistence", edge=GREEN, fill="#0e1814")
    _node(ax, 4.85, 1.05, 2.2, 0.88, "Redis", "Ephemeral state", edge="#45b586", fill="#0e1814")
    _node(ax, 7.75, 1.05, 2.35, 0.88, "Notion", "Calendar DB", edge=ROSE, fill="#1a1018")

    y_c = 6.91
    _arrow_labeled(ax, 4.1, y_c, 4.75, y_c, "chat")
    # OpenClaw → FastAPI (orthogonal, single label)
    _seg_arrow(ax, [(6.85, y_c), (6.85, 5.35), (2.75, 5.35), (2.75, 4.87)], color=ACCENT)
    ax.text(5.0, 5.5, "HTTP /v1", ha="center", fontsize=6.8, color=TEXT_MUTED)
    _arrow_labeled(ax, 4.0, 4.45, 4.45, 4.45, "calls")
    _arrow_labeled(ax, 7.0, 4.45, 7.55, 4.45, "in-process")

    tcx = 5.72
    y_bus = 2.48
    _seg_arrow(ax, [(tcx, 3.95), (tcx, y_bus)], color=LINE)
    ax.text(tcx + 0.28, 3.2, "read/write", fontsize=6.7, color=TEXT_MUTED, rotation=90, va="center")
    for tx, lab in [(3.1, "SQLAlchemy"), (5.95, "redis-py"), (8.92, "HTTPS")]:
        _seg_arrow(ax, [(tcx, y_bus), (tx, y_bus), (tx, 1.93)], color=LINE)
        ax.text((tcx + tx) / 2, y_bus + 0.12, lab, ha="center", fontsize=6.7, color=TEXT_MUTED)

    # APScheduler: own bus below TaskManager (dashed = jobs read/retry, not owning data)
    scx = 8.92
    sch_y = 2.22
    _seg_arrow(ax, [(scx, 3.95), (scx, sch_y)], color=ACCENT_SOFT, dashed=True, lw=1.05)
    for tx, lab in [(3.1, "SQL query"), (5.95, "key scan"), (8.92, "retry sync")]:
        _seg_arrow(ax, [(scx, sch_y), (tx, sch_y), (tx, 1.93)], color=ACCENT_SOFT, dashed=True, lw=1.05)
        ax.text((scx + tx) / 2, sch_y + 0.11, lab, ha="center", fontsize=6.5, color=TEXT_MUTED)

    # Agent ↔ API: poll and response (dashed, labels)
    _seg_arrow(ax, [(5.35, 6.35), (5.35, 5.5), (2.75, 5.5), (2.75, 4.87)], color=ACCENT_SOFT, dashed=True, lw=1.0)
    ax.text(3.85, 5.65, "GET /notifications/pending", ha="center", fontsize=6.5, color=TEXT_MUTED)
    _seg_arrow(ax, [(2.75, 4.5), (2.75, 5.65), (5.5, 5.65), (5.5, 6.35)], color=ACCENT_SOFT, dashed=True, lw=1.0)
    ax.text(4.0, 5.95, "JSON responses", ha="center", fontsize=6.5, color=TEXT_MUTED)

    _save(fig, "architecture.png")


def draw_state_machine() -> None:
    """Happy path horizontal; terminal band below with grouping; subtitle unchanged."""
    fig, ax = plt.subplots(figsize=(12.5, 6.2), dpi=DPI, facecolor=BG)
    ax.set_xlim(0, 12.5)
    ax.set_ylim(0.3, 6.0)
    ax.axis("off")

    ax.text(6.25, 5.75, "Task state machine", ha="center", va="top", fontsize=16, fontweight="700", color=TEXT)
    ax.text(
        6.25,
        5.2,
        "PLANNED → EXECUTING → EXECUTED is the completion path (stopwatch). "
        "PLANNED → EXECUTED is not allowed.",
        ha="center",
        va="top",
        fontsize=8.8,
        color=TEXT_MUTED,
    )

    # Upper band: mutable flow
    ax.axhspan(3.15, 4.85, facecolor=LANE_BG, alpha=0.6, zorder=0)
    ax.text(0.45, 4.0, "Flow", ha="left", va="center", fontsize=8, fontweight="600", color=TEXT_MUTED)

    def st(x, y, name, *, terminal=False):
        ed = TERMINAL_BORDER if terminal else MUTABLE_BORDER
        ls = "--" if terminal else "-"
        fill = "#151a22" if terminal else SURFACE
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                2.2,
                0.88,
                boxstyle="round,pad=0.03,rounding_size=0.14",
                facecolor=fill,
                edgecolor=ed,
                linewidth=1.15,
                linestyle=ls,
            )
        )
        ax.text(x + 1.1, y + 0.52, name, ha="center", va="center", fontsize=10.5, fontweight="600", color=TEXT)
        ax.text(x + 1.1, y + 0.25, "terminal" if terminal else "mutable", ha="center", fontsize=7, color=TEXT_MUTED, style="italic")

    init_x, init_y = 0.65, 3.95
    ax.add_patch(Circle((init_x, init_y), 0.1, facecolor=TEXT, edgecolor=TEXT, zorder=5))
    st(1.25, 3.55, "PLANNED", terminal=False)
    _arrow_labeled(ax, init_x + 0.1, init_y, 1.25, 3.99, "create")
    st(4.0, 3.55, "EXECUTING", terminal=False)
    st(6.75, 3.55, "EXECUTED", terminal=True)

    _arrow_labeled(ax, 3.45, 3.99, 4.0, 3.99, "start_task()")
    _arrow_labeled(ax, 6.2, 3.99, 6.75, 3.99, "complete_task()")

    # Terminal band — grouped, not orphaned
    ax.axhspan(0.55, 2.35, facecolor=LANE_BG, alpha=0.75, zorder=0)
    ax.text(0.45, 1.45, "Terminal\n(from PLANNED)", ha="left", va="center", fontsize=8, fontweight="600", color=TEXT_MUTED)
    ax.add_patch(
        FancyBboxPatch(
            (1.0, 0.7),
            7.8,
            1.5,
            boxstyle="round,pad=0.02,rounding_size=0.2",
            facecolor="none",
            edgecolor=LINE,
            linewidth=1,
            linestyle=(0, (5, 3)),
        )
    )
    ax.text(4.9, 1.95, "Skip / delete without executing", ha="center", fontsize=7.5, color=TEXT_MUTED)

    st(2.1, 1.05, "SKIPPED", terminal=True)
    st(5.35, 1.05, "DELETED", terminal=True)
    _arrow_labeled(ax, 2.45, 3.55, 2.45, 1.93, "skip_task()")
    _arrow_labeled(ax, 3.45, 3.55, 5.8, 1.93, "delete_task()")

    _save(fig, "state-machine.png")


def draw_sequence_main() -> None:
    """Main lifecycle: exactly 15 steps, tight vertical spacing."""
    fig, ax = plt.subplots(figsize=(17.5, 9.2), dpi=DPI, facecolor=BG)
    ax.set_xlim(-0.5, 17.8)
    ax.set_ylim(0, 9.2)
    ax.axis("off")

    ax.text(8.75, 8.75, "Task lifecycle — main path", ha="center", va="top", fontsize=16, fontweight="700", color=TEXT)
    ax.text(
        8.75,
        8.25,
        "Create → start stopwatch → stop (≤15 steps)",
        ha="center",
        va="top",
        fontsize=9.5,
        color=TEXT_MUTED,
    )

    actors = ["User", "OpenClaw", "FastAPI", "SQLite", "Redis", "Notion"]
    xs = [2.0, 3.85, 5.75, 8.35, 10.75, 13.25]
    y_top, y_bot = 7.85, 0.95

    for x, name in zip(xs, actors):
        ax.add_patch(
            FancyBboxPatch(
                (x - 0.75, y_top + 0.05),
                1.5,
                0.48,
                boxstyle="round,pad=0.02,rounding_size=0.2",
                facecolor=SURFACE,
                edgecolor="#2a3342",
                linewidth=1,
            )
        )
        ax.text(x, y_top + 0.29, name, ha="center", va="center", fontsize=9, fontweight="600", color=TEXT)
        ax.plot([x, x], [y_top, y_bot], color="#2a3342", lw=1.05)

    for y_hi, y_lo in [(7.65, 5.85), (5.65, 3.25), (3.05, 1.05)]:
        ax.axhspan(y_lo, y_hi, facecolor=LANE_BG, alpha=0.35, zorder=0)

    # Main path: ≤15 steps (indices 0=User 1=OC 2=F 3=S 4=R 5=N)
    steps = [
        (0, 1, "message", False),
        (1, 2, "POST /v1/create", False),
        (2, 3, "INSERT task", False),
        (2, 5, "sync_task() create", False),
        (2, 1, "TaskCreateResponse → User", True),
        (1, 2, "POST /v1/stopwatch/start", False),
        (2, 3, "start_task + INSERT session", False),
        (2, 4, "SET stopwatch:active", False),
        (2, 5, "sync_task() update", False),
        (2, 1, "StopwatchStartResponse", True),
        (1, 2, "POST /v1/stopwatch/stop", False),
        (2, 4, "GET active + complete + DEL key", False),
        (2, 5, "sync_task() update", False),
        (2, 1, "StopwatchStopResponse → User", True),
    ]
    assert len(steps) <= 15

    y0 = 7.55
    dy = 0.38
    step_x = 0.95
    for i, (a, b, msg, is_ret) in enumerate(steps):
        ya = y0 - i * dy
        x1, x2 = xs[a], xs[b]
        col = TEXT_MUTED if is_ret else ACCENT
        arr = FancyArrowPatch(
            (x1, ya),
            (x2, ya),
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=1.15 if not is_ret else 0.95,
            color=col,
            linestyle="--" if is_ret else "-",
            shrinkA=4,
            shrinkB=4,
        )
        ax.add_patch(arr)
        ax.text(
            step_x,
            ya,
            str(i + 1),
            ha="center",
            va="center",
            fontsize=7.5,
            fontweight="700",
            color=TEXT,
            bbox=dict(boxstyle="round,pad=0.28", facecolor="#1a2330", edgecolor=ACCENT_SOFT, linewidth=0.7),
        )
        ax.text((x1 + x2) / 2, ya + 0.13, msg, ha="center", fontsize=7.3, color=TEXT if not is_ret else TEXT_MUTED)

    custom = [Line2D([0], [0], color=ACCENT, lw=2, label="Call"), Line2D([0], [0], color=TEXT_MUTED, lw=1.4, linestyle="--", label="Return")]
    ax.legend(handles=custom, loc="lower center", bbox_to_anchor=(0.5, 0.02), ncol=2, frameon=True, facecolor=SURFACE, edgecolor="#2a3342", fontsize=7.5, labelcolor=TEXT_MUTED)

    ax.text(8.75, 0.55, "Undo path → see data-flow-undo.png", ha="center", fontsize=7.8, color=TEXT_MUTED)

    _save(fig, "data-flow.png")


def draw_sequence_undo() -> None:
    """POST /v1/undo — separate diagram."""
    fig, ax = plt.subplots(figsize=(17.5, 6.8), dpi=DPI, facecolor=BG)
    ax.set_xlim(-0.5, 17.8)
    ax.set_ylim(0, 6.8)
    ax.axis("off")

    ax.text(8.75, 6.4, "Undo path (30s window)", ha="center", va="top", fontsize=16, fontweight="700", color=TEXT)
    ax.text(8.75, 5.9, "undo.py · Redis undo:{task_id} · TaskManager / Notion", ha="center", fontsize=9, color=TEXT_MUTED)

    actors = ["User", "OpenClaw", "FastAPI", "SQLite", "Redis", "Notion"]
    xs = [2.0, 3.85, 5.75, 8.35, 10.75, 13.25]
    y_top, y_bot = 5.35, 0.85

    for x, name in zip(xs, actors):
        ax.add_patch(
            FancyBboxPatch(
                (x - 0.75, y_top + 0.05),
                1.5,
                0.48,
                boxstyle="round,pad=0.02,rounding_size=0.2",
                facecolor=SURFACE,
                edgecolor="#2a3342",
                linewidth=1,
            )
        )
        ax.text(x, y_top + 0.29, name, ha="center", va="center", fontsize=9, fontweight="600", color=TEXT)
        ax.plot([x, x], [y_top, y_bot], color="#2a3342", lw=1.05)

    steps = [
        (0, 1, '"undo"', False),
        (1, 2, "POST /v1/undo", False),
        (2, 4, "GET undo payload", False),
        (2, 3, "delete_task or restore row", False),
        (2, 5, "archive / un-archive + sync_task", False),
        (2, 4, "DEL undo key", False),
        (2, 1, "UndoResponse", True),
        (1, 0, "confirm", True),
    ]
    y0 = 5.05
    dy = 0.42
    step_x = 0.95
    for i, (a, b, msg, is_ret) in enumerate(steps):
        ya = y0 - i * dy
        x1, x2 = xs[a], xs[b]
        col = TEXT_MUTED if is_ret else ACCENT
        arr = FancyArrowPatch(
            (x1, ya),
            (x2, ya),
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=1.1 if not is_ret else 0.9,
            color=col,
            linestyle="--" if is_ret else "-",
            shrinkA=4,
            shrinkB=4,
        )
        ax.add_patch(arr)
        ax.text(
            step_x,
            ya,
            str(i + 1),
            ha="center",
            va="center",
            fontsize=7.5,
            fontweight="700",
            color=TEXT,
            bbox=dict(boxstyle="round,pad=0.28", facecolor="#1a2330", edgecolor=ACCENT_SOFT, linewidth=0.7),
        )
        ax.text((x1 + x2) / 2, ya + 0.13, msg, ha="center", fontsize=7.3, color=TEXT if not is_ret else TEXT_MUTED)

    _save(fig, "data-flow-undo.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw_architecture()
    draw_state_machine()
    draw_sequence_main()
    draw_sequence_undo()
    print("Wrote:", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
