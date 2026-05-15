"""
LyraOS system design diagrams.

Run:
    python docs/diagrams/generate_diagrams.py

The diagrams are intentionally product/research boundary diagrams, not a full
entity-relationship model. They should match archive/appstore/summary_of_app.md
and the Cortex product-research contracts.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent
DPI = 220

BG = "#0d1117"
SURFACE = "#161b22"
LANE = "#0f1318"
TEXT = "#e6edf3"
MUTED = "#8b949e"
BORDER = "#30363d"

BLUE = "#58a6ff"
GREEN = "#3fb950"
AMBER = "#d29922"
ROSE = "#f85149"
VIOLET = "#bc8cff"
CYAN = "#39c5cf"
WHITE = "#f8fafc"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"],
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
        pad_inches=0.45,
    )
    plt.close(fig)


def _box(
    ax,
    cx: float,
    cy: float,
    w: float,
    h: float,
    label: str,
    sub: str = "",
    *,
    edge: str = BORDER,
    fill: str = SURFACE,
    lw: float = 1.25,
    dashed: bool = False,
    fontsize: float = 9.0,
) -> None:
    linestyle = (0, (5, 3)) if dashed else "solid"
    ax.add_patch(
        FancyBboxPatch(
            (cx - w / 2, cy - h / 2),
            w,
            h,
            boxstyle="round,pad=0.055,rounding_size=0.13",
            facecolor=fill,
            edgecolor=edge,
            linewidth=lw,
            linestyle=linestyle,
            zorder=3,
        )
    )
    label_y = cy + h * 0.13 if sub else cy
    ax.text(
        cx,
        label_y,
        label,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="700",
        color=TEXT,
        zorder=4,
    )
    if sub:
        ax.text(
            cx,
            cy - h * 0.28,
            sub,
            ha="center",
            va="center",
            fontsize=7.0,
            color=MUTED,
            zorder=4,
        )


def _arrow(
    ax,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    label: str = "",
    *,
    color: str = BLUE,
    dashed: bool = False,
    lw: float = 1.15,
    rad: float = 0.0,
    lp: tuple[float, float] | None = None,
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=8,
            linewidth=lw,
            color=color,
            linestyle="--" if dashed else "solid",
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=4,
            shrinkB=4,
            zorder=5,
        )
    )
    if label:
        if lp is None:
            lp = ((x1 + x2) / 2, (y1 + y2) / 2 + 0.17)
        ax.text(lp[0], lp[1], label, ha="center", va="center", fontsize=7, color=MUTED, zorder=6)


def _seg(
    ax,
    pts: list[tuple[float, float]],
    label: str = "",
    *,
    color: str = BLUE,
    dashed: bool = False,
    lw: float = 1.1,
    lp: tuple[float, float] | None = None,
) -> None:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(
        xs,
        ys,
        color=color,
        lw=lw,
        linestyle="--" if dashed else "solid",
        solid_capstyle="round",
        zorder=4,
    )
    ax.annotate(
        "",
        xy=pts[-1],
        xytext=pts[-2],
        arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=7),
        zorder=5,
    )
    if label and lp:
        ax.text(lp[0], lp[1], label, ha="center", va="center", fontsize=7, color=MUTED, zorder=6)


def _lane(ax, y_lo: float, y_hi: float, label: str) -> None:
    ax.axhspan(y_lo, y_hi, facecolor=LANE, alpha=0.50, zorder=0)
    ax.text(
        0.22,
        (y_lo + y_hi) / 2,
        label,
        ha="left",
        va="center",
        fontsize=8,
        fontweight="700",
        color=MUTED,
        rotation=90,
    )


def _phase_band(ax, y_hi: float, y_lo: float, label: str, width: float) -> None:
    ax.axhspan(y_lo, y_hi, facecolor=LANE, alpha=0.45, zorder=0)
    ax.text(
        width - 0.35,
        (y_hi + y_lo) / 2,
        label,
        ha="right",
        va="center",
        fontsize=7.5,
        fontweight="700",
        color=MUTED,
        style="italic",
    )


def draw_architecture() -> None:
    """Current product, research, and operator runtime architecture."""
    w, h = 19.0, 12.0
    fig, ax = plt.subplots(figsize=(w, h), dpi=DPI, facecolor=BG)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")

    ax.text(w / 2, h - 0.25, "LyraOS Current Architecture", ha="center", va="top", fontsize=18, fontweight="800", color=TEXT)
    ax.text(
        w / 2,
        h - 0.75,
        "Product behavior flows forward into event/data rows; Cortex interprets read-time under exposure and clean-data contracts.",
        ha="center",
        va="top",
        fontsize=8.8,
        color=MUTED,
    )

    _lane(ax, 9.1, 10.85, "Product")
    _lane(ax, 6.85, 8.65, "API")
    _lane(ax, 4.45, 6.35, "Persistence")
    _lane(ax, 2.20, 4.05, "Research")
    _lane(ax, 0.45, 1.85, "Operator")

    # Product layer
    _box(ax, 2.5, 10.0, 2.4, 0.78, "Browser User", "normal planning/execution", edge=WHITE, fill="#111820")
    _box(ax, 5.6, 10.0, 2.6, 0.78, "Next.js App", "today, pulse, calendar, insights", edge=CYAN, fill="#0c1e24")
    _box(ax, 8.7, 10.0, 2.4, 0.78, "NextAuth", "Google OAuth + backendToken", edge=CYAN, fill="#0c1e24")

    # API and service authorities
    _box(ax, 2.6, 7.75, 2.5, 0.78, "FastAPI /v1", "REST boundary", edge=BLUE, fill="#0d1822")
    _box(ax, 5.7, 7.75, 2.7, 0.78, "User Scope", "bearer/JWT middleware", edge=BLUE, fill="#0d1822")
    _box(ax, 8.9, 7.75, 3.2, 0.78, "Service Authorities", "Task, Stopwatch, Deadline", edge=AMBER, fill="#1e1b0c")
    _box(ax, 12.5, 7.75, 2.7, 0.78, "API Modules", "brain dump, users, analytics", edge=AMBER, fill="#1e1b0c")

    # Persistence and workers
    _box(ax, 2.5, 5.35, 2.7, 0.78, "Supabase Postgres", "SQLAlchemy models", edge=GREEN, fill="#0d1f12")
    _box(ax, 5.7, 5.35, 2.4, 0.78, "Redis", "hot state, queues, undo", edge=GREEN, fill="#0d1f12")
    _box(ax, 8.9, 5.35, 2.7, 0.78, "APScheduler", "repairs, sync, predictions", edge=GREEN, fill="#0d1f12")
    _box(ax, 12.5, 5.35, 2.8, 0.78, "External Context", "Google, Moodle, Notion", edge=ROSE, fill="#1f0d0d")

    # Research and governance
    _box(ax, 2.5, 3.15, 2.7, 0.78, "Raw Product Rows", "tasks, sessions, deadlines", edge=VIOLET, fill="#17121f")
    _box(ax, 5.7, 3.15, 2.5, 0.78, "Cortex", "read-time projections", edge=VIOLET, fill="#17121f")
    _box(ax, 8.9, 3.15, 2.8, 0.78, "Output Registry", "truth and usage classes", edge=VIOLET, fill="#17121f")
    _box(ax, 12.5, 3.15, 2.8, 0.78, "Exposure Ledger", "baseline gate, fail closed", edge=VIOLET, fill="#17121f")
    _box(ax, 15.9, 3.15, 2.6, 0.78, "Insights", "cards, synthesis, diagnostics", edge=VIOLET, fill="#17121f")

    # Operator-only
    _box(ax, 4.0, 1.15, 2.4, 0.70, "Admin", "operator dashboard", edge=MUTED, fill=SURFACE, dashed=True)
    _box(ax, 7.1, 1.15, 2.4, 0.70, "JARVIS", "confirm-gated writes", edge=MUTED, fill=SURFACE, dashed=True)
    _box(ax, 10.2, 1.15, 2.4, 0.70, "OpenClaw", "agent runtime", edge=MUTED, fill=SURFACE, dashed=True)
    _box(ax, 13.3, 1.15, 2.4, 0.70, "Telegram", "operator notifications", edge=MUTED, fill=SURFACE, dashed=True)

    # Product/API flow
    _arrow(ax, 3.7, 10.0, 4.25, 10.0, "uses", color=CYAN)
    _arrow(ax, 6.9, 10.0, 7.5, 10.0, "session", color=CYAN)
    _seg(ax, [(5.6, 9.6), (5.6, 8.75), (2.6, 8.75), (2.6, 8.15)], "JSON + bearer", color=BLUE, lp=(4.2, 8.93))
    _arrow(ax, 3.85, 7.75, 4.35, 7.75, "auth", color=BLUE)
    _arrow(ax, 7.05, 7.75, 7.3, 7.75, "scoped", color=BLUE)
    _arrow(ax, 10.5, 7.75, 11.15, 7.75, "routes", color=AMBER)

    # Data writes and background jobs
    _arrow(ax, 8.1, 7.35, 3.6, 5.75, "ORM writes", color=GREEN, lp=(5.6, 6.65))
    _arrow(ax, 8.9, 7.35, 5.9, 5.75, "hot state", color=GREEN, lp=(7.2, 6.37))
    _arrow(ax, 9.3, 6.95, 9.1, 5.75, "jobs", color=GREEN, dashed=True, lp=(9.7, 6.35))
    _arrow(ax, 9.9, 5.35, 11.1, 5.35, "sync/read", color=ROSE, dashed=True)

    # Research read path and exposure-safe render loop
    _arrow(ax, 2.5, 4.95, 2.5, 3.55, "raw traces", color=VIOLET)
    _arrow(ax, 3.85, 3.15, 4.4, 3.15, "project", color=VIOLET)
    _arrow(ax, 6.95, 3.15, 7.45, 3.15, "declare", color=VIOLET)
    _arrow(ax, 10.25, 3.15, 11.1, 3.15, "gate", color=VIOLET)
    _arrow(ax, 13.9, 3.15, 14.55, 3.15, "emit", color=VIOLET)
    _seg(ax, [(15.9, 3.55), (15.9, 9.0), (6.1, 9.0), (6.1, 9.6)], "render + ack", color=CYAN, dashed=True, lp=(11.2, 9.18))

    # Operator-only paths
    _arrow(ax, 4.7, 1.5, 2.9, 7.35, "operator read", color=MUTED, dashed=True, rad=-0.08, lp=(3.4, 4.35))
    _arrow(ax, 7.1, 1.5, 8.7, 7.35, "confirmed tools", color=MUTED, dashed=True, rad=-0.06, lp=(8.2, 4.35))
    _arrow(ax, 10.2, 1.5, 12.5, 7.35, "orchestration", color=MUTED, dashed=True, rad=0.08, lp=(11.8, 4.35))
    _arrow(ax, 13.3, 1.5, 8.9, 5.0, "alerts", color=MUTED, dashed=True, rad=0.15, lp=(13.5, 4.25))

    legend = [
        Line2D([0], [0], color=BLUE, lw=1.8, label="runtime request"),
        Line2D([0], [0], color=GREEN, lw=1.8, label="state/write path"),
        Line2D([0], [0], color=VIOLET, lw=1.8, label="research/governance read path"),
        Line2D([0], [0], color=MUTED, lw=1.5, linestyle="--", label="operator-only/background"),
    ]
    ax.legend(
        handles=legend,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.005),
        ncol=4,
        frameon=True,
        facecolor=SURFACE,
        edgecolor=BORDER,
        fontsize=7.5,
        labelcolor=TEXT,
    )

    _save(fig, "architecture.png")


def draw_state_machine() -> None:
    """Task lifecycle with explicit retroactive completion caveat."""
    w, h = 16.8, 8.4
    fig, ax = plt.subplots(figsize=(w, h), dpi=DPI, facecolor=BG)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")

    ax.text(w / 2, h - 0.25, "Task State Machine", ha="center", va="top", fontsize=18, fontweight="800", color=TEXT)
    ax.text(
        w / 2,
        h - 0.78,
        "Measured execution requires a real stopwatch trace; retroactive done is product recovery, not measured evidence.",
        ha="center",
        va="top",
        fontsize=8.5,
        color=MUTED,
    )

    _lane(ax, 3.6, 5.95, "Flow")
    _lane(ax, 0.45, 3.10, "Terminal")

    bw, bh = 2.25, 0.92
    cy = 4.8
    px, ex, pax, edx = 2.1, 5.3, 8.6, 12.0
    ty = 1.8
    skx, delx = 7.7, 3.1

    def state(cx: float, y: float, label: str, sub: str, *, terminal: bool = False) -> None:
        _box(
            ax,
            cx,
            y,
            bw,
            bh,
            label,
            sub,
            edge=BORDER if terminal else BLUE,
            fill="#12161c" if terminal else SURFACE,
            dashed=terminal,
            fontsize=9.8,
        )

    ax.add_patch(Circle((0.75, cy), 0.13, facecolor=TEXT, edgecolor=TEXT, zorder=5))
    state(px, cy, "PLANNED", "mutable")
    state(ex, cy, "EXECUTING", "mutable")
    state(pax, cy, "PAUSED", "mutable")
    state(edx, cy, "EXECUTED", "terminal", terminal=True)
    state(delx, ty, "DELETED", "terminal", terminal=True)
    state(skx, ty, "SKIPPED", "recoverable", terminal=False)

    _arrow(ax, 0.9, cy, px - bw / 2, cy, color=WHITE)
    _arrow(ax, px + bw / 2, cy, ex - bw / 2, cy, "start", color=BLUE)
    _arrow(ax, ex + bw / 2, cy - 0.20, pax - bw / 2, cy - 0.20, "pause", color=AMBER, lp=(6.95, cy - 0.47))
    _arrow(ax, pax - bw / 2, cy + 0.20, ex + bw / 2, cy + 0.20, "resume", color=GREEN, lp=(6.95, cy + 0.48))
    _arrow(ax, ex + bw / 2, cy + 0.10, edx - bw / 2, cy + 0.10, "stop/complete", color=BLUE, rad=0.36, lp=(8.55, cy + 1.10))

    _arrow(ax, px - 0.25, cy - bh / 2, delx - 0.25, ty + bh / 2, "delete", color=BORDER, lp=(2.25, 3.05))
    _arrow(ax, px + 0.25, cy - bh / 2, skx - 0.85, ty + bh / 2, "skip", color=BORDER, lp=(4.25, 2.80))
    _arrow(ax, ex + 0.10, cy - bh / 2, skx - 0.25, ty + bh / 2, "abandon", color=ROSE, lp=(6.35, 2.95))
    _arrow(ax, pax - 0.20, cy - bh / 2, skx + 0.25, ty + bh / 2, "abandon", color=ROSE, lp=(8.25, 3.05))
    _arrow(ax, skx - bw / 2, ty, delx + bw / 2, ty, "delete", color=BORDER, dashed=True, lp=(5.4, ty + 0.25))

    _arrow(
        ax,
        px + bw / 2,
        cy - 0.12,
        edx - bw / 2,
        cy - 0.12,
        "retroactive done",
        color=AMBER,
        dashed=True,
        rad=-0.45,
        lp=(7.0, 3.48),
    )
    _arrow(
        ax,
        skx + bw / 2,
        ty + 0.20,
        edx - bw / 2,
        cy - bh / 2,
        "overdue recovery",
        color=AMBER,
        dashed=True,
        lp=(10.2, 2.98),
    )

    legend = [
        Line2D([0], [0], color=BLUE, lw=1.8, label="measured lifecycle"),
        Line2D([0], [0], color=AMBER, lw=1.8, linestyle="--", label="retroactive recovery"),
        Line2D([0], [0], color=ROSE, lw=1.8, label="abandon/skip"),
        Line2D([0], [0], color=BORDER, lw=1.8, linestyle="--", label="delete"),
    ]
    ax.legend(handles=legend, loc="lower right", bbox_to_anchor=(0.99, 0.02), frameon=True, facecolor=SURFACE, edgecolor=BORDER, fontsize=7.5, labelcolor=TEXT)

    _save(fig, "state-machine.png")


def _sequence_setup(ax, width: float, height: float, title: str, subtitle: str, actors: list[str], xs: list[float]) -> None:
    ax.text(width / 2, height - 0.25, title, ha="center", va="top", fontsize=18, fontweight="800", color=TEXT)
    ax.text(width / 2, height - 0.72, subtitle, ha="center", va="top", fontsize=8.8, color=MUTED)
    y_actor = height - 1.38
    for x, actor in zip(xs, actors):
        _box(ax, x, y_actor, 2.15, 0.44, actor, fontsize=8.4)
        ax.plot([x, x], [y_actor - 0.25, 0.9], color=BORDER, lw=1.0, linestyle="--", zorder=1)


def _step(ax, i: int, a: int, b: int, msg: str, ret: bool, xs: list[float], y: float, *, num_x: float = 0.55) -> None:
    x1, x2 = xs[a], xs[b]
    color = MUTED if ret else BLUE
    ax.add_patch(
        FancyArrowPatch(
            (x1, y),
            (x2, y),
            arrowstyle="-|>",
            mutation_scale=8,
            linewidth=0.95 if ret else 1.15,
            color=color,
            linestyle="--" if ret else "solid",
            shrinkA=4,
            shrinkB=4,
            zorder=5,
        )
    )
    ax.text(
        num_x,
        y,
        str(i + 1),
        ha="center",
        va="center",
        fontsize=7,
        fontweight="700",
        color=TEXT,
        zorder=6,
        bbox=dict(boxstyle="round,pad=0.25", facecolor="#1a2330", edgecolor="#3a5070", linewidth=0.7),
    )
    ax.text((x1 + x2) / 2, y + 0.15, msg, ha="center", va="center", fontsize=7.1, color=MUTED if ret else TEXT, zorder=6)


def draw_sequence_main() -> None:
    """Main product execution and governance path."""
    w, h = 21.0, 11.5
    fig, ax = plt.subplots(figsize=(w, h), dpi=DPI, facecolor=BG)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")

    actors = ["User", "Next.js", "FastAPI", "Services", "Postgres", "Redis", "Cortex/Exposure"]
    xs = [1.7, 4.1, 6.7, 9.2, 11.9, 14.5, 17.6]
    _sequence_setup(
        ax,
        w,
        h,
        "Task Lifecycle - Current Main Path",
        "create task, start timer, stop timer, then render governed insight surfaces",
        actors,
        xs,
    )

    y0 = h - 2.05
    dy = 0.49
    steps = [
        (0, 1, "create task / brain dump", False),
        (1, 2, "POST /v1/create or /brain-dump/commit + bearer", False),
        (2, 3, "resolve user scope, validate payload", False),
        (3, 4, "INSERT task, deadline bindings", False),
        (3, 5, "cache range / undo context", False),
        (2, 1, "{ task_id, planned state }", True),
        (0, 1, "start timer", False),
        (1, 2, "POST /v1/stopwatch/start", False),
        (3, 4, "PLANNED -> EXECUTING; INSERT session", False),
        (3, 5, "SET active_stopwatch:{user_id}", False),
        (2, 1, "{ session_id }", True),
        (0, 1, "stop timer + reflection", False),
        (1, 2, "POST /v1/stopwatch/stop", False),
        (3, 5, "GET/DEL active state", False),
        (3, 4, "EXECUTING -> EXECUTED; write pause/session metrics", False),
        (2, 1, "{ executed task, mirrors }", True),
        (1, 6, "GET /v1/analytics/insights", False),
        (6, 4, "read raw rows, clean profile, exposure context", False),
        (6, 1, "registered insights + render metadata", True),
    ]

    _phase_band(ax, y0 + dy * 0.6, y0 - 5 * dy - dy * 0.4, "PLAN", w)
    _phase_band(ax, y0 - 6 * dy + dy * 0.4, y0 - 10 * dy - dy * 0.4, "START", w)
    _phase_band(ax, y0 - 11 * dy + dy * 0.4, y0 - 15 * dy - dy * 0.4, "STOP", w)
    _phase_band(ax, y0 - 16 * dy + dy * 0.4, y0 - 18 * dy - dy * 0.4, "INSIGHTS", w)

    for i, (a, b, msg, ret) in enumerate(steps):
        _step(ax, i, a, b, msg, ret, xs, y0 - i * dy)

    legend = [
        Line2D([0], [0], color=BLUE, lw=1.5, label="call/write"),
        Line2D([0], [0], color=MUTED, lw=1.2, linestyle="--", label="return"),
    ]
    ax.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=2, frameon=True, facecolor=SURFACE, edgecolor=BORDER, fontsize=8, labelcolor=TEXT)
    _save(fig, "data-flow.png")


def draw_sequence_undo() -> None:
    """Undo and recovery path after create/delete/void actions."""
    w, h = 20.0, 8.8
    fig, ax = plt.subplots(figsize=(w, h), dpi=DPI, facecolor=BG)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")

    actors = ["User", "Next.js", "FastAPI", "TaskManager", "Postgres", "Redis"]
    xs = [1.8, 4.4, 7.0, 9.8, 12.7, 15.5]
    _sequence_setup(
        ax,
        w,
        h,
        "Undo And Recovery Path",
        "Redis stores short-lived undo context; product recovery preserves provenance",
        actors,
        xs,
    )

    y0 = h - 2.05
    dy = 0.56
    steps = [
        (0, 1, "click undo / recovery action", False),
        (1, 2, "POST /v1/undo or task recovery endpoint", False),
        (2, 5, "GET undo:{user_id}:*", False),
        (2, 3, "authorize scoped mutation", False),
        (3, 4, "restore, void, skip, or retroactive completion", False),
        (3, 5, "clear live/undo keys", False),
        (2, 1, "{ updated task, provenance }", True),
        (1, 0, "UI refresh + toast", True),
    ]

    _phase_band(ax, y0 + dy * 0.6, y0 - (len(steps) - 1) * dy - dy * 0.4, "RECOVERY", w)
    for i, (a, b, msg, ret) in enumerate(steps):
        _step(ax, i, a, b, msg, ret, xs, y0 - i * dy)

    ax.text(
        w / 2,
        0.55,
        "Retroactive completion may set initiation_status='retroactive'; it must not create a measured stopwatch trace.",
        ha="center",
        va="center",
        fontsize=8,
        color=AMBER,
    )

    legend = [
        Line2D([0], [0], color=BLUE, lw=1.5, label="call/write"),
        Line2D([0], [0], color=MUTED, lw=1.2, linestyle="--", label="return"),
    ]
    ax.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.03), ncol=2, frameon=True, facecolor=SURFACE, edgecolor=BORDER, fontsize=8, labelcolor=TEXT)
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
