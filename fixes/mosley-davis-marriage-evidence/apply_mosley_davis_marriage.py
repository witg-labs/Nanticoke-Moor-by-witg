#!/usr/bin/env python3
"""Mosley-Davis marriage evidence package (built 2026-11-26).

Applies the 2026-11-26 FamilySearch evidence find to the archive:

  1. Find-or-create two FamilySearch sources: the 1947 Delaware
     Certificate of Marriage of Hersel Davis and Myrtle Mosley
     (File No. 4339) and the 1952 Delaware marriage record of
     Maurice Allen Mosley (File No. 2382).
  2. Cite the 1947 certificate on Hersel Davis's existing Marriage
     fact (24331), filling its date, place, and value (it is a stub:
     no date, source 1270 only). Create the matching Marriage fact
     on Myrtle Mosley's profile (8223), cited the same way. The
     spouse relationship already exists; it is not touched.
  3. Create a profile for Maggie Mosley, Myrtle's mother, named here
     for the first time by a primary record (the 1947 certificate).
     She is the wife in Harry Mosley's census household (Maggie in
     1920 and 1940, Margaret M. in 1930). The package gives her a
     Name fact cited to the certificate, a Birth fact (abt 1883)
     cited to the three census sources, a spouse link to Harry
     Mosley (9239), and Myrtle's mother link. Nothing else about
     her is asserted.
  4. Correct Maurice Allen Mosley's father link: delete the
     child link to Frank Lear Wilson (9238) and link him to
     Hersel Davis (8158), as named on Maurice's own 1952 marriage
     record. Cite that record on Maurice's Marriage fact (24752)
     and fill its date, place, and value. The Myrtle-Frank spouse
     link is NOT touched; it is a separate question.
  5. Apply Jequan Davis's birth-year ruling for Hersel Davis
     (ruled 2026-11-27, folded into this package by amendment the
     same day; the package originally only flagged the conflict).
     The ruling: Hersel's birth is June 3, 1913, per his 1947
     Delaware marriage certificate (File No. 4339), which states
     his birth as June 3, 1913 (read by Orbit from the enlarged
     certificate image; an earlier search-pass transcription read
     the day as June 8, which the image does not support) and his
     age as 34, which agree with each other. The funeral
     program's June 3, 1915 is superseded and stays visible as
     superseded. The package sets persons.birth_info from
     "3 Jun 1915" to "3 Jun 1913" (any other current value stops
     the run), adds a Birth fact for the man himself cited to the
     certificate, and appends the ruling to his notes. His
     duplicated infant Birth/Death facts (1921/1922) are a
     separate conflation item and are NOT touched, and no death
     field changes.
  6. Register both certificate images as document rows in
     unified_photo_catalog (plus photo_catalog title rows) and
     link them: the 1947 certificate to both spouses' profiles,
     the 1952 record to Maurice's profile. Neither is primary;
     all three profiles already have photographs.
  7. Myrtle's 1936 Bridgeton marriage fact (12363, to Ulysses
     Owens) is NOT touched. It is an open question: the 1947
     certificate records her as Single, first marriage, and no
     1936 record has been found. Deleting it is not authorized.

The image files are NOT handled here: place
davis_hersel_mosley_myrtle_marriage_certificate_1947.jpg and
mosley_maurice_allen_marriage_record_1952.jpg into the repo at
frontend/public/assets/archive_media/documents/ before re-export
(they are committed on this branch).

Schema is discovered, never assumed, in the corrected Package 5
style (exact-name candidate lists, unified_photo_catalog by name,
fact-ownership checks). One transaction, timestamped backup first.
On any surprise the script rolls back and prints what it found.
Idempotent.

Usage: python3 apply_mosley_davis_marriage.py [path-to-genealogy_preservation.db]
"""
import json, os, shutil, sqlite3, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "mosley_davis_marriage.json")))
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


def surprise(msg, *extra):
    print("SCHEMA SURPRISE:", msg, *extra)
    raise SystemExit(3)


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
        rels_t = next((t for t in ("relationships",) if t in ts), None)
        flags_t = "fact_quality_flags" if "fact_quality_flags" in ts else None
        if not all([persons_t, facts_t, cites_t, sources_t, photos_t,
                    rels_t]):
            surprise("tables =", ts)
        pc = cols(cur, persons_t)
        pid_c = pick_col(pc, "person_id", "id")
        name_c = pick_col(pc, "name", "full_name")
        notes_c = pick_col(pc, "notes")

        def person_name(pid):
            row = cur.execute(
                f"SELECT {name_c} FROM {persons_t} WHERE {pid_c}=?",
                (pid,)).fetchone()
            return row[0] if row else None

        # --- verify the people this package touches ---
        for pid, frag in DATA["expected_persons"].items():
            nm = person_name(int(pid))
            if not nm or frag.lower() not in nm.lower():
                surprise("person check failed:", pid, nm)
        print("Persons verified:", ", ".join(
            f"{pid} {person_name(int(pid))}"
            for pid in DATA["expected_persons"]))

        # --- verify the stub facts (exist, right owner, right type) ---
        fc = cols(cur, facts_t)
        fid_c = pick_col(fc, "fact_id", "id")
        fpid_c = pick_col(fc, "person_id", "person")
        ftype_c = pick_col(fc, "fact_type", "type")
        fdate_c = pick_col(fc, "date_string", "date")
        fplace_c = pick_col(fc, "place_string", "place")
        fval_c = pick_col(fc, "value_string", "value")

        def fact_row(fid):
            return cur.execute(
                f"SELECT {fpid_c}, {ftype_c}, {fdate_c} FROM {facts_t} "
                f"WHERE {fid_c}=?", (fid,)).fetchone()

        for key in ("hersel_marriage_fact", "maurice_marriage_fact"):
            spec = DATA[key]
            row = fact_row(spec["fact_id"])
            if not row or row[0] != spec["person_id"] or \
                    row[1] != "Marriage":
                surprise(f"{key} check failed:", spec["fact_id"], row)
        print("Stub marriage facts verified.")

        # --- sources (find or create) ---
        sc = cols(cur, sources_t)
        sid_c = pick_col(sc, "source_id", "id")
        title_c = pick_col(sc, "title", "source_title", "name")

        def find_or_create_source(s):
            row = cur.execute(
                f"SELECT {sid_c} FROM {sources_t} WHERE {title_c}=?",
                (s["title"],)).fetchone()
            if row:
                print("Source exists:", row[0], "-", s["title"][:60])
                return row[0]
            vals = {}
            for cand, val in (("title", s["title"]),
                              ("dataset", s["dataset"]),
                              ("url", s["url"])):
                col = pick_col(sc, cand)
                if col and col not in vals:
                    vals[col] = val
            keys = list(vals)
            cur.execute(
                f"INSERT INTO {sources_t} ({','.join(keys)}) "
                f"VALUES ({','.join('?' * len(keys))})",
                [vals[k] for k in keys])
            print("Source created:", cur.lastrowid, "-", s["title"][:60])
            return cur.lastrowid

        s1 = find_or_create_source(DATA["source_1947"])
        s2 = find_or_create_source(DATA["source_1952"])

        # --- citation helper (direct model, discovered) ---
        cc = cols(cur, cites_t)
        cite_fid = pick_col(cc, "fact_id")
        cite_sid = pick_col(cc, "source_id")
        cite_evi = pick_col(cc, "evidence_text", "evidence", "notes")
        if not cite_fid or not cite_sid:
            surprise("citations model not direct:", cc)

        def cite(fid, sid, evidence):
            if cur.execute(
                    f"SELECT 1 FROM {cites_t} WHERE {cite_fid}=? AND "
                    f"{cite_sid}=?", (fid, sid)).fetchone():
                print(f"Citation already present on fact {fid}; skipped.")
                return
            keys = [cite_fid, cite_sid] + ([cite_evi] if cite_evi else [])
            vals = [fid, sid] + ([evidence] if cite_evi else [])
            cur.execute(
                f"INSERT INTO {cites_t} ({','.join(keys)}) "
                f"VALUES ({','.join('?' * len(keys))})", vals)
            print(f"Citation added to fact {fid} from source {sid}.")

        def fill_stub_fact(spec, sid, evidence):
            fid = spec["fact_id"]
            row = fact_row(fid)
            if row[2]:
                print(f"Fact {fid} already has a date ({row[2]}); "
                      "fields left as they are.")
            else:
                cur.execute(
                    f"UPDATE {facts_t} SET {fdate_c}=?, {fplace_c}=?, "
                    f"{fval_c}=? WHERE {fid_c}=?",
                    (spec["date_string"], spec["place_string"],
                     spec["value_string"], fid))
                print(f"Fact {fid} filled: {spec['date_string']}, "
                      f"{spec['place_string']}.")
            cite(fid, sid, evidence)

        # --- 1947 marriage: Hersel's stub fact + citation ---
        fill_stub_fact(DATA["hersel_marriage_fact"], s1,
                       DATA["hersel_marriage_fact"]["evidence"])

        # --- 1947 marriage: create Myrtle's marriage fact ---
        m = DATA["myrtle_marriage_fact"]
        existing = cur.execute(
            f"SELECT {fid_c} FROM {facts_t} WHERE {fpid_c}=? AND "
            f"{ftype_c}='Marriage' AND {fdate_c}=?",
            (m["person_id"], m["date_string"])).fetchone()
        if existing:
            myrtle_fact_id = existing[0]
            print("Myrtle marriage fact already exists:", myrtle_fact_id)
        else:
            cur.execute(
                f"INSERT INTO {facts_t} ({fpid_c}, {ftype_c}, {fdate_c}, "
                f"{fplace_c}, {fval_c}) VALUES (?,?,?,?,?)",
                (m["person_id"], "Marriage", m["date_string"],
                 m["place_string"], m["value_string"]))
            myrtle_fact_id = cur.lastrowid
            print("Myrtle marriage fact created:", myrtle_fact_id)
        cite(myrtle_fact_id, s1, m["evidence"])

        # --- Maggie Mosley: find or create ---
        mg = DATA["maggie"]
        row = cur.execute(
            f"SELECT {pid_c}, {notes_c} FROM {persons_t} WHERE {name_c}=?",
            (mg["name"],)).fetchone()
        if row and row[1] and mg["marker"] in row[1]:
            maggie_id = row[0]
            print("Maggie Mosley profile already exists:", maggie_id)
        elif row:
            surprise("a profile named Maggie Mosley exists without "
                     "this package's marker:", row[0])
        else:
            keys = [name_c, notes_c]
            cur.execute(
                f"INSERT INTO {persons_t} ({','.join(keys)}) "
                f"VALUES ({','.join('?' * len(keys))})",
                [mg["name"], mg["notes"]])
            maggie_id = cur.lastrowid
            print("Maggie Mosley profile created:", maggie_id)
            # Name fact, cited to the certificate that names her
            cur.execute(
                f"INSERT INTO {facts_t} ({fpid_c}, {ftype_c}, {fval_c}) "
                f"VALUES (?,?,?)",
                (maggie_id, "Name", mg["name"]))
            cite(cur.lastrowid, s1, mg["name_fact_evidence"])
            # Birth fact from the census ages, one citation per census
            cur.execute(
                f"INSERT INTO {facts_t} ({fpid_c}, {ftype_c}, {fdate_c}, "
                f"{fplace_c}, {fval_c}) VALUES (?,?,?,?,?)",
                (maggie_id, "Birth", mg["birth_date_string"],
                 mg["birth_place_string"], mg["birth_value_string"]))
            birth_fact_id = cur.lastrowid
            for cen in mg["census_citations"]:
                cite(birth_fact_id, cen["source_id"], cen["evidence"])
            print("Maggie facts created: Name + Birth ("
                  f"{mg['birth_date_string']}).")

        # --- relationships helper ---
        rc = cols(cur, rels_t)
        ra_c = pick_col(rc, "person_a_id")
        rb_c = pick_col(rc, "person_b_id")
        rt_c = pick_col(rc, "relationship_type")
        re_c = pick_col(rc, "evidence_text")
        rcert_c = pick_col(rc, "certainty")
        if not all([ra_c, rb_c, rt_c]):
            surprise("relationships columns:", rc)

        def rel_exists(a, b, types):
            ph = ",".join("?" * len(types))
            return bool(cur.execute(
                f"SELECT 1 FROM {rels_t} WHERE {rt_c} IN ({ph}) AND "
                f"(({ra_c}=? AND {rb_c}=?) OR ({ra_c}=? AND {rb_c}=?))",
                (*types, a, b, b, a)).fetchone())

        def add_rel(a, b, rtype, evidence, certainty="confirmed"):
            keys = [ra_c, rb_c, rt_c]
            vals = [a, b, rtype]
            if re_c:
                keys.append(re_c); vals.append(evidence)
            if rcert_c:
                keys.append(rcert_c); vals.append(certainty)
            cur.execute(
                f"INSERT INTO {rels_t} ({','.join(keys)}) "
                f"VALUES ({','.join('?' * len(keys))})", vals)

        # Maggie <-> Harry spouse link
        if rel_exists(maggie_id, mg["spouse_id"],
                      ("spouse", "spouse_of", "spouses")):
            print("Maggie-Harry spouse link already present; skipped.")
        else:
            add_rel(maggie_id, mg["spouse_id"], "spouse",
                    mg["spouse_evidence"])
            print("Maggie-Harry spouse link created.")
        # Myrtle -> Maggie mother link
        if rel_exists(mg["child_id"], maggie_id,
                      ("child_of", "parent_of")):
            print("Myrtle-Maggie parent link already present; skipped.")
        else:
            add_rel(mg["child_id"], maggie_id, "child_of",
                    mg["mother_link_evidence"])
            print("Myrtle-Maggie mother link created.")

        # --- Maurice: father correction ---
        mo = DATA["maurice"]
        cite(mo["marriage_fact_id"], s2, mo["marriage_evidence"])
        fill = DATA["maurice_marriage_fact"]
        row = fact_row(fill["fact_id"])
        if not row[2]:
            cur.execute(
                f"UPDATE {facts_t} SET {fdate_c}=?, {fplace_c}=?, "
                f"{fval_c}=? WHERE {fid_c}=?",
                (fill["date_string"], fill["place_string"],
                 fill["value_string"], fill["fact_id"]))
            print(f"Fact {fill['fact_id']} filled: "
                  f"{fill['date_string']}, {fill['place_string']}.")
        wrong = cur.execute(
            f"SELECT {ra_c}, {rb_c}, {rt_c} FROM {rels_t} WHERE "
            f"{rt_c} IN ('child_of','parent_of') AND "
            f"(({ra_c}=? AND {rb_c}=?) OR ({ra_c}=? AND {rb_c}=?))",
            (mo["person_id"], mo["wrong_father_id"],
             mo["wrong_father_id"], mo["person_id"])).fetchall()
        if rel_exists(mo["person_id"], mo["father_id"],
                      ("child_of", "parent_of")):
            print("Maurice-Hersel father link already present; skipped.")
            if wrong:
                cur.execute(
                    f"DELETE FROM {rels_t} WHERE {rt_c} IN "
                    f"('child_of','parent_of') AND (({ra_c}=? AND "
                    f"{rb_c}=?) OR ({ra_c}=? AND {rb_c}=?))",
                    (mo["person_id"], mo["wrong_father_id"],
                     mo["wrong_father_id"], mo["person_id"]))
                print("Stale Frank Lear Wilson link removed.")
        else:
            if not wrong:
                surprise("Maurice's Frank Lear Wilson father link was "
                         "not found; the correction premise changed. "
                         "Nothing applied.")
            cur.execute(
                f"DELETE FROM {rels_t} WHERE {rt_c} IN "
                f"('child_of','parent_of') AND (({ra_c}=? AND "
                f"{rb_c}=?) OR ({ra_c}=? AND {rb_c}=?))",
                (mo["person_id"], mo["wrong_father_id"],
                 mo["wrong_father_id"], mo["person_id"]))
            print(f"Removed {cur.rowcount} Frank Lear Wilson father "
                  "link row(s) for Maurice.")
            add_rel(mo["person_id"], mo["father_id"], "child_of",
                    mo["father_link_evidence"])
            print("Maurice-Hersel father link created.")

        # --- Hersel birth-year ruling (Jequan Davis, 2026-11-27) ---
        hr = DATA["hersel_birth_ruling"]
        binfo_c = pick_col(pc, "birth_info")
        row = cur.execute(
            f"SELECT {binfo_c} FROM {persons_t} WHERE {pid_c}=?",
            (hr["person_id"],)).fetchone()
        current_binfo = row[0] if row else None
        if current_binfo == hr["new_birth_info"]:
            print("Hersel birth_info already ruled "
                  f"({hr['new_birth_info']}); skipped.")
        elif current_binfo == hr["expected_old_birth_info"]:
            cur.execute(
                f"UPDATE {persons_t} SET {binfo_c}=? WHERE {pid_c}=?",
                (hr["new_birth_info"], hr["person_id"]))
            print(f"Hersel birth_info ruled: {current_binfo} -> "
                  f"{hr['new_birth_info']}.")
        else:
            surprise("Hersel birth_info is neither the expected "
                     "superseded value nor the ruled value:",
                     current_binfo)
        already = cur.execute(
            f"SELECT f.{fid_c} FROM {facts_t} f JOIN {cites_t} c ON "
            f"c.{cite_fid}=f.{fid_c} WHERE f.{fpid_c}=? AND "
            f"f.{ftype_c}='Birth' AND c.{cite_sid}=?",
            (hr["person_id"], s1)).fetchone()
        if already:
            print("Hersel ruled Birth fact already present:",
                  already[0])
        else:
            bf = hr["fact"]
            cur.execute(
                f"INSERT INTO {facts_t} ({fpid_c}, {ftype_c}, "
                f"{fdate_c}, {fplace_c}, {fval_c}) VALUES (?,?,?,?,?)",
                (hr["person_id"], "Birth", bf["date_string"],
                 bf["place_string"], bf["value_string"]))
            birth_fact_id = cur.lastrowid
            cite(birth_fact_id, s1, bf["evidence"])
            print("Hersel ruled Birth fact created:", birth_fact_id)
        row = cur.execute(
            f"SELECT {notes_c} FROM {persons_t} WHERE {pid_c}=?",
            (hr["person_id"],)).fetchone()
        notes = row[0] or ""
        if hr["note_marker"] in notes:
            print("Hersel ruling note already present; skipped.")
        else:
            cur.execute(
                f"UPDATE {persons_t} SET {notes_c}=? WHERE {pid_c}=?",
                (notes + hr["note_append"], hr["person_id"]))
            print("Hersel ruling note appended to his notes.")

        # --- photo/document rows + links ---
        phc = cols(cur, photos_t)
        path_c = pick_col(phc, "local_image_path", "image_path",
                          "file_path", "path")
        phid_c = pick_col(phc, "photo_id", "id")
        link_t = "person_photos" if "person_photos" in ts else None
        if not link_t:
            surprise("person_photos table not found:", ts)
        lc = cols(cur, link_t)
        lph = pick_col(lc, "photo_id", "photo")
        lpe = pick_col(lc, "person_id", "person")
        lip = pick_col(lc, "is_primary")
        lcs = pick_col(lc, "confidence_score")
        pc_t = "photo_catalog" if "photo_catalog" in ts else None
        pcc = cols(cur, pc_t) if pc_t else []
        pc_pid = pick_col(pcc, "photo_id") if pc_t else None
        pc_title = pick_col(pcc, "title_or_caption") if pc_t else None

        for doc in DATA["documents"]:
            vals = {}
            for k, v in doc["row"].items():
                col = pick_col(phc, k)
                if col:
                    vals[col] = v
            prow = cur.execute(
                f"SELECT {phid_c} FROM {photos_t} WHERE {path_c}=?",
                (doc["row"]["local_image_path"],)).fetchone()
            if prow:
                photo_id = prow[0]
                print("Photo row already registered; skipped:",
                      photo_id)
            else:
                keys = list(vals)
                cur.execute(
                    f"INSERT INTO {photos_t} ({','.join(keys)}) "
                    f"VALUES ({','.join('?' * len(keys))})",
                    [vals[k] for k in keys])
                photo_id = cur.lastrowid
                print("Photo row created:", photo_id)
            if pc_t and pc_pid and pc_title:
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
                        pvals.append(doc["row"]["title_or_caption"])
                    cur.execute(
                        f"INSERT INTO {pc_t} ({','.join(keys)}) "
                        f"VALUES ({','.join('?' * len(keys))})", pvals)
                    print("Photo title row created in photo_catalog:",
                          photo_id)
            for pid in doc["link_person_ids"]:
                if cur.execute(
                        f"SELECT 1 FROM {link_t} WHERE {lph}=? AND "
                        f"{lpe}=?", (photo_id, pid)).fetchone():
                    print(f"Photo {photo_id} already linked to "
                          f"{pid}; skipped.")
                    continue
                keys = [lph, lpe]
                lvals = [photo_id, pid]
                if lip:
                    keys.append(lip); lvals.append(0)
                if lcs:
                    keys.append(lcs); lvals.append(1.0)
                cur.execute(
                    f"INSERT INTO {link_t} ({','.join(keys)}) "
                    f"VALUES ({','.join('?' * len(keys))})", lvals)
                print(f"Photo {photo_id} linked to person {pid}.")

        # --- final gates: the committed state must match the plan ---
        def cited(fid, sid):
            return bool(cur.execute(
                f"SELECT 1 FROM {cites_t} WHERE {cite_fid}=? AND "
                f"{cite_sid}=?", (fid, sid)).fetchone())
        gates = [
            ("1947 citation on Hersel's marriage fact",
             cited(DATA["hersel_marriage_fact"]["fact_id"], s1)),
            ("1947 citation on Myrtle's marriage fact",
             cited(myrtle_fact_id, s1)),
            ("1952 citation on Maurice's marriage fact",
             cited(DATA["maurice"]["marriage_fact_id"], s2)),
            ("exactly one Maggie Mosley profile",
             cur.execute(
                 f"SELECT COUNT(*) FROM {persons_t} WHERE {name_c}=?",
                 (mg["name"],)).fetchone()[0] == 1),
            ("Maurice linked to Hersel as father",
             rel_exists(mo["person_id"], mo["father_id"],
                        ("child_of", "parent_of"))),
            ("Maurice no longer linked to Frank Lear Wilson",
             not rel_exists(mo["person_id"], mo["wrong_father_id"],
                            ("child_of", "parent_of"))),
            ("Hersel birth_info ruled to 1913",
             cur.execute(
                 f"SELECT {pick_col(pc, 'birth_info')} FROM "
                 f"{persons_t} WHERE {pid_c}=?",
                 (hr["person_id"],)).fetchone()[0] ==
             hr["new_birth_info"]),
            ("Hersel ruled Birth fact cited to the certificate",
             bool(cur.execute(
                 f"SELECT 1 FROM {facts_t} f JOIN {cites_t} c ON "
                 f"c.{cite_fid}=f.{fid_c} WHERE f.{fpid_c}=? AND "
                 f"f.{ftype_c}='Birth' AND c.{cite_sid}=?",
                 (hr["person_id"], s1)).fetchone())),
        ]
        for doc in DATA["documents"]:
            prow = cur.execute(
                f"SELECT {phid_c} FROM {photos_t} WHERE {path_c}=?",
                (doc["row"]["local_image_path"],)).fetchone()
            nlinks = 0
            if prow:
                nlinks = cur.execute(
                    f"SELECT COUNT(*) FROM {link_t} WHERE {lph}=?",
                    (prow[0],)).fetchone()[0]
            gates.append((f"document row + {len(doc['link_person_ids'])} "
                          f"links: {doc['row']['local_image_path']}",
                          bool(prow) and
                          nlinks == len(doc["link_person_ids"])))
        failed = [name for name, ok in gates if not ok]
        if failed:
            surprise("final gate failed:", "; ".join(failed))
        print(f"Final gates passed ({len(gates)} checks).")

        con.commit()
        print("COMMITTED.")
    except SystemExit as e:
        con.rollback()
        if e.code != 3:
            raise
        print("ROLLED BACK, nothing changed.")
        sys.exit(3)
    except Exception as e:
        con.rollback()
        print("ERROR, rolled back:", e); sys.exit(4)


if __name__ == "__main__":
    main()
