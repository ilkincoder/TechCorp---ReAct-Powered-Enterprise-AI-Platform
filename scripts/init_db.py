"""Initialize PostgreSQL database — load all CSVs into tables.
   Runs on container startup. Idempotent: drops and recreates tables each run."""

import csv
import re
import sys
import time
from pathlib import Path

import psycopg2
import psycopg2.extras
from psycopg2 import sql

sys.path.insert(0, str(Path(__file__).parent.parent))

from techcorp_platform.config import (
    POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB,
    POSTGRES_HOST, POSTGRES_PORT, DATA_DIR,
)


def wait_for_postgres():
    """Wait until PostgreSQL is accepting connections."""
    for attempt in range(30):
        try:
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                dbname=POSTGRES_DB,
            )
            conn.close()
            print(f"  PostgreSQL ready on {POSTGRES_HOST}:{POSTGRES_PORT}")
            return
        except psycopg2.OperationalError:
            print(f"  Waiting for PostgreSQL... ({attempt + 1}/30)")
            time.sleep(2)
    raise RuntimeError("PostgreSQL did not become ready in 60 seconds.")


def infer_column_type(col_name: str, sample_values: list[str]) -> str:
    """Guess PostgreSQL column type from sample values."""
    # Try INTEGER
    int_count = 0
    for v in sample_values:
        v = v.strip()
        if not v:
            continue
        try:
            int(v)
            int_count += 1
        except ValueError:
            break
    if int_count == len([v for v in sample_values if v.strip()]):
        return "INTEGER"

    # Try TIMESTAMP/DATE (must start with ISO date pattern: YYYY-MM-DD)
    for v in sample_values:
        v = v.strip()
        if not v:
            continue
        # ISO 8601 timestamp: 2024-01-15T10:30:00 or 2024-01-15T10:30:00+00:00
        if re.match(r"^\d{4}-\d{2}-\d{2}T", v):
            return "TIMESTAMP"
        # ISO date: 2024-01-15
        if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            return "DATE"

    # Default: TEXT
    return "TEXT"


def init_db():
    print("\n  Initializing PostgreSQL database...\n")

    wait_for_postgres()

    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        dbname=POSTGRES_DB,
    )
    conn.autocommit = True
    cur = conn.cursor()

    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        print("  No CSV files found in data/ directory.")
        conn.close()
        return

    loaded = 0

    for csv_path in csv_files:
        table_name = csv_path.stem.replace("-", "_").replace(" ", "_").lower()

        try:
            with open(csv_path, newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    continue

                # Normalize column names: lowercase, replace spaces/hyphens
                raw_columns = list(reader.fieldnames)
                safe_columns = [
                    re.sub(r"[^a-zA-Z0-9_]", "_", c).lower().strip("_")
                    for c in raw_columns
                ]

                # Handle duplicate column names
                seen = {}
                unique_columns = []
                for c in safe_columns:
                    if c in seen:
                        seen[c] += 1
                        unique_columns.append(f"{c}_{seen[c]}")
                    else:
                        seen[c] = 0
                        unique_columns.append(c)

                # Read all rows
                all_rows = []
                for row in reader:
                    all_rows.append([row.get(f, "") for f in raw_columns])

                if not all_rows:
                    continue

                # Infer types from first 20 rows
                sample = [row for row in all_rows[:20]]
                col_types = []
                for i, col_name in enumerate(unique_columns):
                    values = [row[i] for row in sample]
                    col_types.append(infer_column_type(col_name, values))

                # Drop and create table
                cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                    sql.Identifier(table_name)
                ))

                col_defs = [
                    sql.SQL("{} {}").format(
                        sql.Identifier(unique_columns[i]),
                        sql.SQL(col_types[i]),
                    )
                    for i in range(len(unique_columns))
                ]

                cur.execute(
                    sql.SQL("CREATE TABLE {} ({})").format(
                        sql.Identifier(table_name),
                        sql.SQL(", ").join(col_defs),
                    )
                )

                # Insert data (batched)
                placeholders = sql.SQL(", ").join([sql.Placeholder()] * len(unique_columns))
                insert_sql = sql.SQL("INSERT INTO {} VALUES ({})").format(
                    sql.Identifier(table_name),
                    placeholders,
                )

                batch_size = 500
                for i in range(0, len(all_rows), batch_size):
                    batch = all_rows[i : i + batch_size]
                    # Convert to proper types
                    typed_batch = []
                    for row in batch:
                        typed_row = []
                        for j, val in enumerate(row):
                            if col_types[j] == "INTEGER":
                                try:
                                    typed_row.append(int(val) if val.strip() else None)
                                except (ValueError, TypeError):
                                    typed_row.append(val)
                            elif col_types[j] in ("TIMESTAMP", "DATE"):
                                typed_row.append(val if val.strip() else None)
                            else:
                                typed_row.append(val)
                        typed_batch.append(typed_row)

                    psycopg2.extras.execute_batch(cur, insert_sql, typed_batch)

                # Count
                cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(
                    sql.Identifier(table_name)
                ))
                count = cur.fetchone()[0]

                print(f"  ✓ {table_name:<30s} {count:>5} rows  ({len(unique_columns)} cols)")
                loaded += 1

        except Exception as e:
            print(f"  ✗ {csv_path.name}: {e}")
            conn.rollback()

    cur.close()
    conn.close()

    print(f"\n  Done. {loaded} tables loaded into PostgreSQL.\n")


if __name__ == "__main__":
    init_db()