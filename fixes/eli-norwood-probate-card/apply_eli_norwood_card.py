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

Correction 2026-11-26 (Orbit), from a pre-run audit against the live
exporter source and photos.json (the Package 4 lesson: audit before the
first run, not after the first stop):
  1. The photo catalog table is unified_photo_catalog (the exporter's
     photos.json source); the original candidate list ("photos",
     "photo", "media") matches no table in this database and would
     have stopped the run. It is now the first candidate.
  2. The Death-fact check now also verifies the fact belongs to
     person 10457 (the original checked only the fact's type).
  3. The template-row copy for the catalog row's remaining fields is
     removed: it selected with LIMIT 1 and no ordering, so the values
     were a lottery. eli_norwood_card.json now carries the full row
     spec with the archive's document-row conventions.
  4. A title row is also registered in photo_catalog (the exporter's
     title_or_caption source), so the card keeps its caption in
     photos.json instead of falling back to the subject name.
  5. The person link prefers the person_photos table by exact name
     and records is_primary/confidence for the link row.
No change to the package's scope: source, citation, document row,
person link; no spouse relationship for Elon Norwood.

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
        photos_t = next((t for t in ("unified_photo_catalog", "photos",
                                     "photo", "media")
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
        fperson_c = pick_col(fc, "person_id", "person")
        frow = cur.execute(
            f"SELECT {ftype_c}, {fperson_c} FROM {facts_t} WHERE {fid_c}=?",
            (DATA["death_fact_id"],)).fetchone()
        if not frow or frow[0] != "Death" or frow[1] != DATA["person_id"]:
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
        id_c = pick_col(phc, "photo_id", "id")
        # full row spec: every DATA["photo"] key that names a real column
        vals = {}
        for k, v in DATA["photo"].items():
            col = pick_col(phc, k)
            if col:
                vals[col] = v
        prow = cur.execute(
            f"SELECT {id_c} FROM {photos_t} WHERE {path_c}=?",
            (DATA["photo"]["local_image_path"],)).fetchone()
        if prow:
            photo_id = prow[0]
            print("Photo row already registered; skipped:", photo_id)
        else:
            keys = list(vals)
            cur.execute(
                f"INSERT INTO {photos_t} ({','.join(keys)}) "
                f"VALUES ({','.join('?' * len(keys))})",
                [vals[k] for k in keys])
            photo_id = cur.lastrowid
            print("Photo row created:", photo_id)
        # title row in photo_catalog: the exporter's title_or_caption
        # source for photos.json. Without it the caption falls back to
        # the subject name.
        pc_t = "photo_catalog" if "photo_catalog" in ts else None
        if pc_t:
            pcc = cols(cur, pc_t)
            pc_pid = pick_col(pcc, "photo_id")
            pc_title = pick_col(pcc, "title_or_caption")
            if pc_pid and pc_title:
                if cur.execute(
                        f"SELECT 1 FROM {pc_t} WHERE {pc_pid}=?",
                        (photo_id,)).fetchone():
                    print("Photo title row already in photo_catalog;"
                          " skipped.")
                else:
                    keys = [pc_pid]
                    pvals = [photo_id]
                    for col, v in vals.items():
                        c2 = pick_col(pcc, col)
                        if c2 and c2 not in keys:
                            keys.append(c2); pvals.append(v)
                    if pc_title not in keys:
                        keys.append(pc_title)
                        pvals.append(DATA["photo"]["title_or_caption"])
                    cur.execute(
                        f"INSERT INTO {pc_t} ({','.join(keys)}) "
                        f"VALUES ({','.join('?' * len(keys))})", pvals)
                    print("Photo title row created in photo_catalog:",
                          photo_id)
        # link photo -> person (person_photos preferred by exact name)
        if "person_photos" in ts:
            link_t = "person_photos"
        else:
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
                keys = [lph, lpe]
                lvals = [photo_id, DATA["person_id"]]
                lip = pick_col(lc, "is_primary")
                if lip:
                    keys.append(lip); lvals.append(1)
                lcs = pick_col(lc, "confidence_score")
                if lcs:
                    keys.append(lcs); lvals.append(1.0)
                cur.execute(
                    f"INSERT INTO {link_t} ({','.join(keys)}) "
                    f"VALUES ({','.join('?' * len(keys))})", lvals)
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
