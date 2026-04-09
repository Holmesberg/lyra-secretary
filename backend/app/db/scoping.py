"""Multi-user query auto-scoping.

Structural defense against cross-user data leaks. Every SQLAlchemy query
against a table that has a `user_id` column is rewritten at compile time
to filter by the current user's id, set via `set_current_user_id()`
inside the per-request auth dependency.

This is the most important file in the multi-user migration. If a query
is built with the model classes (e.g. `db.query(Task).filter(...)`), it
goes through the ORM's `before_compile` event and is auto-scoped. Raw
`db.execute(text(...))` queries bypass this — those must scope manually.

Models opted into scoping: any model whose `__table__` has a `user_id`
column. The `User` model itself is exempt (you cannot scope the user
table by user_id without a chicken-and-egg problem).

Reading the current user:
- Set in the request lifecycle by `get_current_user` dependency.
- Stored in a `contextvars.ContextVar` so concurrent requests don't mix.
- If unset (e.g. background job, test, migration), the hook is a no-op
  and queries run unscoped. Background jobs that iterate users MUST set
  the user_id explicitly per iteration via `set_current_user_id()`.
"""
from contextvars import ContextVar
from typing import Optional

from sqlalchemy import event
from sqlalchemy.orm import Query, with_loader_criteria

_current_user_id: ContextVar[Optional[int]] = ContextVar("current_user_id", default=None)


def set_current_user_id(user_id: Optional[int]) -> None:
    _current_user_id.set(user_id)


def get_current_user_id() -> Optional[int]:
    return _current_user_id.get()


def install_scoping(Base) -> None:
    """Install the before_compile hook on the given declarative Base.

    Walks all mapped classes; any with a `user_id` attribute gets a
    `with_loader_criteria` injection on every query that touches it.
    """

    @event.listens_for(Query, "before_compile", retval=True)
    def _add_user_filter(query: Query) -> Query:  # noqa: ANN001
        user_id = _current_user_id.get()
        if user_id is None:
            return query
        for desc in query.column_descriptions:
            entity = desc.get("entity")
            if entity is None:
                continue
            table = getattr(entity, "__table__", None)
            if table is None or "user_id" not in table.c:
                continue
            # Exempt the User table itself: its `user_id` column is the
            # primary key (the identity), not a foreign owner pointer.
            if table.c.user_id.primary_key:
                continue
            query = query.enable_assertions(False).filter(entity.user_id == user_id)
        return query
