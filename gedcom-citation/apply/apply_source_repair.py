#!/usr/bin/env python3
"""Repair the two GEDCOM source records in genealogy_preservation.db.

Changes ONLY the title column of sources 622 and 625 (Jequan's rulings,
2026-11-14). The url column doubles as a filename key for pipeline
scripts and is deliberately left unchanged. Backs up the database,
applies in one transaction, asserts exactly one row per update.

Usage: python3 apply_source_repair.py /path/to/genealogy_preservation.db [--dry-run]
"""
import shutil, sqlite3, sys, datetime

UPDATES = [
    (622, "Record: Davis Family Tree.ged",
     "Davis Family Tree (GEDCOM), compiled by Jequan Davis, 2026"),
    (625, "Record: GEDCOM Import",
     "Davis Family Tree (GEDCOM), supplemental import, compiled by Jequan Davis, 2026"),
]

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: apply_source_repair.py <db_path> [--dry-run]")
    db_path, dry = sys.argv[1], "--dry-run" in sys.argv
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "sources" not in tables:
        sys.exit("STOP: sources table not found. Nothing applied.")
    for sid, expected_old, new_title in UPDATES:
        row = cur.execute("SELECT title FROM sources WHERE source_id=?", (sid,)).fetchone()
        if row is None:
            sys.exit(f"STOP: source {sid} not found. Nothing applied.")
        print(f"source {sid}: {row[0]!r} -> {new_title!r}")
        if row[0] != expected_old:
            sys.exit(f"STOP: source {sid} title is {row[0]!r}, expected {expected_old!r}. Nothing applied.")
    if dry:
        print("DRY RUN: both titles match expectations. Nothing committed.")
        return
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = db_path + f".backup-{stamp}"
    shutil.copy2(db_path, backup)
    print(f"backup written: {backup}")
    try:
        for sid, _old, new_title in UPDATES:
            cur.execute("UPDATE sources SET title=? WHERE source_id=?", (new_title, sid))
            assert cur.rowcount == 1, f"source {sid} rowcount {cur.rowcount}"
        con.commit()
        print("COMMITTED.")
    except Exception:
        con.rollback()
        raise
    for sid, _o, _n in UPDATES:
        print(f"source {sid} now:", cur.execute("SELECT title FROM sources WHERE source_id=?", (sid,)).fetchone()[0])
    con.close()

if __name__ == "__main__":
    main()
