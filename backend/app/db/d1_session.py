"""Minimal D1 session adapter — covers what admin.py needs.

Maps SQLAlchemy ORM patterns to Cloudflare D1 REST API calls.
When USE_D1=true, this replaces the SQLAlchemy async session.

Supported patterns:
  - session.execute(select(Model).where(...))
  - session.add(new_obj) → INSERT OR REPLACE
  - obj.attr = val; await session.commit() → UPDATE via dirty tracking
  - session.delete(obj) → DELETE
  - result.scalar_one_or_none(), result.scalars().all(), result.scalar()
"""

import json
from copy import deepcopy
from datetime import datetime
from typing import Optional, List, Any

from sqlalchemy import Select
from app.db.cloudflare import fetchall, execute


def _model_to_dict(obj) -> dict:
    """Convert a SQLAlchemy model instance to a flat dict for D1.
    Includes ALL columns — even None values — so INSERT OR REPLACE
    doesn't silently NULL out unmentioned columns.
    Booleans → 0/1 (SQLAlchemy emits WHERE col=1 for bool comparisons).
    """
    data = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name, None)
        if val is not None:
            if isinstance(val, datetime):
                val = val.isoformat()
            elif isinstance(val, bool):
                val = 1 if val else 0
            elif isinstance(val, (list, dict)):
                val = json.dumps(val)
        data[col.name] = val
    return data


def _row_to_model(row: dict, model_class):
    """Convert a D1 row dict back to a model instance."""
    kwargs = {}
    for col in model_class.__table__.columns:
        val = row.get(col.name)
        if val is not None:
            try:
                from sqlalchemy import DateTime, JSON, Boolean, Integer, Float
                col_type = col.type
                if isinstance(col_type, DateTime) and isinstance(val, str):
                    val = datetime.fromisoformat(val.replace('Z', '+00:00'))
                elif isinstance(col_type, JSON) and isinstance(val, str):
                    val = json.loads(val)
                elif isinstance(col_type, Boolean):
                    # D1 stores booleans as 0/1 (our convention) or "true"/"false" (legacy)
                    if isinstance(val, str):
                        val = val.lower() in ("1", "true")
                    else:
                        val = bool(int(val))
                elif isinstance(col_type, Integer):
                    val = int(val)
                elif isinstance(col_type, Float):
                    val = float(val)
            except Exception:
                pass
        kwargs[col.name] = val
    return model_class(**kwargs)


def _pk_pair(obj):
    """Get (pk_name, pk_value) for a model instance."""
    for col in obj.__table__.primary_key.columns:
        return col.name, str(getattr(obj, col.name, ""))
    return None, None


def _tracking_key(obj) -> Optional[str]:
    """Build a stable tracking key from table name + primary key."""
    table = obj.__tablename__
    pk_name, pk_val = _pk_pair(obj)
    if pk_name and pk_val:
        return f"{table}:{pk_val}"
    return None


def _snapshot(obj) -> dict:
    """Take a snapshot of all column values for dirty checking."""
    snap = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name, None)
        if isinstance(val, (list, dict)):
            snap[col.name] = deepcopy(val)
        else:
            snap[col.name] = val
    return snap


def _normalize(val):
    """Normalize a value for dirty-check comparison."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, (list, dict)):
        return json.dumps(val, sort_keys=True)
    return val


def _is_dirty(obj, snapshot: dict) -> bool:
    """Check if any column value changed from snapshot."""
    for col in obj.__table__.columns:
        current = _normalize(getattr(obj, col.name, None))
        old = snapshot.get(col.name)
        if current != old:
            return True
    return False


def _compile_select(statement: Select) -> tuple:
    """Compile a SQLAlchemy Select into (sql_string, params_list).
    Converts :name placeholders to ? since D1 only supports positional params.
    """
    try:
        compiled = statement.compile(compile_kwargs={"literal_binds": True})
        return str(compiled), []
    except Exception:
        compiled = statement.compile()
        sql = str(compiled)
        params = compiled.params if hasattr(compiled, "params") and compiled.params else {}
        param_list = list(params.values()) if params else []
        return sql, param_list


def _extract_model(statement):
    """Try to extract the model class from a Select statement."""
    if hasattr(statement, "column_descriptions") and statement.column_descriptions:
        desc = statement.column_descriptions[0]
        entity = desc.get("entity")
        if entity is not None:
            return entity
        expr = desc.get("expr")
        if expr is not None and hasattr(expr, "table"):
            return expr.table
    return None


def _is_count_query(statement):
    """Detect if this is a COUNT(*) query."""
    for cd in statement.column_descriptions or []:
        expr = cd.get("expr")
        if expr is not None and hasattr(expr, "name") and expr.name == "count":
            return True
    return False


def _upsert_sql(table_name: str, data: dict) -> tuple:
    """Build INSERT OR REPLACE SQL and params for D1."""
    cols = ", ".join(f'"{k}"' for k in data.keys())
    placeholders = ", ".join("?" * len(data))
    sql = f"INSERT OR REPLACE INTO {table_name} ({cols}) VALUES ({placeholders})"
    return sql, list(data.values())


class D1Result:
    """Minimal result wrapper that mimics SQLAlchemy's Result."""

    def __init__(self, rows: list, model_class=None):
        self._rows = rows
        self._model_class = model_class
        self.session = None

    def scalar_one_or_none(self):
        if not self._rows:
            return None
        row = self._rows[0]
        if self._model_class:
            obj = _row_to_model(row, self._model_class)
            if self.session:
                self.session._track(obj)
            return obj
        return row

    def scalars(self):
        return self

    def all(self):
        if self._model_class:
            objs = [_row_to_model(row, self._model_class) for row in self._rows]
            if self.session:
                for obj in objs:
                    self.session._track(obj)
            return objs
        return self._rows

    def scalar(self):
        if not self._rows:
            return None
        row = self._rows[0]
        if isinstance(row, dict):
            return list(row.values())[0] if row else None
        return row


class D1Session:
    """An async session-like object that delegates to Cloudflare D1.

    Tracks loaded objects for dirty checking via snapshots.
    At commit(): flushes explicit adds/deletes, then upserts any
    loaded objects that changed from their snapshots.
    """

    def __init__(self):
        self._adds: list = []       # objects to INSERT
        self._deletes: list = []    # objects to DELETE
        self._snapshots: dict = {}  # pk_key -> original snapshot dict
        self._objects: dict = {}  # pk_key -> object

    def _track(self, obj):
        """Snapshot an object so we can dirty-check at commit time."""
        key = self._pk_key(obj)
        if key not in self._snapshots:
            self._snapshots[key] = _model_to_dict(obj)
            self._objects[key] = obj

    def _pk_key(self, obj) -> str:
        """Compute a stable key from the object's primary key."""
        parts = []
        for col in obj.__table__.primary_key.columns:
            parts.append(str(getattr(obj, col.name, "")))
        return f"{obj.__tablename__}:{':'.join(parts)}"

    async def execute(self, statement):
        """Execute a SQLAlchemy Select statement against D1."""
        if isinstance(statement, Select):
            model_class = _extract_model(statement)
            is_count = _is_count_query(statement)
            sql, params = _compile_select(statement)
            rows = await fetchall(sql, params if params else None)
            result = D1Result(rows, None if is_count else model_class)
            if model_class and not is_count:
                result.session = self
            return result
        raise ValueError(f"Unsupported statement type: {type(statement)}")

    def add(self, obj):
        """Queue an INSERT (or REPLACE)."""
        self._adds.append(obj)

    def delete(self, obj):
        """Queue a DELETE."""
        self._deletes.append(obj)

    async def commit(self):
        """Flush all pending operations + dirty-check all tracked objects."""

        # 1. Dirty-check tracked objects → UPSERT if changed
        for key, snapshot in list(self._snapshots.items()):
            obj = self._objects.get(key)
            if obj and _is_dirty(obj, snapshot):
                data = _model_to_dict(obj)
                sql, params = _upsert_sql(obj.__tablename__, data)
                await execute(sql, params)

        # 2. Process adds
        for obj in self._adds:
            data = _model_to_dict(obj)
            sql, params = _upsert_sql(obj.__tablename__, data)
            await execute(sql, params)

        # 3. Process deletes
        for obj in self._deletes:
            pk_name, pk_val = _pk_pair(obj)
            if pk_name:
                await execute(
                    f'DELETE FROM {obj.__tablename__} WHERE "{pk_name}" = ?',
                    [pk_val],
                )

        self._adds = []
        self._deletes = []
        self._snapshots = {}

    async def rollback(self):
        self._adds = []
        self._deletes = []
        self._snapshots = {}

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


def d1_session_maker():
    """Factory that returns a new D1Session (mimics async_sessionmaker)."""
    return D1Session()
