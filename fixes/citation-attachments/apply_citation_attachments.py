#!/usr/bin/env python3
"""
Attach primary-record citations to the 43 internally corroborated facts.

Data: attachments.json beside this script: 69 (fact_id, citation_id) pairs.
Each pair says: this primary-record citation, already attached to a same-type
fact on the same profile, also supports this GEDCOM-only fact (internal
cross-reference verdicts, 2026-11-14: 43 CORROBORATED).

Schema handling (the DB schema is discovered, never assumed):
- If a link table exists (a table holding both a fact reference and a
  citation reference, e.g. fact_citations), pairs are inserted there.
- Else if the citations table itself carries a fact reference column,
  attaching means inserting a copy of the supporting citation row pointed
  at the target fact (same source, same evidence text).
- Else the script prints the schema of every table mentioning 'citation'
  or 'fact' and stops without changing anything.

Safety: timestamped backup first; one transaction; idempotent (pairs
already attached are skipped); every target fact and source citation is
verified to exist before any write; rollback on any surprise.

Usage: python3 apply_citation_attachments.py [path-to-genealogy_preservation.db]
"""
import json, os, shutil, sqlite3, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "attachments.json")))
PAIRS = DATA["pairs"]

def find_link_model(cur):
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    def cols(t):
        return [r[1] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()]
    # Model A: dedicated link table with fact + citation columns
    for t in tables:
        cs = [c.lower() for c in cols(t)]
        if any("fact" in c for c in cs) and any("citation" in c for c in cs) \
           and t.lower() not in ("facts", "citations"):
            fc = next(c for c in cols(t) if "fact" in c.lower())
            cc = next(c for c in cols(t) if "citation" in c.lower())
            return ("link", t, fc, cc)
    # Model B: citations table carries the fact reference
    for t in tables:
        if "citation" in t.lower():
            cs = cols(t)
            low = [c.lower() for c in cs]
            if any("fact" in c for c in low):
                fc = next(c for c in cs if "fact" in c.lower())
                idc = next((c for c in cs if c.lower() in ("citation_id", "id")), cs[0])
                return ("copy", t, fc, idc)
    return (None, None, None, None)

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
    model, table, fact_col, cit_col = find_link_model(cur)
    if model is None:
        for (t,) in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            if "citation" in t.lower() or "fact" in t.lower():
                print(t, [r[1] for r in cur.execute(f"PRAGMA table_info({t})")])
        con.close()
        sys.exit("STOP: no recognizable fact-citation link model. "
                 "Schema printed above; nothing was changed.")

    # Verify every target fact and source citation exists up front.
    fact_ids = {p["fact_id"] for p in PAIRS}
    cit_ids = {p["citation_id"] for p in PAIRS}
    ft = next((r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if r[0].lower() in ("facts", "person_facts", "fact")), None)
    if ft is None:
        con.close(); sys.exit("STOP: no facts table found; nothing changed.")
    fid_col = [r[1] for r in cur.execute(f"PRAGMA table_info({ft})")][0]
    have_facts = {r[0] for r in cur.execute(
        f"SELECT {fid_col} FROM {ft}").fetchall()}
    missing = fact_ids - have_facts
    if missing:
        con.close(); sys.exit(f"STOP: target facts missing from DB: {sorted(missing)}")

    inserted = skipped = 0
    try:
        cur.execute("BEGIN")
        if model == "link":
            have = {(r[0], r[1]) for r in cur.execute(
                f"SELECT {fact_col}, {cit_col} FROM {table}").fetchall()}
            have_cits = {r[1] for r in have}
            gone = cit_ids - have_cits
            if gone:
                raise RuntimeError(f"source citations not in link table: {sorted(gone)}")
            for p in PAIRS:
                key = (p["fact_id"], p["citation_id"])
                if key in have:
                    skipped += 1; continue
                cur.execute(f"INSERT INTO {table} ({fact_col}, {cit_col}) VALUES (?, ?)", key)
                inserted += 1
        else:  # copy model
            cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]
            rows = {}
            for cid in cit_ids:
                r = cur.execute(f"SELECT * FROM {table} WHERE {cit_col} = ?", (cid,)).fetchone()
                if r is None:
                    raise RuntimeError(f"source citation {cid} not found")
                rows[cid] = dict(zip(cols, r))
            existing = {(r[0], r[1]) for r in cur.execute(
                f"SELECT {fact_col}, source_id FROM {table}").fetchall()} \
                if "source_id" in cols else set()
            for p in PAIRS:
                if (p["fact_id"], p["source_id"]) in existing:
                    skipped += 1; continue
                src = dict(rows[p["citation_id"]])
                src[fact_col] = p["fact_id"]
                src.pop(cit_col, None)  # let the DB assign a new citation id
                use = [c for c in cols if c != cit_col]
                cur.execute(
                    f"INSERT INTO {table} ({', '.join(use)}) VALUES ({', '.join('?' * len(use))})",
                    [src[c] for c in use])
                inserted += 1
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        sys.exit(f"ROLLED BACK, nothing changed: {e}")
    print(f"Model: {model} on table {table}. Inserted {inserted}, "
          f"already present {skipped}, pairs total {len(PAIRS)}.")
    con.close()

if __name__ == "__main__":
    main()
