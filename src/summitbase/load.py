"""Load: rebuild the staging schema and bulk-load data with PostgreSQL COPY."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import psycopg

from summitbase.config import SQL_DIR, TABLES


def run_sql_file(conn: psycopg.Connection, path: Path) -> None:
    conn.execute(path.read_text(encoding="utf-8"))


def copy_dataframe(conn: psycopg.Connection, schema: str, table: str, df: pd.DataFrame) -> int:
    """Stream a DataFrame into an existing table using COPY (fast for 100k+ rows)."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep="", date_format="%Y-%m-%d %H:%M:%S")
    buffer.seek(0)
    columns = ", ".join(df.columns)
    with conn.cursor() as cur:
        sql = f"COPY {schema}.{table} ({columns}) FROM STDIN WITH (FORMAT csv)"
        with cur.copy(sql) as copy:
            while chunk := buffer.read(1 << 20):
                copy.write(chunk)
    return len(df)


def load_all(conninfo: str, tables: dict[str, pd.DataFrame]) -> dict[str, int]:
    """Full refresh inside a single transaction: either everything loads or nothing."""
    counts: dict[str, int] = {}
    with psycopg.connect(conninfo) as conn:
        run_sql_file(conn, SQL_DIR / "01_staging_schema.sql")
        for name in TABLES:
            counts[name] = copy_dataframe(conn, "staging", name, tables[name])
        run_sql_file(conn, SQL_DIR / "02_analytics_views.sql")
    return counts
