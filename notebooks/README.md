# Operator Analytics Notebook

Private operator tooling. Not a product feature. Not shipped to users.

## Purpose

Systematic interrogation of the Lyra dataset at Day 10 / 30 / 60 / 90 milestones.
Replaces ad-hoc CSV review, which causes silent signal loss.

Paired artifacts:

- `operator_analytics.ipynb` — seven helper cells (a–g) plus Day 10 question-cell
  templates. Day 30 / 60 / 90 questions live in the checklist and are added as
  additional cells when the milestone arrives.
- `docs/operator_interrogation_checklist.md` — prose question list per milestone.
- `docs/operator_findings_log.md` — template for recording observations and
  resulting actions (new dogfood item, new VT, noted-not-actionable).

## Setup

Outside Docker:

```bash
cd notebooks/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter notebook operator_analytics.ipynb
```

Inside the backend container (preferred when DB is inside the `lyra_data` volume):

```bash
docker-compose exec backend pip install -r /app/notebooks/requirements.txt
docker-compose exec backend bash -c "cd /app && jupyter notebook --ip=0.0.0.0 --no-browser --allow-root"
```

## Database access

The SQLite file lives inside the Docker named volume `lyra_data` at
`/app/data/lyra.db`. It is **not** bind-mounted to the host. Three options:

1. **Export to host (read-only snapshot):**
   ```bash
   docker cp $(docker-compose ps -q backend):/app/data/lyra.db ./backend/app/lyra.db
   ```
   Then run the notebook locally — `Cell A` defaults to
   `./backend/app/lyra.db`.

2. **Run the notebook inside the backend container** and set
   `LYRA_DB_PATH=/app/data/lyra.db` in the environment.

3. **Point at a custom path** via the same env var when working off a
   backup / pre-pivot snapshot (`./backend/app/lyra_pre_pivot_apr09.sqlite`).

Never write to the live DB from the notebook. Treat it as read-only.

## Live data hygiene

- The committed `operator_analytics.ipynb` is a **clean template** (no outputs).
- When running against real data, save as `operator_analytics.local.ipynb`.
  That filename is gitignored — outputs, findings, and derived tables stay
  off git.
- `.ipynb_checkpoints/` is also gitignored.
- If a cell output is worth preserving, copy the finding into
  `docs/operator_findings_log.md` as text. Do not commit notebook outputs.

## Cell inventory

| Cell | Purpose |
|------|---------|
| A | DB connection + session setup |
| B | `load_sessions(cohort, date_range)` primary loader |
| C | `plot_distribution(df, column, stratify_by=None)` |
| D | `stratified_corr(df, target, primary, confounder, bucket_strategy)` |
| E | `plot_over_time(df, column, window, agg_func)` |
| F | `category_time_heatmap(df, metric)` |
| G | `plot_cascade_chains(df, date_range)` |
| VT-load | `load_pause_predictions(cohort)` + `load_pause_events(cohort)` — VT-17 data |
| VT-17a | Anchor drift — per-user Spearman ρ, ρ ≤ −0.40 trip |
| VT-17b | Induced pause rate — paired Wilcoxon pre/post first firing, +50% trip |
| VT-17c | Natural vs prompted — Mann-Whitney U on first-pause times, 5-min trip |

Day 10 question cells follow the helpers. Each runs against the dataframe
produced by Cell B with minimal modification. VT-17 cells are the
pre-registered integrity suite from `MANIFESTO.md §VT-17` and must be run
at the end of each user's 7-day acceptance window, independent of the
Day-10/30/60/90 schedule.

## Why hybrid properties are computed in the notebook

`duration_delta_minutes`, `discrepancy_score`, and `signed_discrepancy` are
SQLAlchemy `@hybrid_property` definitions on `backend/app/db/models.py`, not
stored columns. The notebook recomputes them in pandas to match backend
semantics exactly. If the backend definitions change, update Cell B.
