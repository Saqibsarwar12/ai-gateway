import os
import httpx
from typing import Optional, List, Dict, Any

CF_API_TOKEN = os.getenv("CF_API_TOKEN", "")
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID", "")
CF_D1_ID = os.getenv("CF_D1_ID", "")
CF_EMAIL = os.getenv("CF_EMAIL", "")
CLOUDFLARE_GLOBAL_KEY = os.getenv("Cloudflare_Global_API_Key", "")

ENDPOINT = "https://api.cloudflare.com/client/v4"
D1_URL = f"{ENDPOINT}/accounts/{CF_ACCOUNT_ID}/d1/database/{CF_D1_ID}"


def _auth_headers() -> dict:
    """Return auth headers for Cloudflare API."""
    if CLOUDFLARE_GLOBAL_KEY and CF_EMAIL:
        return {
            "X-Auth-Email": CF_EMAIL,
            "X-Auth-Key": CLOUDFLARE_GLOBAL_KEY,
            "Content-Type": "application/json",
        }
    if CF_API_TOKEN:
        return {"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"}
    raise RuntimeError(
        "Cloudflare auth not configured. Set CF_API_TOKEN or both CF_EMAIL and Cloudflare_Global_API_Key."
    )


async def query(sql: str, params: list = None):
    """Execute a SQL query against Cloudflare D1. Returns list of dicts."""
    if not CF_ACCOUNT_ID or not CF_D1_ID:
        raise RuntimeError("CF_ACCOUNT_ID and CF_D1_ID env vars not set")
    try:
        headers = _auth_headers()
        body = {"sql": sql}
        if params:
            body["params"] = params
        url = f"{D1_URL}/query"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=body)
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"D1 error: {data.get('errors')}")
        rows = []
        for r in (data.get("result") or []):
            rows.extend(r.get("results") or [])
        return rows
    except Exception as e:
        raise RuntimeError(f"D1 query failed: {e}") from e


async def execute(sql: str, params: list = None):
    """Execute a non-SELECT statement (INSERT, UPDATE, DELETE, CREATE)."""
    return await query(sql, params)


async def fetchone(sql: str, params: list = None) -> Optional[dict]:
    """Execute a SELECT and return the first row."""
    rows = await query(sql, params)
    return rows[0] if rows else None


async def fetchall(sql: str, params: list = None) -> List[dict]:
    """Execute a SELECT and return all rows."""
    return await query(sql, params)


async def insert(table: str, data: dict) -> str:
    """Insert a row into a table. Returns the id if present."""
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" * len(data))
    vals = list(data.values())
    await execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", vals)
    return data.get("id", "")


async def update(table: str, pk_name: str, pk_value: str, data: dict):
    """Update a row. Returns affected row count."""
    sets = ", ".join(f'"{k}" = ?' for k in data if k != pk_name)
    vals = [v for k, v in data.items() if k != pk_name] + [pk_value]
    await execute(f'UPDATE {table} SET {sets} WHERE "{pk_name}" = ?', vals)


async def delete(table: str, pk_name: str, pk_value: str):
    """Delete a row by primary key."""
    await execute(f'DELETE FROM {table} WHERE "{pk_name}" = ?', [pk_value])


async def insert_many(table: str, rows: List[dict]):
    """Insert multiple rows in a single query."""
    if not rows:
        return
    cols = list(rows[0].keys())
    placeholders = ", ".join(f"({', '.join('?' * len(cols))})" for _ in rows)
    flat_vals = []
    for row in rows:
        flat_vals.extend(row[col] for col in cols)
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES {placeholders}"
    await execute(sql, flat_vals)


async def d1_count(table: str, where: str = None, params: list = None) -> int:
    """Count rows in a table with optional WHERE clause."""
    sql = f"SELECT COUNT(*) as cnt FROM {table}"
    if where:
        sql += f" WHERE {where}"
    row = await fetchone(sql, params)
    return row["cnt"] if row else 0


async def table_exists(table: str) -> bool:
    """Check if a table exists."""
    rows = await fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", [table])
    return len(rows) > 0
