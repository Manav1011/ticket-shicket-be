#!/usr/bin/env python3
"""Raw SQL query engine — run any query against the database.

Usage:
    uv run python scripts/db_query_engine.py "SELECT * FROM orders LIMIT 3"
    uv run python scripts/db_query_engine.py "SELECT status, count(*) FROM orders GROUP BY status"
    uv run python scripts/db_query_engine.py "UPDATE orders SET status='expired' WHERE id='abc'" --commit
"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "src")

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

ENGINE_URL = "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"


async def run_query(sql: str, *, commit: bool = False):
    engine = create_async_engine(ENGINE_URL, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(sa.text(sql))
        if result.returns_rows:
            cols = result.keys()
            rows = result.fetchall()
            return True, cols, rows
        else:
            await conn.commit() if commit else None
            return False, result.rowcount, None


def format_rows(cols, rows) -> str:
    if not rows:
        return "(no rows)"
    cols_list = list(cols)
    rows_list = [tuple(r) for r in rows]
    widths = {
        i: max(
            len(str(cols_list[i])),
            max(len(str(r[i])) for r in rows_list) if rows_list else 0,
        )
        for i in range(len(cols_list))
    }
    header = " | ".join(str(cols_list[i]).ljust(widths[i]) for i in range(len(cols_list)))
    sep = "-+-".join("-" * widths[i] for i in range(len(cols_list)))
    lines = [header, sep]
    for row in rows_list:
        lines.append(" | ".join(str(row[i]).ljust(widths[i]) for i in range(len(row))))
    return "\n".join(lines)


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Raw SQL query engine (testing only)")
    parser.add_argument("sql", nargs="?", help="SQL query to run")
    parser.add_argument("--commit", action="store_true", help="Commit the transaction (required for writes)")
    args = parser.parse_args()

    if not args.sql:
        parser.print_help()
        return

    has_rows, cols_or_rc, data = await run_query(args.sql, commit=args.commit)
    if has_rows:
        print(format_rows(list(cols_or_rc), data))
    elif isinstance(cols_or_rc, int):
        print(f"OK — {cols_or_rc} row(s) affected")
    else:
        print(data)


if __name__ == "__main__":
    asyncio.run(main())
