# Testing patterns — cross-user isolation seam guide

**Status:** canonical reference. Last revised 2026-04-27 (Part A of E→A→B→D→C plan).
**Audience:** anyone writing a backend test in this repo.
**Why this exists:** Lyra's per-user scoping is enforced through TWO different seams depending on whether the test goes through the FastAPI middleware or talks directly to the ORM/services. Mixing the seams silently produces tests that pass for the wrong reason. This doc names the patterns explicitly so the trap is visible.

---

## TL;DR — pick your pattern by call shape

| You're calling… | Use this seam | Why |
|---|---|---|
| `TaskManager`, `StopwatchManager`, `DeadlineManager`, `_run_for_one_user`, `db.query(...)` directly | `set_current_user_id(uid)` in fixture | The SQLAlchemy `before_compile` hook reads ContextVar and auto-filters every query by `user_id == uid`. |
| `client.post(...)`, `client.get(...)`, `client.put(...)`, `client.delete(...)` | `headers=auth_headers(uid)` on every call | The `UserScopeMiddleware` overwrites ContextVar from `X-User-Id` per-request. `set_current_user_id` set OUTSIDE the request is wiped on entry and reset on exit. |
| Both (seed via ORM, then drive via TestClient) | Both — `set_current_user_id` AND `auth_headers(uid)` | Patterns 1 + 2 in the same test. |

---

## Pattern 1 — ORM-direct test

**When:** you're calling a service or model directly without going through an HTTP request.

**Seam:** `set_current_user_id(uid)`

**Why it works:** The scoping hook lives in `backend/app/db/scoping.py:41-65`. It hooks SQLAlchemy's `before_compile` event and reads the current_user_id ContextVar (line 50). Every `db.query(SomeModel)` is rewritten to include `WHERE user_id = <ContextVar value>`. Set the ContextVar once in your fixture; every ORM operation in the test body auto-scopes.

```python
import pytest
from app.db.scoping import set_current_user_id
from app.db.models import User, Task
from app.services.task_manager import TaskManager
from tests.conftest import TestingSession


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)              # reset before each test
    db.rollback()
    db.query(Task).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)              # reset after each test
    db.rollback()
    db.query(Task).delete()
    db.query(User).delete()
    db.commit()


def test_task_manager_creates_task_for_user_77(db):
    user = User(user_id=77, email="x@y", ...)
    db.add(user); db.commit()

    set_current_user_id(77)                 # ★ THE SEAM ★
    tm = TaskManager(db)
    task, _, _ = tm.create_task(title="...", start=..., end=...)

    assert task.user_id == 77               # auto-scoped: TaskManager
                                            # read uid from ContextVar
```

**Examples in the codebase:**
- `backend/tests/test_create_task_with_deadline.py` (TaskManager direct)
- `backend/tests/test_multiuser_isolation.py` (raw `db.query` to verify isolation)
- `backend/tests/test_jobs_skip_voided_tasks.py` (background-job per-user functions)
- `backend/tests/test_recovery_and_negative_pause.py` (StopwatchManager direct)
- `backend/tests/test_parser_pass2_keyword_binding.py` (TaskManager direct)
- `backend/tests/test_orphan_task_recovery.py` (per-user job runner)

---

## Pattern 2 — TestClient request

**When:** you're driving an endpoint via `TestClient` (i.e., simulating an HTTP request).

**Seam:** `headers=auth_headers(uid)` on every `client.X(...)` call.

**Why it works:** The `UserScopeMiddleware` at `backend/app/main.py:44-88` reads `X-User-Id` from request headers and calls `set_current_user_id(uid)` for the duration of the request handler. **It overrides whatever the ContextVar was set to outside the request** — calling `set_current_user_id(77)` in your fixture and then `client.post("/endpoint", ...)` without the X-User-Id header silently runs as `user_id=1` (the middleware's default for missing-header fallback at `main.py:50, 76-82`).

This is the single most-common cross-user-isolation trap. The footgun is that the test PASSES — the middleware just operates on whatever data user_id=1 has.

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import auth_headers   # ★ THE HELPER ★

client = TestClient(app, raise_server_exceptions=False)


def test_archetype_endpoint_for_user_77(db):
    # Seed via ORM (Pattern 1 inside the seeding only — see Pattern 3)
    set_current_user_id(77)
    # ... seed user 77's data ...
    set_current_user_id(None)               # release before TestClient call

    # Drive via TestClient with header (Pattern 2)
    resp = client.post(
        "/v1/users/me/archetype-survey",
        json={...},
        headers=auth_headers(77),           # ★ THE SEAM ★
    )
    assert resp.status_code == 200
```

**Examples in the codebase:**
- `backend/tests/test_archetype_endpoints.py` (every TestClient call uses header)
- `backend/tests/test_deadline_endpoints.py` (CRUD endpoints with header)
- `backend/tests/test_analytics_pause_prediction.py` (pre-existing X-User-Id pattern)

**The footgun in code form**:
```python
# ❌ WRONG — silently runs as user_id=1, NOT user 77
set_current_user_id(77)
resp = client.post("/v1/something", json={...})

# ✓ CORRECT
resp = client.post("/v1/something", json={...}, headers=auth_headers(77))
```

---

## Pattern 3 — Cross-user isolation verification

**When:** you're writing a test that asserts user A cannot see user B's data through the API.

**Seam:** Pattern 1 (seeding) + Pattern 2 (driving) for two different users.

```python
def test_user_a_cannot_see_user_b_deadlines(db):
    user_a = _make_user(db, "a@example.com")
    user_b = _make_user(db, "b@example.com")

    # Seed user B's deadline (drives via TestClient as B, not direct ORM —
    # this exercises the full create + scope path)
    client.post(
        "/v1/deadlines",
        json={"title": "B's secret deadline", ...},
        headers=auth_headers(user_b.user_id),
    )

    # Query as user A — should see nothing
    resp = client.get("/v1/deadlines", headers=auth_headers(user_a.user_id))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0   # B's deadline invisible to A

    # 404 (not 403) on direct fetch — avoid existence-leak
    b_deadline_id = ...   # captured from B's create response
    resp = client.get(
        f"/v1/deadlines/{b_deadline_id}",
        headers=auth_headers(user_a.user_id),
    )
    assert resp.status_code == 404
```

**Examples in the codebase:**
- `backend/tests/test_deadline_endpoints.py::test_list_deadlines_cross_user_isolation`
- `backend/tests/test_deadline_endpoints.py::test_get_deadline_cross_user_returns_404`
- `backend/tests/test_create_task_with_deadline.py::test_wrong_user_rejection`
- `backend/tests/test_multiuser_isolation.py::test_user_a_query_excludes_user_b_tasks`

---

## The middleware's default-to-user-id-1 footgun

`backend/app/main.py:50, 76-82`:

```python
user_id = 1                                    # ← DEFAULT
# ... try Bearer token ...
if not resolved:
    raw = request.headers.get("X-User-Id")
    if raw is not None:
        try:
            user_id = int(raw)
        except ValueError:
            user_id = 1                        # malformed → default
# ELSE user_id stays as 1 — silently
set_current_user_id(user_id)
```

This default exists for backwards compatibility with single-user dev clients. It is **not** a bug — it's a deliberate compatibility shim documented at line 29 of `main.py`. But it means **any TestClient call without X-User-Id silently runs as the operator (user_id=1)**.

If your test seeds user_id=77's data and then calls `client.get(...)` without `auth_headers(77)`, the request runs as user_id=1. user_id=1 has no rows in user 77's seeded data, so most tests fall through to "empty response" or 404 — which often happens to match the test's expectation, hiding the bug.

The only way the bug surfaces is when user_id=1 happens to have data that satisfies a different assertion. **Do not rely on coincidence.** Use `auth_headers(uid)` every time.

---

## The `auth_headers` helper

Defined in `backend/tests/conftest.py`:

```python
def auth_headers(user_id: int) -> dict:
    """Build an X-User-Id header dict for TestClient requests.

    Always use this when calling client.{post,get,put,delete}. Without it,
    UserScopeMiddleware defaults to user_id=1 silently.
    """
    return {"X-User-Id": str(user_id)}
```

Import in test files: `from tests.conftest import auth_headers`.

---

## When in doubt — recipe for any new test

1. **Am I calling `client.{post,get,put,delete}`?** → Pattern 2: pass `auth_headers(uid)` on every call.
2. **Am I calling a service or `db.query(...)` directly?** → Pattern 1: `set_current_user_id(uid)` in fixture.
3. **Both?** → Both seams, scoped to the same uid.
4. **Cross-user assertion?** → Pattern 3.
5. **None of the above?** → If your test doesn't touch user-scoped data at all (e.g., pure unit test of `extract_scope_bullets(...)`), neither seam is needed.

---

## SIR + voided_at + research-integrity discipline (orthogonal but related)

These patterns sit alongside two other backend-test disciplines that EVERY test must respect:

- **`voided_at IS NULL` filter** (per `feedback_voided_at_guard` memory): every `Task` query asserts voided rows are excluded. Many existing tests demonstrate this pattern (`backend/tests/test_create_task_with_deadline.py::test_voided_deadline_rejection`, etc).
- **External-source contamination** (per CLAUDE.md:156): if your test touches imported event data, filter `external_source IS NULL` to keep the H1/H2 measurement layer clean. Currently relevant only to `external_event_outcome` analytics tests.

Cross-user isolation is the seam discipline. voided_at + external_source are the data-purity disciplines. They are orthogonal — a test can pass cross-user isolation while silently leaking voided rows, or vice versa.
