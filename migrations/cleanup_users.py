"""Migration: Remove all non-admin users from D1.

Safe to run multiple times. Preserves the admin account specified by
ADMIN_EMAIL env var (default: saqibsarwar003@gmail.com).

Usage:
    python migrations/cleanup_users.py
    ADMIN_EMAIL=admin@example.com python migrations/cleanup_users.py --dry-run
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime

# Add backend to path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.db.cloudflare import fetchall, execute


ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "saqibsarwar003@gmail.com").lower()


async def get_tables() -> list[str]:
    rows = await fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return [r["name"] for r in rows]


async def count_rows(table: str, where: str = "") -> int:
    sql = f"SELECT COUNT(*) as cnt FROM {table}"
    if where:
        sql += f" WHERE {where}"
    row = await fetchone(sql)
    return row["cnt"] if row else 0


async def fetchone(sql: str, params: list = None) -> dict | None:
    rows = await fetchall(sql, params)
    return rows[0] if rows else None


async def cleanup(dry_run: bool = False) -> None:
    tables = await get_tables()
    print(f"Found tables: {', '.join(tables)}")

    # 1. Find admin user
    admin_rows = await fetchall(
        'SELECT id, email, role FROM users WHERE LOWER(email) = ?',
        [ADMIN_EMAIL],
    )
    if not admin_rows:
        print(f"ERROR: Admin user with email {ADMIN_EMAIL} not found in users table.")
        print("Aborting to avoid deleting the only admin.")
        sys.exit(1)

    admin = admin_rows[0]
    if admin["role"] != "admin":
        print(f"WARNING: Admin user {ADMIN_EMAIL} has role '{admin['role']}', not 'admin'.")
        print("Proceeding anyway, but verify this is correct.")

    admin_id = admin["id"]
    print(f"Admin to preserve: id={admin_id} email={admin['email']} role={admin['role']}")

    # 2. Count what will be deleted
    non_admin_users = await fetchall(
        'SELECT id, email, role FROM users WHERE id != ?',
        [admin_id],
    )
    pending = await fetchall("SELECT id, email FROM pending_registrations")
    tokens = await fetchall(
        "SELECT id, user_id FROM verification_tokens WHERE user_id != ?",
        [admin_id],
    )
    api_keys = await fetchall(
        "SELECT id, user_id FROM api_keys WHERE user_id != ?",
        [admin_id],
    )
    gateway_configs = await fetchall(
        "SELECT id, user_id FROM user_gateway_configs WHERE user_id != ?",
        [admin_id],
    )
    request_logs = await fetchall(
        "SELECT id, user_id FROM request_logs WHERE user_id != ?",
        [admin_id],
    )
    usage_stats = await fetchall(
        "SELECT id, user_id FROM usage_stats WHERE user_id != ?",
        [admin_id],
    )

    print("\n=== Deletion Plan ===")
    print(f"Non-admin users:          {len(non_admin_users)}")
    print(f"Pending registrations:    {len(pending)}")
    print(f"Verification tokens:      {len(tokens)}")
    print(f"API keys:                 {len(api_keys)}")
    print(f"Gateway configs:          {len(gateway_configs)}")
    print(f"Request logs:             {len(request_logs)}")
    print(f"Usage stats:              {len(usage_stats)}")

    if dry_run:
        print("\nDRY RUN — no changes made.")
        return

    # 3. Delete in order (respecting FK-ish relationships)
    print("\nDeleting...")

    # Delete request logs for non-admin users
    if request_logs:
        ids = [r["id"] for r in request_logs]
        placeholders = ",".join(["?"] * len(ids))
        res = await execute(
            f"DELETE FROM request_logs WHERE id IN ({placeholders})", ids
        )
        print(f"  Deleted {len(request_logs)} request logs")

    # Delete usage stats for non-admin users
    if usage_stats:
        ids = [r["id"] for r in usage_stats]
        placeholders = ",".join(["?"] * len(ids))
        res = await execute(
            f"DELETE FROM usage_stats WHERE id IN ({placeholders})", ids
        )
        print(f"  Deleted {len(usage_stats)} usage stats")

    # Delete gateway configs for non-admin users
    if gateway_configs:
        ids = [r["id"] for r in gateway_configs]
        placeholders = ",".join(["?"] * len(ids))
        res = await execute(
            f"DELETE FROM user_gateway_configs WHERE id IN ({placeholders})", ids
        )
        print(f"  Deleted {len(gateway_configs)} gateway configs")

    # Delete API keys for non-admin users
    if api_keys:
        ids = [r["id"] for r in api_keys]
        placeholders = ",".join(["?"] * len(ids))
        res = await execute(
            f"DELETE FROM api_keys WHERE id IN ({placeholders})", ids
        )
        print(f"  Deleted {len(api_keys)} API keys")

    # Delete verification tokens for non-admin users
    if tokens:
        ids = [r["id"] for r in tokens]
        placeholders = ",".join(["?"] * len(ids))
        res = await execute(
            f"DELETE FROM verification_tokens WHERE id IN ({placeholders})", ids
        )
        print(f"  Deleted {len(tokens)} verification tokens")

    # Delete pending registrations
    if pending:
        ids = [r["id"] for r in pending]
        placeholders = ",".join(["?"] * len(ids))
        res = await execute(
            f"DELETE FROM pending_registrations WHERE id IN ({placeholders})", ids
        )
        print(f"  Deleted {len(pending)} pending registrations")

    # Delete non-admin users
    if non_admin_users:
        ids = [r["id"] for r in non_admin_users]
        placeholders = ",".join(["?"] * len(ids))
        res = await execute(
            f"DELETE FROM users WHERE id IN ({placeholders})", ids
        )
        print(f"  Deleted {len(non_admin_users)} non-admin users")

    # 4. Verify
    remaining_users = await fetchall("SELECT id, email, role FROM users")
    print(f"\nRemaining users: {len(remaining_users)}")
    for u in remaining_users:
        print(f"  {u['id']} | {u['email']} | {u['role']}")

    remaining_pending = await count_rows("pending_registrations")
    print(f"Remaining pending registrations: {remaining_pending}")

    print("\nCleanup complete.")


def main():
    parser = argparse.ArgumentParser(description="Cleanup non-admin users from D1")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    args = parser.parse_args()

    asyncio.run(cleanup(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
