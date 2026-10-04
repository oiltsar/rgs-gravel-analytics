"""Load: parquet -> DuckDB (data/gravel.duckdb) + витрины из sql/marts.sql."""
from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "gravel.duckdb"
TABLES = ("dim_event", "dim_race", "dim_rider", "fct_result")


def connect(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def main() -> None:
    DB_PATH.unlink(missing_ok=True)
    con = connect(read_only=False)
    for t in TABLES:
        con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_parquet('{PROCESSED / t}.parquet')")
    con.execute((ROOT / "sql" / "marts.sql").read_text(encoding="utf-8"))
    for (name,) in con.execute("SELECT table_name FROM information_schema.tables ORDER BY 1").fetchall():
        n = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"{name:<20} {n:>6}")
    con.close()


if __name__ == "__main__":
    main()
