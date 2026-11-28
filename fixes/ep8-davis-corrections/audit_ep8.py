#!/usr/bin/env python3
"""Read-only audit for the ep8-davis-corrections package.

Dumps everything the package touches, in the database's own
vocabulary, before any run:

* PRAGMA table_info (notnull + defaults) for persons,
  relationships, facts, citations, sources, fact_quality_flags,
  unified_photo_catalog and photo_catalog.
* Totals for persons, sources, facts, citations, relationships.
* Full rows for persons 8192 (Ethel Gwendolyn Clark) and 8159
  (Harry Edward Davis): the person row including notes, every
  fact with its citations, and every relationship row touching
  the profile in either direction, ids included (per the 9928
  lesson: relationship storage is not uniform, so gate on the
  actual rows).
* Every relationship row between 8192 and 3591 (John Clark), and
  the live child_of row id for the detach, printed on its own
  DETACH line: fill that id into "expected_relationship_id" in
  ep8_davis_corrections_package.json before the live apply run
  to arm the id gate (see SPEC.md).
* Both photo catalog rows for photos 611 and 617, whichever
  tables carry them.
* The dataset values of the reference sources 667, 860, 1274
  and 1281 (the new sources copy their dataset from these).

Opens the database read-only; never writes.

Usage: python3 audit_ep8.py <path-to-db>
"""
import sqlite3
import sys
from pathlib import Path

TABLES = ("persons", "relationships", "facts", "citations",
          "sources", "fact_quality_flags", "unified_photo_catalog",
          "photo_catalog")
PROFILES = (8192, 8159)
REFERENCE_SOURCES = (667, 860, 1274, 1281)
PHOTOS = (611, 617)


def main():
    if len(sys.argv) != 2:
        print("usage: audit_ep8.py <db path>")
        return 2
    db_path = Path(sys.argv[1])
    if not db_path.exists():
        print(f"database not found: {db_path}")
        return 2
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    def exists(table):
        return cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name=?", (table,)).fetchone() is not None

    print("=" * 72)
    print("SCHEMA (PRAGMA table_info: cid, name, type, notnull, "
          "default, pk)")
    print("=" * 72)
    for table in TABLES:
        print(f"\n-- PRAGMA table_info({table})")
        if not exists(table):
            print("   TABLE MISSING")
            continue
        for r in cur.execute(f"PRAGMA table_info({table})"):
            print(f"   {tuple(r)}")

    print()
    print("=" * 72)
    print("TOTALS")
    print("=" * 72)
    for table in ("persons", "sources", "facts", "citations",
                  "relationships"):
        if exists(table):
            n = cur.execute(
                f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {n}")

    for pid in PROFILES:
        print()
        print("=" * 72)
        print(f"PERSON {pid}")
        print("=" * 72)
        row = cur.execute(
            "SELECT * FROM persons WHERE person_id = ?",
            (pid,)).fetchone()
        if row is None:
            print("   NOT FOUND")
            continue
        for k in row.keys():
            print(f"   {k}: {row[k]!r}")
        print(f"\n-- facts on {pid} (with citations)")
        for f in cur.execute(
                "SELECT * FROM facts WHERE person_id = ? "
                "ORDER BY fact_id", (pid,)):
            print(f"   fact {dict(f)}")
            for c in cur.execute(
                    "SELECT * FROM citations WHERE fact_id = ? "
                    "ORDER BY citation_id", (f["fact_id"],)):
                print(f"      citation {dict(c)}")
        print(f"\n-- relationship rows touching {pid} "
              f"(either direction, all types, ids included)")
        for r in cur.execute(
                "SELECT * FROM relationships WHERE "
                "person_a_id = ? OR person_b_id = ? ORDER BY id",
                (pid, pid)):
            print(f"   {dict(r)}")

    print()
    print("=" * 72)
    print("DETACH TARGET: relationship rows between 8192 and 3591")
    print("=" * 72)
    detach_id = None
    for r in cur.execute(
            "SELECT * FROM relationships WHERE "
            "(person_a_id = 8192 AND person_b_id = 3591) OR "
            "(person_a_id = 3591 AND person_b_id = 8192) "
            "ORDER BY id"):
        print(f"   {dict(r)}")
        if r["person_a_id"] == 8192 and r["person_b_id"] == 3591 \
                and r["relationship_type"] == "child_of":
            detach_id = r["id"]
    print(f"DETACH child_of row id (8192 -> 3591): {detach_id}")
    print("Fill this id into \"expected_relationship_id\" in "
          "ep8_davis_corrections_package.json before the live "
          "apply run (see SPEC.md).")

    print()
    print("=" * 72)
    print("PHOTO CATALOG ROWS for photos 611 and 617")
    print("=" * 72)
    for table in ("unified_photo_catalog", "photo_catalog"):
        print(f"\n-- {table}")
        if not exists(table):
            print("   TABLE MISSING")
            continue
        cols = [r[1] for r in cur.execute(
            f"PRAGMA table_info({table})")]
        if "photo_id" not in cols:
            print("   no photo_id column")
            continue
        for ph in PHOTOS:
            row = cur.execute(
                f"SELECT * FROM {table} WHERE photo_id = ?",
                (ph,)).fetchone()
            print(f"   photo {ph}: "
                  f"{dict(row) if row is not None else 'NO ROW'}")

    print()
    print("=" * 72)
    print("REFERENCE SOURCE DATASETS (new sources copy these)")
    print("=" * 72)
    for sid in REFERENCE_SOURCES:
        row = cur.execute(
            "SELECT source_id, dataset, title FROM sources "
            "WHERE source_id = ?", (sid,)).fetchone()
        print(f"   {dict(row) if row is not None else f'source {sid} MISSING'}")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
