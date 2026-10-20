"""Small helpers to load the CSVs into SQLite and run the SQL files in /sql."""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SQL_DIR = ROOT / "sql"


def build_database(path: str = ":memory:") -> sqlite3.Connection:
    """Load stores, vendors, and work_orders into SQLite and create the staging view."""
    con = sqlite3.connect(path)
    for table in ("stores", "vendors", "work_orders"):
        pd.read_csv(DATA_DIR / f"{table}.csv").to_sql(table, con, index=False, if_exists="replace")
    con.executescript((SQL_DIR / "00_stg_work_orders.sql").read_text())
    return con


def run_sql(con: sqlite3.Connection, filename: str, **params) -> pd.DataFrame:
    """Run one of the .sql files in /sql and return the result as a DataFrame."""
    query = (SQL_DIR / filename).read_text()
    return pd.read_sql_query(query, con, params=params or None)
