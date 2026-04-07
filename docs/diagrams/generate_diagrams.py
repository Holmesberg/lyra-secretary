"""
Lyra Secretary — system design diagrams (dark theme, 220 DPI).
Run:  python docs/diagrams/generate_diagrams.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
from matplotlib.lines import Line2D

OUT = Path(__file__).resolve().parent

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = "#0d1117"
SURFACE  = "#161b22"
LANE     = "#0f1318"
TEXT     = "#e6edf3"
MUTED    = "#8b949e"
BORDER   = "#30363d"
ACCENT   = "#58a6ff"   # blue   — HTTP / calls
GREEN    = "#3fb950"   # green  — storage writes / resume
AMBER    = "#d29922"   # amber  — pause
ROSE     = "#f85149"   # red    — abandon
VIOLET   = "#bc8cff"   # purple — OpenClaw
CYAN     = "#39c5cf"   # teal   — Telegram
M_BDR    = "#58a6ff"   # mutable state box border
T_BDR    = "#484f58"   # terminal state box border

DPI = 220

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"],
    "font.size": 9,
})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save(fig, name: str) -> None:
    fig.savefig(
        OUT / name, dpi=DPI, facecolor=BG, edgecolor="none",
        bbox_inches="tight", pad_inches=0.45,
    )
    plt.close(fig)


def _box(ax, cx, cy, w, h, label, sub="", *,
         edge=BORDER, fill=SURFACE, lw=1.25, dashed=False):
    ls = (0, (5, 3)) if dashed else "solid"
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.05,rounding_size=0.13",
        facecolor=fill, edgecolor=edge, linewidth=lw, linestyle=ls, zorder=3,
    ))
    label_y = cy + h * 0.12 if sub else cy
    ax.text(cx, label_y, label, ha="center", va="center",
            fontsize=9.5, fontweight="600", color=TEXT, zorder=4)
    if sub:
        ax.text(cx, cy - h * 0.29, sub, ha="center", va="center",
                fontsize=7, color=MUTED, zorder=4)


def _arrow(ax, x1, y1, x2, y2, label="", *,
           color=ACCENT, dashed=False, lw=1.2, rad=0.0, lp=None):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=8,
        linewidth=lw, color=color,
        linestyle="--" if dashed else "solid",
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=3, shrinkB=3, zorder=5,
    ))
    if label:
        if lp is None:
            lp = ((x1 + x2) / 2, (y1 + y2) / 2 + 0.18)
        ax.text(lp[0], lp[1], label, ha="center", va="center",
                fontsize=7, color=MUTED, zorder=6)


def _seg(ax, pts, label="", *, color=ACCENT, dashed=False, lw=1.15, lp=None):
    """Multi-point path with arrowhead at the final segment."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(xs, ys, color=color, lw=lw,
            linestyle="--" if dashed else "solid",
            solid_capstyle="round", zorder=4)
    ax.annotate(
        "", xy=pts[-1], xytext=pts[-2],
        arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=7),
        zorder=5,
    )
    if label and lp:
        ax.text(lp[0], lp[1], label, ha="center", va="center",
                fontsize=7, color=MUTED, zorder=6)


def _lane(ax, y_lo, y_hi):
    ax.axhspan(y_lo, y_hi, facecolor=LANE, alpha=0.5, zorder=0)


# ── 1. System Architecture ────────────────────────────────────────────────────
#
#  Grid (3 columns × 3 rows):
#    Col A x=4.5   Col B x=9.5   Col C x=14.5
#    ─────────────────────────────────────────
#    Telegram       [gap]         OpenClaw      ← Clients  y=8.3
#    FastAPI        TaskManager   APScheduler   ← Backend  y=5.3
#    SQLite         Redis         Notion        ← Storage  y=2.0
#
#  Arrows (solid = runtime call, dashed = background):
#    1  Telegram    → OpenClaw     user message
#    2  OpenClaw    → FastAPI      HTTP /v1  (orthogonal: down → left → down)
#    3  FastAPI     → TaskManager  service calls
#    4  TaskManager → SQLite       SQLAlchemy  (fan-out left)
#    5  TaskManager → Redis        redis-py    (straight down)
#    6  TaskManager → Notion       HTTPS       (fan-out right)
#    7  APScheduler → Notion       retry sync  (straight down, dashed)

def draw_architecture() -> None:
    W, H = 17.5, 10.0
    fig, ax = plt.subplots(figsize=(W, H), dpi=DPI, facecolor=BG)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    ax.text(W / 2, H - 0.30, "System Architecture",
            ha="center", va="top", fontsize=18, fontweight="700", color=TEXT)

    # Swimlane bands
    _lane(ax, 7.0, 9.3)   # Clients
    _lane(ax, 3.8, 6.7)   # Backend
    _lane(ax, 0.5, 3.5)   # Storage
    for y_mid, lbl in [(8.15, "Clients"), (5.25, "Backend"), (2.0, "Storage & External")]:
        ax.text(0.22, y_mid, lbl, ha="left", va="center",
                fontsize=8, fontweight="600", color=MUTED, rotation=90)

    # ── Nodes ─────────────────────────────────────────────────────────────────
    # row: Clients  (cy = 8.3)
    _box(ax,  4.5, 8.3, 2.2, 0.85, "Telegram",    "user chat",         edge=CYAN,   fill="#0c1e24")
    _box(ax, 14.5, 8.3, 2.4, 0.85, "OpenClaw",    "agent / skills",    edge=VIOLET, fill="#17121f")
    # row: Backend  (cy = 5.3)
    _box(ax,  4.5, 5.3, 2.2, 0.85, "FastAPI",     "REST /v1",          edge=AMBER,  fill="#1e1b0c")
    _box(ax,  9.5, 5.3, 2.6, 0.85, "TaskManager", "domain logic",      edge=ACCENT, fill="#0d1822")
    _box(ax, 14.5, 5.3, 2.4, 0.85, "APScheduler", "background jobs",   edge=BORDER, fill=SURFACE)
    # row: Storage  (cy = 2.0)
    _box(ax,  4.5, 2.0, 2.2, 0.85, "SQLite",      "persistence",       edge=GREEN,  fill="#0d1f12")
    _box(ax,  9.5, 2.0, 2.2, 0.85, "Redis",       "ephemeral state",   edge=GREEN,  fill="#0d1f12")
    _box(ax, 14.5, 2.0, 2.2, 0.85, "Notion",      "calendar database", edge=ROSE,   fill="#1f0d0d")

    # ── Arrows ─────────────────────────────────────────────────────────────────
    # 1. Telegram → OpenClaw
    _arrow(ax, 5.6, 8.3, 13.3, 8.3,
           "user message", color=CYAN, lw=1.1, lp=(9.45, 8.52))

    # 2. OpenClaw → FastAPI — orthogonal: drop to inter-lane gap, run left, drop to FastAPI
    #    Gap between Backend-top (6.7) and Clients-bottom (7.0) sits at y ≈ 6.85
    _seg(ax,
         [(14.5, 7.875), (14.5, 6.85), (4.5, 6.85), (4.5, 5.725)],
         "HTTP /v1", color=ACCENT, lp=(9.5, 7.03))

    # 3. FastAPI → TaskManager
    _arrow(ax, 5.6, 5.3, 8.2, 5.3,
           "service calls", color=ACCENT, lw=1.15, lp=(6.9, 5.52))

    # 4–6. TaskManager fan-out to storage (three arrows from bottom of TaskManager)
    #      Spread start points slightly so arrowheads don't pile up.
    _arrow(ax, 8.3, 4.875, 5.1, 2.425,   # left fan → SQLite
           "SQLAlchemy", color=GREEN, lw=1.1, lp=(6.35, 3.87))
    _arrow(ax, 9.5, 4.875, 9.5, 2.425,   # center fan → Redis
           "redis-py",   color=GREEN, lw=1.1, lp=(10.18, 3.65))
    _arrow(ax, 10.7, 4.875, 13.9, 2.425, # right fan → Notion
           "HTTPS",      color=GREEN, lw=1.1, lp=(12.65, 3.87))

    # 7. APScheduler → Notion (dashed — retry sync background job)
    _arrow(ax, 14.5, 4.875, 14.5, 2.425,
           "retry sync", color=MUTED, dashed=True, lw=1.05, lp=(15.35, 3.65))

    _save(fig, "architecture.png")


# ── 2. Task State Machine ─────────────────────────────────────────────────────
#
#  Flow band (horizontal, left→right):
#    ●  →  PLANNED  →  EXECUTING  ⇄  PAUSED  →  EXECUTED
#                   ↘ (mark-abandoned)  ↙
#  Terminal band (below):
#    SKIPPED   DELETED
#
#  EXECUTING ⇄ PAUSED: two offset horizontal arrows
#    pause():  lower track, AMBER, EXECUTING → PAUSED
#    resume(): upper track, GREEN, PAUSED → EXECUTING
#  EXECUTING → EXECUTED: arc over PAUSED, ACCENT
#  PLANNED → DELETED: short drop, T_BDR
#  PLANNED, EXECUTING, PAUSED → SKIPPED: converging arrows, ROSE / T_BDR

def draw_state_machine() -> None:
    W, H = 16.5, 8.2
    fig, ax = plt.subplots(figsize=(W, H), dpi=DPI, facecolor=BG)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    ax.text(W / 2, H - 0.28, "Task State Machine",
            ha="center", va="top", fontsize=18, fontweight="700", color=TEXT)
    ax.text(W / 2, H - 0.80,
            "PAUSED is non-terminal — resolves to EXECUTED (auto-resume on stop) "
            "or SKIPPED (mark-abandoned)",
            ha="center", va="top", fontsize=8.5, color=MUTED)

    # ── Swimlane bands ─────────────────────────────────────────────────────────
    _lane(ax, 3.6, 5.9)   # flow band
    _lane(ax, 0.4, 3.1)   # terminal band

    ax.text(0.22, 4.75, "Flow\n(mutable)", ha="left", va="center",
            fontsize=8, fontweight="600", color=MUTED)
    ax.text(0.22, 1.75, "Terminal\n(immutable)", ha="left", va="center",
            fontsize=8, fontweight="600", color=MUTED)

    # ── State box geometry ─────────────────────────────────────────────────────
    BW, BH = 2.2, 0.9   # box width, height
    CY = 4.75            # flow row y-centre

    # Column centres (enough gap between each pair for arrow labels)
    PX  = 2.2    # PLANNED
    EX  = 5.5    # EXECUTING
    PAX = 8.8    # PAUSED
    EDX = 12.2   # EXECUTED

    def _state(cx, label, terminal=False):
        edge = T_BDR if terminal else M_BDR
        fill = "#12161c" if terminal else SURFACE
        ls   = (0, (5, 3)) if terminal else "solid"
        ax.add_patch(FancyBboxPatch(
            (cx - BW / 2, CY - BH / 2), BW, BH,
            boxstyle="round,pad=0.05,rounding_size=0.13",
            facecolor=fill, edgecolor=edge, linewidth=1.25, linestyle=ls, zorder=3,
        ))
        ax.text(cx, CY + BH * 0.12, label, ha="center", va="center",
                fontsize=10, fontweight="700", color=TEXT, zorder=4)
        sub = "terminal" if terminal else "mutable"
        ax.text(cx, CY - BH * 0.29, sub, ha="center", va="center",
                fontsize=7, color=MUTED, style="italic", zorder=4)

    # Start node (filled circle)
    start_x = 0.75
    ax.add_patch(Circle((start_x, CY), 0.13, facecolor=TEXT, edgecolor=TEXT, zorder=5))

    _state(PX,  "PLANNED")
    _state(EX,  "EXECUTING")
    _state(PAX, "PAUSED")
    _state(EDX, "EXECUTED", terminal=True)

    # ── Flow arrows ────────────────────────────────────────────────────────────
    # ● → PLANNED
    _arrow(ax, start_x + 0.14, CY, PX - BW / 2, CY, color=TEXT, lw=1.1)

    # PLANNED → EXECUTING
    _arrow(ax, PX + BW / 2, CY, EX - BW / 2, CY,
           "start_task()", color=ACCENT, lw=1.2, lp=((PX + BW/2 + EX - BW/2)/2, CY + 0.22))

    # EXECUTING → PAUSED  (lower track, AMBER)
    y_pause  = CY - 0.2
    _arrow(ax, EX + BW / 2, y_pause, PAX - BW / 2, y_pause,
           "pause()", color=AMBER, lw=1.15, lp=((EX + BW/2 + PAX - BW/2)/2, y_pause - 0.18))

    # PAUSED → EXECUTING  (upper track, GREEN)
    y_resume = CY + 0.2
    _arrow(ax, PAX - BW / 2, y_resume, EX + BW / 2, y_resume,
           "resume()", color=GREEN, lw=1.15, lp=((EX + BW/2 + PAX - BW/2)/2, y_resume + 0.18))

    # EXECUTING → EXECUTED  (arc over PAUSED; rad>0 bows upward for left→right arrow)
    _arrow(ax, EX + BW / 2, CY + 0.15, EDX - BW / 2, CY + 0.15,
           "complete_task()", color=ACCENT, lw=1.2, rad=0.40,
           lp=((EX + BW/2 + EDX - BW/2)/2, CY + 1.15))

    # ── Terminal states ────────────────────────────────────────────────────────
    TY = 1.75          # terminal row y-centre
    DEL_X = 3.2        # DELETED (only from PLANNED)
    SKP_X = 8.5        # SKIPPED (from PLANNED, EXECUTING, PAUSED)

    def _terminal(cx, label):
        ax.add_patch(FancyBboxPatch(
            (cx - BW / 2, TY - BH / 2), BW, BH,
            boxstyle="round,pad=0.05,rounding_size=0.13",
            facecolor="#12161c", edgecolor=T_BDR, linewidth=1.25,
            linestyle=(0, (5, 3)), zorder=3,
        ))
        ax.text(cx, TY + BH * 0.12, label, ha="center", va="center",
                fontsize=10, fontweight="700", color=TEXT, zorder=4)
        ax.text(cx, TY - BH * 0.29, "terminal", ha="center", va="center",
                fontsize=7, color=MUTED, style="italic", zorder=4)

    _terminal(DEL_X, "DELETED")
    _terminal(SKP_X, "SKIPPED")

    # PLANNED → DELETED
    _arrow(ax, PX - 0.3, CY - BH / 2, DEL_X - 0.3, TY + BH / 2,
           "delete_task()", color=T_BDR, lw=1.05, lp=(DEL_X - 1.2, 3.0))

    # PLANNED → SKIPPED
    _arrow(ax, PX + 0.3, CY - BH / 2, SKP_X - 0.8, TY + BH / 2,
           "skip_task()", color=T_BDR, lw=1.05, lp=(4.8, 2.85))

    # EXECUTING → SKIPPED  (mark-abandoned)
    _arrow(ax, EX + 0.1, CY - BH / 2, SKP_X - 0.3, TY + BH / 2,
           "mark-abandoned", color=ROSE, lw=1.1, lp=(7.2, 2.9))

    # PAUSED → SKIPPED  (mark-abandoned — label omitted to avoid clutter; same color signals intent)
    _arrow(ax, PAX - 0.3, CY - BH / 2, SKP_X + 0.3, TY + BH / 2,
           "", color=ROSE, lw=1.1)

    # Small legend
    legend = [
        Line2D([0], [0], color=ACCENT,  lw=1.8, label="normal transition"),
        Line2D([0], [0], color=AMBER,   lw=1.8, label="pause()"),
        Line2D([0], [0], color=GREEN,   lw=1.8, label="resume()"),
        Line2D([0], [0], color=ROSE,    lw=1.8, label="mark-abandoned"),
        Line2D([0], [0], color=T_BDR,   lw=1.8, label="delete / skip from PLANNED"),
    ]
    ax.legend(handles=legend, loc="lower right", bbox_to_anchor=(0.99, 0.02),
              ncol=1, frameon=True, facecolor=SURFACE, edgecolor=BORDER,
              fontsize=7.5, labelcolor=MUTED)

    _save(fig, "state-machine.png")


# ── 3 & 4. Sequence diagram helpers ──────────────────────────────────────────

def _sequence_setup(ax, W, H, title, subtitle, actors, xs):
    """Draw title, actor boxes, and lifelines. Returns (y_top, y_bot)."""
    ax.text(W / 2, H - 0.30, title, ha="center", va="top",
            fontsize=18, fontweight="700", color=TEXT)
    if subtitle:
        ax.text(W / 2, H - 0.80, subtitle, ha="center", va="top",
                fontsize=9, color=MUTED)

    y_actor = H - 1.45
    y_lifeline_top = y_actor - 0.23
    y_lifeline_bot = 1.0

    for x, name in zip(xs, actors):
        _box(ax, x, y_actor, 2.1, 0.44, name)
        ax.plot([x, x], [y_lifeline_top, y_lifeline_bot],
                color=BORDER, lw=1.0, linestyle="--", zorder=1)

    return y_lifeline_top, y_lifeline_bot


def _step(ax, i, a, b, msg, is_ret, xs, y, num_x=0.6):
    x1, x2 = xs[a], xs[b]
    col = MUTED if is_ret else ACCENT
    lw  = 0.9 if is_ret else 1.15

    ax.add_patch(FancyArrowPatch(
        (x1, y), (x2, y),
        arrowstyle="-|>", mutation_scale=8,
        linewidth=lw, color=col,
        linestyle="--" if is_ret else "solid",
        shrinkA=4, shrinkB=4, zorder=5,
    ))
    # Step badge
    ax.text(num_x, y, str(i + 1), ha="center", va="center",
            fontsize=7, fontweight="700", color=TEXT, zorder=6,
            bbox=dict(boxstyle="round,pad=0.26", facecolor="#1a2330",
                      edgecolor="#3a5070", linewidth=0.7))
    # Message
    mx = (x1 + x2) / 2
    ax.text(mx, y + 0.16, msg, ha="center", va="center",
            fontsize=7.2, color=TEXT if not is_ret else MUTED, zorder=6)


def _phase_band(ax, y_hi, y_lo, label, W):
    ax.axhspan(y_lo, y_hi, facecolor=LANE, alpha=0.45, zorder=0)
    ax.text(W - 0.35, (y_hi + y_lo) / 2, label, ha="right", va="center",
            fontsize=7.5, fontweight="600", color=MUTED, style="italic")


# ── 3. Task Lifecycle — Main Path ─────────────────────────────────────────────
#
#  14 steps across 3 phases:
#    SCHEDULE (1–5):  create task, Notion sync, confirm task_id
#    START    (6–9):  start stopwatch, mark EXECUTING, cache session
#    STOP    (10–14): stop stopwatch, mark EXECUTED, Notion sync, confirm

def draw_sequence_main() -> None:
    W, H = 20.0, 11.0
    fig, ax = plt.subplots(figsize=(W, H), dpi=DPI, facecolor=BG)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    actors = ["User", "OpenClaw", "FastAPI", "SQLite", "Redis", "Notion"]
    xs     = [2.0, 4.5, 7.0, 10.0, 13.0, 16.0]

    _sequence_setup(ax, W, H, "Task Lifecycle — Main Path",
                    "create  ·  start stopwatch  ·  stop", actors, xs)

    y0 = H - 2.1
    dy = 0.50

    steps = [                                                      # (from, to, label, return?)
        (0, 1, "schedule task",                               False),  # 1
        (1, 2, "POST /v1/create",                             False),  # 2
        (2, 3, "INSERT task  ·  state: PLANNED",              False),  # 3
        (2, 5, "sync_task()  (create)",                       False),  # 4
        (2, 1, "{ task_id }",                                 True),   # 5
        (1, 2, "POST /v1/stopwatch/start",                    False),  # 6
        (2, 3, "PLANNED → EXECUTING  ·  INSERT session",      False),  # 7
        (2, 4, "SET stopwatch:active:{id}",                   False),  # 8
        (2, 1, "{ session_id }",                              True),   # 9
        (1, 2, "POST /v1/stopwatch/stop",                     False),  # 10
        (2, 4, "GET + DEL stopwatch:active",                  False),  # 11
        (2, 3, "EXECUTING → EXECUTED  ·  UPDATE session",     False),  # 12
        (2, 5, "sync_task()  (complete)",                     False),  # 13
        (2, 1, "{ duration_minutes, delta_minutes }",         True),   # 14
    ]
    assert len(steps) <= 15

    # Phase bands
    #   SCHEDULE: steps 1–5  →  y = y0 down to y0-4*dy
    #   START:    steps 6–9  →  y = y0-5*dy down to y0-8*dy
    #   STOP:     steps 10–14 → y = y0-9*dy down to y0-13*dy
    s_hi = y0 + dy * 0.6
    s_lo = y0 - 4 * dy - dy * 0.4
    t_hi = y0 - 5 * dy + dy * 0.4
    t_lo = y0 - 8 * dy - dy * 0.4
    p_hi = y0 - 9 * dy + dy * 0.4
    p_lo = y0 - 13 * dy - dy * 0.4

    _phase_band(ax, s_hi, s_lo, "SCHEDULE", W)
    _phase_band(ax, t_hi, t_lo, "START", W)
    _phase_band(ax, p_hi, p_lo, "STOP", W)

    for i, (a, b, msg, is_ret) in enumerate(steps):
        _step(ax, i, a, b, msg, is_ret, xs, y0 - i * dy)

    legend = [
        Line2D([0], [0], color=ACCENT, lw=1.5, label="call"),
        Line2D([0], [0], color=MUTED,  lw=1.2, linestyle="--", label="return"),
    ]
    ax.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.01),
              ncol=2, frameon=True, facecolor=SURFACE, edgecolor=BORDER,
              fontsize=8, labelcolor=TEXT)

    _save(fig, "data-flow.png")


# ── 4. Undo Path ──────────────────────────────────────────────────────────────

def draw_sequence_undo() -> None:
    W, H = 20.0, 8.2
    fig, ax = plt.subplots(figsize=(W, H), dpi=DPI, facecolor=BG)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    actors = ["User", "OpenClaw", "FastAPI", "SQLite", "Redis", "Notion"]
    xs     = [2.0, 4.5, 7.0, 10.0, 13.0, 16.0]

    _sequence_setup(ax, W, H, "Undo Path  (30-second window)",
                    "POST /v1/undo  ·  reverts last create or delete", actors, xs)

    y0 = H - 2.1
    dy = 0.60

    steps = [
        (0, 1, '"undo"',                            False),  # 1
        (1, 2, "POST /v1/undo",                     False),  # 2
        (2, 4, "GET undo:{task_id}",                False),  # 3
        (2, 3, "restore task row / soft-delete",    False),  # 4
        (2, 5, "archive or un-archive page",        False),  # 5
        (2, 4, "DEL undo key",                      False),  # 6
        (2, 1, "{ undone: true, task_id }",         True),   # 7
        (1, 0, "confirmed",                         True),   # 8
    ]

    y_hi = y0 + dy * 0.6
    y_lo = y0 - (len(steps) - 1) * dy - dy * 0.4
    _phase_band(ax, y_hi, y_lo, "UNDO", W)

    for i, (a, b, msg, is_ret) in enumerate(steps):
        _step(ax, i, a, b, msg, is_ret, xs, y0 - i * dy)

    legend = [
        Line2D([0], [0], color=ACCENT, lw=1.5, label="call"),
        Line2D([0], [0], color=MUTED,  lw=1.2, linestyle="--", label="return"),
    ]
    ax.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.01),
              ncol=2, frameon=True, facecolor=SURFACE, edgecolor=BORDER,
              fontsize=8, labelcolor=TEXT)

    _save(fig, "data-flow-undo.png")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw_architecture()
    draw_state_machine()
    draw_sequence_main()
    draw_sequence_undo()
    print("Wrote:", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
