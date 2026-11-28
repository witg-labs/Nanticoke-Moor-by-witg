#!/usr/bin/env python3
"""Read-only audit for the john-clark-3591-untangle package.

Dumps everything the package touches, in the database's own
vocabulary, before any run:

* PRAGMA table_info (notnull + defaults) for persons,
  relationships, facts, citations and sources.
* Totals for persons, sources, facts, citations, relationships.
* Full rows for person 3591 (John Clark): the person row
  including notes, source_page and dataset_source, every fact
  with its citations, and every relationship row touching the
  profile in either direction, ids included (per the 9928
  lesson: relationship storage is not uniform, so gate on the
  actual rows).
* The fact list of person 8193 (John Wesley Clark Jr), who
  receives the moved 1930 census fact.
* Person 9622 (John Wesley Clark Sr): source_page and
  dataset_source, the values 3591's row is aligned to.
* The Ep8 dependency check, on its own line:
  "EP8 DEPENDENCY: rows between 8192 and 3591: <n>".
  This package runs only when that number is 0 (the
  ep8-davis-corrections package deletes the child_of row
  8192 -> 3591 and must run first).
* One WILL DELETE line per relationship row the package will
  delete (spouse rows to 8194; child_of / parent_of rows to
  8195, 8210, 8196, 8207), with ids: fill those ids into each
  removal's "expected_ids" in
  john_clark_3591_untangle_package.json before the live apply
  run to arm the id gate (see SPEC.md). Rows of an ignored type
  (cross_dataset_match) are printed as LEFT IN PLACE; any other
  unexpected row type is printed as UNEXPECTED (the apply run
  aborts on those).

Opens the database read-only; never writes.

Usage: python3 audit_3591.py <path-to-db>
"""
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = json.loads(
    (HERE / "john_clark_3591_untangle_package.json").read_text(
        encoding="utf-8"))
TABLES = ("persons", "relationships", "facts", "citations",
          "sources")
TARGET = SPEC["target_person"]["person_id"]


def main():
    if len(sys.argv) != 2:
        print("usage: audit_3591.py <db path>")
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
    for table in TABLES:
        if exists(table):
            n = cur.execute(
                f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {n}")

    print()
    print("=" * 72)
    print(f"PERSON {TARGET} (John Clark)")
    print("=" * 72)
    row = cur.execute(
        "SELECT * FROM persons WHERE person_id = ?",
        (TARGET,)).fetchone()
    if row is None:
        print("   NOT FOUND")
    else:
        for k in row.keys():
            print(f"   {k}: {row[k]!r}")
        print(f"\n-- facts on {TARGET} (with citations)")
        for f in cur.execute(
                "SELECT * FROM facts WHERE person_id = ? "
                "ORDER BY fact_id", (TARGET,)):
            print(f"   fact {dict(f)}")
            for c in cur.execute(
                    "SELECT * FROM citations WHERE fact_id = ? "
                    "ORDER BY citation_id", (f["fact_id"],)):
                print(f"      citation {dict(c)}")
        print(f"\n-- relationship rows touching {TARGET} "
              f"(either direction, all types, ids included)")
        for r in cur.execute(
                "SELECT * FROM relationships WHERE "
                "person_a_id = ? OR person_b_id = ? ORDER BY id",
                (TARGET, TARGET)):
            print(f"   {dict(r)}")

    print()
    print("=" * 72)
    print("PERSON 8193 (John Wesley Clark Jr): fact list")
    print("=" * 72)
    for f in cur.execute(
            "SELECT * FROM facts WHERE person_id = 8193 "
            "ORDER BY fact_id"):
        print(f"   fact {dict(f)}")
        for c in cur.execute(
                "SELECT * FROM citations WHERE fact_id = ? "
                "ORDER BY citation_id", (f["fact_id"],)):
            print(f"      citation {dict(c)}")

    print()
    print("=" * 72)
    print("PERSON 9622 (John Wesley Clark Sr): source alignment "
          "reference")
    print("=" * 72)
    ref = cur.execute(
        "SELECT person_id, name, source_page, dataset_source "
        "FROM persons WHERE person_id = 9622").fetchone()
    print(f"   {dict(ref) if ref is not None else 'NOT FOUND'}")

    print()
    print("=" * 72)
    print("EP8 DEPENDENCY CHECK")
    print("=" * 72)
    dep = SPEC["dependency"]["pair"]
    rows = cur.execute(
        "SELECT * FROM relationships WHERE "
        "(person_a_id = ? AND person_b_id = ?) OR "
        "(person_a_id = ? AND person_b_id = ?) ORDER BY id",
        (dep[0], dep[1], dep[1], dep[0])).fetchall()
    for r in rows:
        print(f"   {dict(r)}")
    print(f"EP8 DEPENDENCY: rows between 8192 and 3591: "
          f"{len(rows)}")
    print("This package runs only when that number is 0.")

    print()
    print("=" * 72)
    print("RELATIONSHIP ROWS THIS PACKAGE WILL DELETE")
    print("=" * 72)
    ignored_types = set(SPEC["ignored_relationship_types"])
    for rem in SPEC["relationship_removals"]:
        other = rem["other_id"]
        print(f"\n-- pair {TARGET} / {other} ({rem['other_name']}, "
              f"{rem['key']})")
        for r in cur.execute(
                "SELECT * FROM relationships WHERE "
                "(person_a_id = ? AND person_b_id = ?) OR "
                "(person_a_id = ? AND person_b_id = ?) ORDER BY id",
                (TARGET, other, other, TARGET)):
            d = dict(r)
            if d["relationship_type"] in ignored_types:
                print(f"   LEFT IN PLACE rel id {d['id']}: "
                      f"{d['person_a_id']} -> {d['person_b_id']} "
                      f"{d['relationship_type']} (ignored type)")
            elif d["relationship_type"] in rem["allowed_types"]:
                print(f"   WILL DELETE rel id {d['id']}: "
                      f"{d['person_a_id']} -> {d['person_b_id']} "
                      f"{d['relationship_type']} "
                      f"certainty={d['certainty']!r} "
                      f"evidence={d['evidence_text']!r}")
            else:
                print(f"   UNEXPECTED rel id {d['id']}: "
                      f"{d['person_a_id']} -> {d['person_b_id']} "
                      f"{d['relationship_type']} (the apply run "
                      f"aborts on this row)")
    print()
    print("Fill the WILL DELETE ids for each pair into that "
          "removal's \"expected_ids\" in "
          "john_clark_3591_untangle_package.json before the live "
          "apply run (see SPEC.md).")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
