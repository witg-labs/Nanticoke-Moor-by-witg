#!/usr/bin/env python3
"""
Mark the 56 provably wrong burial facts as GEDCOM import artifacts.

Ruling (Jequan Davis, 2026-11-16): of the 79 burial facts carrying the
import-artifact signature, the 56 dated before the person's birth or death
get class-level import-artifact marking. The 9 held for individual review
and the 14 repetition-only facts are NOT in this package and are untouched.

Data: burial_marks.json beside this script (fact_id, person, claimed date,
reasons).

Marking strategy (schema discovered, never assumed):
- If the facts table has a notes-like text column (notes, note,
  evidence_text, comments), the marker sentence is appended to it.
- Otherwise a sidecar table fact_quality_flags is created (it does not
  alter any source table) and one row per fact is inserted.
Marker text: "[Import artifact: this burial date was propagated by the
GEDCOM import and is not a recorded burial date. Flagged 2026-11-16.]"

Safety: timestamped backup first; one transaction; idempotent (a fact
already carrying the marker is skipped); every fact is verified to exist
and to be a Burial fact before any write; rollback on any surprise.

Usage: python3 apply_burial_artifact_marks.py [path-to-genealogy_preservation.db]
"""
import json, os, shutil, sqlite3, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "burial_marks.json")))
FACTS = DATA["facts"]
MARKER = ("[Import artifact: this burial date was propagated by the GEDCOM "
          "import and is not a recorded burial date. Flagged 2026-11-16.]")

def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
        "~/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/"
        "preservation_output/genealogy_preservation.db")
    if not os.path.exists(db_path):
        sys.exit(f"DB not found: {db_path}")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{db_path}.backup-{stamp}"
    shutil.copy2(db_path, backup)
    print(f"Backup: {backup}")

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    ft = next((t for t in tables if t.lower() in ("facts", "person_facts", "fact")), None)
    if ft is None:
        con.close(); sys.exit("STOP: no facts table found; nothing changed.")
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({ft})")]
    id_col = cols[0]
    type_col = next((c for c in cols if "type" in c.lower()), None)
    note_col = next((c for c in cols
                     if c.lower() in ("notes", "note", "evidence_text",
                                      "comments", "comment")), None)

    # Verify all 56 facts exist and are Burial facts before writing.
    for f in FACTS:
        row = cur.execute(f"SELECT {id_col}" +
                          (f", {type_col}" if type_col else "") +
                          f" FROM {ft} WHERE {id_col} = ?", (f["fact_id"],)).fetchone()
        if row is None:
            con.close(); sys.exit(f"STOP: fact {f['fact_id']} not in DB; nothing changed.")
        if type_col and str(row[1]).lower() != "burial":
            con.close(); sys.exit(
                f"STOP: fact {f['fact_id']} is type {row[1]}, not Burial; nothing changed.")

    marked = skipped = 0
    try:
        cur.execute("BEGIN")
        if note_col:
            for f in FACTS:
                cur_note = cur.execute(
                    f"SELECT {note_col} FROM {ft} WHERE {id_col} = ?",
                    (f["fact_id"],)).fetchone()[0] or ""
                if "Import artifact" in cur_note:
                    skipped += 1; continue
                new = (cur_note.rstrip() + " " + MARKER).strip()
                cur.execute(f"UPDATE {ft} SET {note_col} = ? WHERE {id_col} = ?",
                            (new, f["fact_id"]))
                if cur.rowcount != 1:
                    raise RuntimeError(f"fact {f['fact_id']}: update rowcount {cur.rowcount}")
                marked += 1
            print(f"Strategy: appended marker to {ft}.{note_col}.")
        else:
            cur.execute("""CREATE TABLE IF NOT EXISTS fact_quality_flags (
                fact_id INTEGER PRIMARY KEY, flag TEXT, note TEXT, applied_at TEXT)""")
            for f in FACTS:
                cur.execute(
                    "INSERT OR IGNORE INTO fact_quality_flags VALUES (?, 'import_artifact', ?, ?)",
                    (f["fact_id"], MARKER, datetime.date.today().isoformat()))
                if cur.rowcount == 1:
                    marked += 1
                else:
                    skipped += 1
            print("Strategy: sidecar table fact_quality_flags (no source table altered).")
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        sys.exit(f"ROLLED BACK, nothing changed: {e}")
    print(f"Marked {marked}, already marked {skipped}, total {len(FACTS)}.")
    con.close()

if __name__ == "__main__":
    main()
