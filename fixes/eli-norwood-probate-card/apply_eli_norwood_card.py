#!/usr/bin/env python3
"""Attach the Eli Norwood probate index card (Sussex County, 1838) to his
archive profile (person 10457) as a cited document.

Does three things, in one transaction, after a timestamped backup:
  1. Find-or-create the Delaware Public Archives source row for the card.
  2. Cite that source on Eli Norwood's Death fact (9800), with the card's
     contents and the Elon Norwood / Whittington Clark cross-reference as
     the evidence text. Skipped if already cited from that source.
  3. Register the card image as a photo/document row (mirroring the shape
     of an existing no-face documents row) and link it to person 10457 via
     the photo-person link mechanism. Skipped if the image path is already
     registered.

The image file itself is NOT handled here: place
norwood_eli_probate_card_1838.png (from Drive, Genealogy Records, file
"Norwood, Eli - Probate Index Card 1838, Sussex County DE.png") into the
repo at frontend/public/assets/archive_media/documents/ before re-export.

Schema is discovered, never assumed. On any surprise the script rolls back
and prints the schema it found. Idempotent.

Usage: python3 apply_eli_norwood_card.py [path-to-genealogy_preservation.db]
"""
import json, os, shutil, sqlite3, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "eli_norwood_card.json")))
DEFAULT_DB = os.path.expanduser(
    "~/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/"
    "preservation_output/genealogy_preservation.db")


def cols(cur, table):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]


def tables(cur):
    return [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")]


def pick_col(names, *cands):
    low = {n.lower(): n for n in names}
    for c in cands:
        if c.lower() in low:
            return low[c.lower()]
    return None


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    if not os.path.exists(db_path):
        print("Database not found:", db_path); sys.exit(2)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{db_path}.backup-{stamp}"
    shutil.copy2(db_path, backup)
    print("Backup written:", backup)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    try:
        ts = tables(cur)
        persons_t = next((t for t in ("persons", "people", "person")
                          if t in ts), None)
        facts_t = next((t for t in ("facts", "person_facts") if t in ts), None)
        cites_t = next((t for t in ("citations", "fact_citations")
                        if t in ts), None)
        sources_t = next((t for t in ("sources",) if t in ts), None)
        photos_t = next((t for t in ("photos", "photo", "media")
                         if t in ts), None)
        if not all([persons_t, facts_t, cites_t, sources_t, photos_t]):
            print("SCHEMA SURPRISE: tables =", ts); con.rollback(); sys.exit(3)

        # --- verify the person and the death fact ---
        pc = cols(cur, persons_t)
        pid_c = pick_col(pc, "person_id", "id")
        name_c = pick_col(pc, "name", "full_name")
        row = cur.execute(
            f"SELECT {name_c} FROM {persons_t} WHERE {pid_c}=?",
            (DATA["person_id"],)).fetchone()
        if not row or DATA["person_name_expected"].lower() not in row[0].lower():
            print("SCHEMA SURPRISE: person check failed:", row)
            con.rollback(); sys.exit(3)
        fc = cols(cur, facts_t)
        fid_c = pick_col(fc, "fact_id", "id")
        ftype_c = pick_col(fc, "fact_type", "type")
        frow = cur.execute(
            f"SELECT {ftype_c} FROM {facts_t} WHERE {fid_c}=?",
            (DATA["death_fact_id"],)).fetchone()
        if not frow or frow[0] != "Death":
            print("SCHEMA SURPRISE: death fact check failed:", frow)
            con.rollback(); sys.exit(3)

        # --- source row (find or create) ---
        sc = cols(cur, sources_t)
        sid_c = pick_col(sc, "source_id", "id")
        title_c = pick_col(sc, "title", "source_title", "name")
        s = DATA["source"]
        row = cur.execute(
            f"SELECT {sid_c} FROM {sources_t} WHERE {title_c}=?",
            (s["title"],)).fetchone()
        if row:
            source_id = row[0]
            print("Source exists:", source_id)
        else:
            vals, keys = {}, []
            for cand, val in (("title", s["title"]), ("source_title", s["title"]),
                              ("name", s["title"]), ("dataset", s["dataset"]),
                              ("dataset_source", s["dataset"]), ("url", s["url"]),
                              ("source_url", s["url"])):
                col = pick_col(sc, cand)
                if col and col not in vals:
                    vals[col] = val; keys.append(col)
            cur.execute(
                f"INSERT INTO {sources_t} ({','.join(keys)}) "
                f"VALUES ({','.join('?' * len(keys))})",
                [vals[k] for k in keys])
            source_id = cur.lastrowid
            print("Source created:", source_id)

        # --- citation on the Death fact (link model discovered) ---
        cc = cols(cur, cites_t)
        cite_sid = pick_col(cc, "source_id")
        cite_fid = pick_col(cc, "fact_id")
        cite_evi = pick_col(cc, "evidence_text", "evidence", "notes")
        already = False
        if cite_fid:
            already = bool(cur.execute(
                f"SELECT 1 FROM {cites_t} WHERE {cite_fid}=? AND {cite_sid}=?",
                (DATA["death_fact_id"], source_id)).fetchone())
        if already:
            print("Citation already present; skipped.")
        elif cite_fid:
            keys = [cite_fid, cite_sid] + ([cite_evi] if cite_evi else [])
            vals = [DATA["death_fact_id"], source_id] + \
                   ([DATA["citation_evidence"]] if cite_evi else [])
            cur.execute(
                f"INSERT INTO {cites_t} ({','.join(keys)}) "
                f"VALUES ({','.join('?' * len(keys))})", vals)
            print("Citation added to Death fact", DATA["death_fact_id"])
        else:
            link_t = next((t for t in ts if "citation" in t and
                           ("link" in t or "fact" in t) and t != cites_t), None)
            if not link_t:
                print("SCHEMA SURPRISE: no citation link model. citations"
                      " cols:", cc, "tables:", ts)
                con.rollback(); sys.exit(3)
            lc = cols(cur, link_t)
            lf = pick_col(lc, "fact_id"); ls = pick_col(lc, "citation_id",
                                                      "source_id")
            cur.execute(
                f"INSERT INTO {link_t} ({lf},{ls}) VALUES (?,?)",
                (DATA["death_fact_id"], source_id))
            print("Citation linked via", link_t)

        # --- photo/document row + person link ---
        phc = cols(cur, photos_t)
        path_c = pick_col(phc, "local_image_path", "image_path", "file_path",
                          "path")
        prow = cur.execute(
            f"SELECT 1 FROM {photos_t} WHERE {path_c}=?",
            (DATA["photo"]["local_image_path"],)).fetchone()
        if prow:
            print("Photo row already registered; skipped.")
            photo_id = cur.execute(
                f"SELECT {pick_col(phc, 'photo_id', 'id')} FROM {photos_t} "
                f"WHERE {path_c}=?",
                (DATA["photo"]["local_image_path"],)).fetchone()[0]
        else:
            # mirror the free-text conventions of an existing no-face
            # documents row
            tmpl = cur.execute(
                f"SELECT * FROM {photos_t} WHERE "
                f"{pick_col(phc, 'document_type')}='historical_document' "
                f"LIMIT 1").fetchone()
            tmpl_d = dict(zip(phc, tmpl)) if tmpl else {}
            vals = {}
            for k, v in DATA["photo"].items():
                col = pick_col(phc, k)
                if col:
                    vals[col] = v
            for carry in ("face_context", "confidence_score", "subtype",
                          "routing_target"):
                col = pick_col(phc, carry)
                if col and col not in vals and col in tmpl_d:
                    vals[col] = tmpl_d[col]
            keys = list(vals)
            cur.execute(
                f"INSERT INTO {photos_t} ({','.join(keys)}) "
                f"VALUES ({','.join('?' * len(keys))})",
                [vals[k] for k in keys])
            photo_id = cur.lastrowid
            print("Photo row created:", photo_id)
        # link photo -> person
        link_t = next((t for t in ts if "photo" in t and
                       ("person" in t or "subject" in t or "link" in t)
                       and t != photos_t), None)
        direct = pick_col(phc, "person_id")
        if link_t:
            lc = cols(cur, link_t)
            lph = pick_col(lc, "photo_id", "photo")
            lpe = pick_col(lc, "person_id", "person")
            if not cur.execute(
                    f"SELECT 1 FROM {link_t} WHERE {lph}=? AND {lpe}=?",
                    (photo_id, DATA["person_id"])).fetchone():
                cur.execute(
                    f"INSERT INTO {link_t} ({lph},{lpe}) VALUES (?,?)",
                    (photo_id, DATA["person_id"]))
            print("Photo linked to person via", link_t)
        elif direct:
            cur.execute(
                f"UPDATE {photos_t} SET {direct}=? WHERE "
                f"{pick_col(phc, 'photo_id', 'id')}=?",
                (DATA["person_id"], photo_id))
            print("Photo linked via photos.person_id")
        else:
            print("SCHEMA SURPRISE: no photo-person link model. photos"
                  " cols:", phc, "tables:", ts)
            con.rollback(); sys.exit(3)
        con.commit()
        print("COMMITTED.")
    except SystemExit:
        raise
    except Exception as e:
        con.rollback()
        print("ERROR, rolled back:", e); sys.exit(4)


if __name__ == "__main__":
    main()
