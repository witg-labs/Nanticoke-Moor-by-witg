#!/usr/bin/env python3
"""Apply the Phase 4 photo metadata corrections to genealogy_preservation.db.

Reads corrections_final.json (same directory). Updates ONLY document_type,
contains_face, and face_context on unified_photo_catalog, in one
transaction, after writing a timestamped backup copy of the database.
Retire-from-export and held items are reported, never applied here.

Usage: python3 apply_photo_corrections.py /path/to/genealogy_preservation.db [--dry-run]
"""
import json, os, shutil, sqlite3, sys, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: apply_photo_corrections.py <db_path> [--dry-run]")
    db_path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    pkg = json.load(open(os.path.join(HERE, "corrections_final.json")))
    updates = pkg["updates"]

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "unified_photo_catalog" not in tables:
        sys.exit("STOP: unified_photo_catalog not found in this database. Schema differs from the export code. Nothing applied.")
    cols = {r[1] for r in cur.execute("PRAGMA table_info(unified_photo_catalog)")}
    need = {"photo_id", "document_type", "contains_face", "face_context", "flag_for_human_review"}
    if not need.issubset(cols):
        sys.exit(f"STOP: missing columns {need - cols}. Nothing applied.")

    before_types = collections.Counter(r[0] for r in cur.execute("SELECT document_type FROM unified_photo_catalog"))
    before_faces = cur.execute("SELECT COUNT(*) FROM unified_photo_catalog WHERE contains_face").fetchone()[0]
    print(f"records in table: {sum(before_types.values())}, contains_face total: {before_faces}")
    print(f"updates to apply: {len(updates)}")

    if not dry:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = db_path + f".backup-{stamp}"
        shutil.copy2(db_path, backup)
        print(f"backup written: {backup}")

    failures = []
    try:
        for it in updates:
            cur.execute(
                "UPDATE unified_photo_catalog SET document_type=?, contains_face=?, face_context=? WHERE photo_id=?",
                (it["to_type"], it["contains_face"], it["face_context"], it["photo_id"]),
            )
            if cur.rowcount != 1:
                failures.append((it["photo_id"], f"rowcount {cur.rowcount}"))
            if it.get("keep_review_flag"):
                cur.execute("UPDATE unified_photo_catalog SET flag_for_human_review=1 WHERE photo_id=?", (it["photo_id"],))
        if failures:
            con.rollback()
            print("ROLLBACK. Failed photo_ids:", failures)
            sys.exit(2)
        if dry:
            con.rollback()
            print("DRY RUN: all updates matched exactly one row. Nothing committed.")
        else:
            con.commit()
            print("COMMITTED.")
    finally:
        after_types = collections.Counter(r[0] for r in cur.execute("SELECT document_type FROM unified_photo_catalog"))
        after_faces = cur.execute("SELECT COUNT(*) FROM unified_photo_catalog WHERE contains_face").fetchone()[0]
        con.close()
    print(f"contains_face total now: {after_faces} (package expects {pkg['expected']['contains_face_total_after']} after a real run)")
    print("type counts now (changed types only):")
    for t, exp in pkg["expected"]["type_deltas"].items():
        print(f"  {t}: {after_types.get(t, 0)} (package expects {exp['after']})")
    print("HELD (no changes applied):", pkg["held"])
    print("RETIRE FROM EXPORT (not applied by this script; see handoff step 5):",
          [r["photo_id"] for r in pkg["retire_from_export"]])

if __name__ == "__main__":
    main()
