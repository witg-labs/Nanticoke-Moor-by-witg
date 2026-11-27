#!/usr/bin/env python3
"""Maryland Phoebe Davis package (built 2026-11-27).

Applies Jequan Davis's 2026-11-23 rulings and her funeral program
(Watson Funeral Home, Millsboro DE; service February 1, 2020;
photographed and supplied by Jequan Davis 2026-11-20; transcription
in ~/workspace/genealogy-records/maryland-phoebe-davis/) to profile
11253:

  1. Burial fact 27650 is import boilerplate ("Interred in
     historical Delmarva cemetery", dated with her death date,
     place "Delmarva", cited to the cemetery-survey source 1274).
     The package corrects it in place to the program's interment
     (Harmony U.M. Cemetery, 28571 Harmony Cemetery Rd, Millsboro,
     following the February 1, 2020 service), detaches the 1274
     citation to the unassigned-evidence register, and cites the
     funeral program.
  2. Parent links: the child_of link to Martha E Thompson (8147),
     her grandmother, is a census-household auto-link and is
     removed (the row is captured in full into the register). The
     child_of link to her father, William Wesley Davis Sr (8609),
     is added, evidenced by the program's obituary ("born ... to
     the late William Wesley Davis and Phoebe (Thompson) Davis")
     and by the 1950 census citation already on her profile. Her
     correct child_of link to Phoebe Thompson (8146) is kept. (The
     matching wrong link to Samuel Thompson 8169 was already
     removed by the Samuel Thompson package, PR #45.)
  3. New facts, each cited to the funeral program: Companion
     (Charles Henry, companion of 37 years, predeceased her),
     Education (Millsboro #204 School; William C. Jason High
     School), Employment (Townsend Poultry Plant, over 30 years).
     Two Nickname facts: "Aunt Meryl" (the program) and "Marilyn
     (Merle)" (Jequan's 2026-11-23 statement that Marilyn Davis
     and Maryland Phoebe Davis are the same person).
  4. A notes append records, from the program, that she never had
     biological children, helped raise her sister Joan's children
     (Sandra Davis, Jane Davis, Toney Floyd), and her survivors.
     No parent links are created by the note.
  5. The generic import Marriage fact 27653 is NOT converted and
     NOT deleted (ruling 2026-11-23: it is not evidence of a
     marriage). The package marks it in fact_quality_flags with
     flag "generic_unverified" and an explanatory note.
  6. Her three funeral program page photographs are registered in
     unified_photo_catalog (plus photo_catalog title rows) and
     linked to her profile, none primary, following the Samuel
     Thompson program rows (category "people", document_type
     "funeral_program", contains_face 1, face_context
     "embedded_photo"). The image files are committed on this
     branch at frontend/public/assets/archive_media/people/.

Out of scope, deliberately: Joan Ellen Davis has no profile in the
archive, so no link is created for her; Preston Davis's parent
link is not in the approved spec; Stanley Davis (8155) is his own
package; her portraits 3679-3681 and census documents are
untouched; the man in the couch photographs stays unidentified
and is never named Charles Henry (ruling 2026-11-23).

The unassigned-evidence register is the file
unassigned_evidence_register.json in this script's directory: a
JSON list, appended to at commit time. On rollback the file is
left exactly as it was.

Schema is discovered, never assumed. One transaction, timestamped
backup first. On any surprise the script rolls back and prints
what it found. Idempotent: a second run changes nothing.

Usage: python3 apply_maryland_davis_package.py [path-to-db]
"""
import json, os, shutil, sqlite3, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "maryland_davis_package.json")))
REGISTER_PATH = os.path.join(HERE, DATA["register_file"])
DEFAULT_DB = os.path.expanduser(
    "~/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/"
    "preservation_output/genealogy_preservation.db")
EXP = DATA["expected"]
MD = 11253


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
    register_entries = []
    sources_created = []
    facts_created = []

    def register(kind, note, **payload):
        entry = {"registered_at": stamp, "package": "maryland-davis",
                 "kind": kind, "note": note}
        entry.update(payload)
        register_entries.append(entry)

    try:
        ts = tables(cur)
        persons_t = next((t for t in ("persons", "people", "person")
                          if t in ts), None)
        facts_t = next((t for t in ("facts", "person_facts")
                        if t in ts), None)
        cites_t = next((t for t in ("citations", "fact_citations")
                        if t in ts), None)
        sources_t = next((t for t in ("sources",) if t in ts), None)
        photos_t = next((t for t in ("unified_photo_catalog", "photos",
                                     "photo", "media")
                         if t in ts), None)
        rels_t = next((t for t in ("relationships",) if t in ts), None)
        flags_t = "fact_quality_flags" if "fact_quality_flags" in ts \
            else None
        link_t = "person_photos" if "person_photos" in ts else None
        pc_t = "photo_catalog" if "photo_catalog" in ts else None
        if not all([persons_t, facts_t, cites_t, sources_t, photos_t,
                    rels_t, link_t]):
            surprise("tables =", ts)
        pc = cols(cur, persons_t)
        pid_c = pick_col(pc, "person_id", "id")
        name_c = pick_col(pc, "name", "full_name")
        notes_c = pick_col(pc, "notes")

        def row_dict(table, colnames, where, args):
            row = cur.execute(
                f"SELECT {','.join(colnames)} FROM {table} WHERE "
                f"{where}", args).fetchone()
            return dict(zip(colnames, row)) if row else None

        def person_name(pid):
            row = cur.execute(
                f"SELECT {name_c} FROM {persons_t} WHERE {pid_c}=?",
                (pid,)).fetchone()
            return row[0] if row else None

        for pid, frag in DATA["expected_persons"].items():
            nm = person_name(int(pid))
            if not nm or frag.lower() not in nm.lower():
                surprise("person check failed:", pid, nm)
        print("Persons verified:", ", ".join(
            f"{pid} {person_name(int(pid))}"
            for pid in DATA["expected_persons"]))

        fc = cols(cur, facts_t)
        fid_c = pick_col(fc, "fact_id", "id")
        fpid_c = pick_col(fc, "person_id", "person")
        ftype_c = pick_col(fc, "fact_type", "type")
        fdate_c = pick_col(fc, "date_string", "date")
        fplace_c = pick_col(fc, "place_string", "place")
        fval_c = pick_col(fc, "value_string", "value")
        cc = cols(cur, cites_t)
        cid_c = pick_col(cc, "citation_id", "id")
        cite_fid = pick_col(cc, "fact_id")
        cite_sid = pick_col(cc, "source_id")
        cite_evi = pick_col(cc, "evidence_text", "evidence", "notes")
        if not all([fid_c, fpid_c, ftype_c, cite_fid, cite_sid]):
            surprise("fact/citation columns:", fc, cc)
        rc = cols(cur, rels_t)
        rid_c = pick_col(rc, "id", "relationship_id")
        ra_c = pick_col(rc, "person_a_id")
        rb_c = pick_col(rc, "person_b_id")
        rt_c = pick_col(rc, "relationship_type")
        re_c = pick_col(rc, "evidence_text")
        rcert_c = pick_col(rc, "certainty")
        if not all([ra_c, rb_c, rt_c]):
            surprise("relationships columns:", rc)

        def fact_row(fid):
            return row_dict(facts_t, fc, f"{fid_c}=?", (fid,))

        def facts_of(pid):
            rows = cur.execute(
                f"SELECT {','.join(fc)} FROM {facts_t} WHERE "
                f"{fpid_c}=?", (pid,)).fetchall()
            return [dict(zip(fc, r)) for r in rows]

        def cites_of_fact(fid):
            rows = cur.execute(
                f"SELECT {','.join(cc)} FROM {cites_t} WHERE "
                f"{cite_fid}=?", (fid,)).fetchall()
            return [dict(zip(cc, r)) for r in rows]

        def rel_rows_between(a, b, types):
            ph = ",".join("?" * len(types))
            rows = cur.execute(
                f"SELECT {','.join(rc)} FROM {rels_t} WHERE "
                f"{rt_c} IN ({ph}) AND (({ra_c}=? AND {rb_c}=?) OR "
                f"({ra_c}=? AND {rb_c}=?))",
                (*types, a, b, b, a)).fetchall()
            return [dict(zip(rc, r)) for r in rows]

        def rel_exists(a, b, types):
            return bool(rel_rows_between(a, b, types))

        def count_rels_touching(pid):
            return cur.execute(
                f"SELECT COUNT(*) FROM {rels_t} WHERE {ra_c}=? OR "
                f"{rb_c}=?", (pid, pid)).fetchone()[0]

        # --- pre-state ---
        persons_before = cur.execute(
            f"SELECT COUNT(*) FROM {persons_t}").fetchone()[0]
        sources_before = cur.execute(
            f"SELECT COUNT(*) FROM {sources_t}").fetchone()[0]
        facts_before = len(facts_of(MD))
        rels_before = count_rels_touching(MD)
        print(f"Pre-state: persons {persons_before}, sources "
              f"{sources_before}, facts on {MD} {facts_before}, "
              f"relationships touching her {rels_before}.")
        if persons_before != EXP["persons_total"]:
            surprise("persons total is not the expected "
                     f"{EXP['persons_total']}:", persons_before)
        if facts_before not in (EXP["facts_on_maryland_before"],
                                EXP["facts_on_maryland_after"]):
            surprise("facts on 11253 neither the pre-state nor the "
                     "post-state count:", facts_before)
        if rels_before != EXP["relationships_touching_maryland_before"]:
            surprise("relationships touching 11253:", rels_before)

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
            sources_created.append(cur.lastrowid)
            print("Source created:", cur.lastrowid, "-",
                  s["title"][:60])
            return cur.lastrowid

        program_sid = find_or_create_source(DATA["program_source"])
        statement_sid = find_or_create_source(DATA["statement_source"])
        source_by_key = {"program": program_sid,
                         "statement": statement_sid}

        def cite(fid, sid, evidence):
            if cur.execute(
                    f"SELECT 1 FROM {cites_t} WHERE {cite_fid}=? AND "
                    f"{cite_sid}=?", (fid, sid)).fetchone():
                print(f"Citation already present on fact {fid}; "
                      "skipped.")
                return
            keys = [cite_fid, cite_sid] + ([cite_evi] if cite_evi
                                           else [])
            vals = [fid, sid] + ([evidence] if cite_evi else [])
            cur.execute(
                f"INSERT INTO {cites_t} ({','.join(keys)}) "
                f"VALUES ({','.join('?' * len(keys))})", vals)
            print(f"Citation added to fact {fid} from source {sid}.")

        # --- 1. Burial fact correction ---
        b = DATA["burial"]
        bf = fact_row(b["fact_id"])
        if bf is None or bf[fpid_c] != b["person_id"] or \
                bf[ftype_c] != "Burial":
            surprise("burial fact check failed:", b["fact_id"], bf)
        cur_vals = (bf[fdate_c], bf[fplace_c], bf[fval_c])
        old_vals = (b["expected_old"]["date_string"],
                    b["expected_old"]["place_string"],
                    b["expected_old"]["value_string"])
        new_vals = (b["new"]["date_string"], b["new"]["place_string"],
                    b["new"]["value_string"])
        bcites = cites_of_fact(b["fact_id"])
        if cur_vals == new_vals:
            if not any(c[cite_sid] == program_sid for c in bcites):
                surprise("burial fact carries the new values but no "
                         "program citation:", bcites)
            print("Burial fact already corrected; skipped.")
        elif cur_vals == old_vals:
            if len(bcites) != 1 or \
                    bcites[0][cite_sid] != b["expected_citation_source_id"]:
                surprise("burial fact citations are not the single "
                         "expected cemetery-survey citation:", bcites)
            crow = bcites[0]
            register("citation", b["detach_note"], person_id=MD,
                     fact_id=b["fact_id"], citation=crow)
            cur.execute(
                f"DELETE FROM {cites_t} WHERE {cid_c}=?",
                (crow[cid_c],))
            print(f"Citation {crow[cid_c]} detached to the register.")
            cur.execute(
                f"UPDATE {facts_t} SET {fdate_c}=?, {fplace_c}=?, "
                f"{fval_c}=? WHERE {fid_c}=?",
                (*new_vals, b["fact_id"]))
            print("Burial fact corrected: "
                  f"{new_vals[0]}, {new_vals[1]}.")
            cite(b["fact_id"], program_sid, b["evidence"])
        else:
            surprise("burial fact carries unexpected values:",
                     cur_vals)

        # --- 2. Parent links ---
        rm = DATA["remove_parent_link"]
        wrong = rel_rows_between(rm["person_id"], rm["wrong_parent_id"],
                                 ("child_of", "parent_of"))
        add = DATA["add_parent_link"]
        have_father = rel_exists(add["person_id"], add["parent_id"],
                                 ("child_of", "parent_of"))
        if wrong:
            if len(wrong) != 1:
                surprise("expected exactly one wrong parent row:",
                         wrong)
            register("relationship", rm["note"], person_id=MD,
                     relationship=wrong[0])
            cur.execute(
                f"DELETE FROM {rels_t} WHERE {rid_c}=?",
                (wrong[0][rid_c],))
            print("Removed 1 relationship row(s): "
                  f"{rm['person_id']} <-> {rm['wrong_parent_id']} "
                  "(grandparent auto-link).")
        elif have_father:
            print("Wrong grandparent link already removed; skipped.")
        else:
            surprise("the wrong grandparent link was not found and "
                     "the father link is absent; the correction "
                     "premise changed. Nothing applied.")
        if have_father:
            print("Father link to 8609 already present; skipped.")
        else:
            keys = [ra_c, rb_c, rt_c]
            vals = [add["person_id"], add["parent_id"], "child_of"]
            if re_c:
                keys.append(re_c); vals.append(add["evidence"])
            if rcert_c:
                keys.append(rcert_c); vals.append("confirmed")
            cur.execute(
                f"INSERT INTO {rels_t} ({','.join(keys)}) "
                f"VALUES ({','.join('?' * len(keys))})", vals)
            print("Father link created: 11253 child_of 8609.")

        # --- 3. New facts ---
        for spec in DATA["new_facts"]:
            sid = source_by_key[spec["source"]]
            existing = [f for f in facts_of(MD)
                        if f[ftype_c] == spec["fact_type"]
                        and f[fval_c] == spec["value_string"]]
            if len(existing) > 1:
                surprise(f"multiple {spec['fact_type']} facts with "
                         "the package value on 11253:", existing)
            if existing:
                nfid = existing[0][fid_c]
                print(f"{spec['fact_type']} fact already exists: "
                      f"{nfid}")
            else:
                cur.execute(
                    f"INSERT INTO {facts_t} ({fpid_c}, {ftype_c}, "
                    f"{fdate_c}, {fplace_c}, {fval_c}) "
                    "VALUES (?,?,?,?,?)",
                    (MD, spec["fact_type"], spec["date_string"],
                     spec["place_string"], spec["value_string"]))
                nfid = cur.lastrowid
                facts_created.append(nfid)
                print(f"{spec['fact_type']} fact created on 11253: "
                      f"{nfid}")
            cite(nfid, sid, spec["evidence"])

        # --- 4. Notes append ---
        na = DATA["notes_append"]
        row = cur.execute(
            f"SELECT {notes_c} FROM {persons_t} WHERE {pid_c}=?",
            (na["person_id"],)).fetchone()
        notes = row[0] or ""
        if na["marker"] in notes:
            print("Program notes append already present; skipped.")
        else:
            cur.execute(
                f"UPDATE {persons_t} SET {notes_c}=? WHERE {pid_c}=?",
                (notes + na["text"], na["person_id"]))
            print("Program notes appended to 11253.")

        # --- 5. Marriage fact quality flag ---
        mf = DATA["marriage_flag"]
        mrow = fact_row(mf["fact_id"])
        if mrow is None or mrow[fpid_c] != mf["person_id"] or \
                mrow[ftype_c] != "Marriage":
            surprise("marriage fact check failed:", mf["fact_id"],
                     mrow)
        if flags_t:
            flc = cols(cur, flags_t)
            fl_fid = pick_col(flc, "fact_id")
            fl_flag = pick_col(flc, "flag")
            fl_note = pick_col(flc, "note")
            fl_at = pick_col(flc, "applied_at")
            existing_flag = cur.execute(
                f"SELECT {fl_flag} FROM {flags_t} WHERE {fl_fid}=?",
                (mf["fact_id"],)).fetchone()
            if existing_flag:
                print(f"Marriage fact already flagged "
                      f"({existing_flag[0]}); left as it is.")
            else:
                keys = [fl_fid, fl_flag]
                vals = [mf["fact_id"], mf["flag"]]
                if fl_note:
                    keys.append(fl_note); vals.append(mf["note"])
                if fl_at:
                    keys.append(fl_at)
                    vals.append(stamp[:4] + "-" + stamp[4:6] + "-" +
                                stamp[6:8])
                cur.execute(
                    f"INSERT INTO {flags_t} ({','.join(keys)}) "
                    f"VALUES ({','.join('?' * len(keys))})", vals)
                print("Marriage fact flagged generic_unverified.")
        else:
            print("fact_quality_flags table absent; flag skipped.")

        # --- 6. Program page photo rows + links ---
        phc = cols(cur, photos_t)
        path_c = pick_col(phc, "local_image_path", "image_path",
                          "file_path", "path")
        phid_c = pick_col(phc, "photo_id", "id")
        lc = cols(cur, link_t)
        lph = pick_col(lc, "photo_id", "photo")
        lpe = pick_col(lc, "person_id", "person")
        lip = pick_col(lc, "is_primary")
        lcs = pick_col(lc, "confidence_score")
        pcc = cols(cur, pc_t) if pc_t else []
        pc_pid = pick_col(pcc, "photo_id") if pc_t else None
        pc_title = pick_col(pcc, "title_or_caption") if pc_t else None
        photos_created = 0
        for doc in DATA["documents"]:
            vals = {}
            for k, v in doc["row"].items():
                col = pick_col(phc, k)
                if col:
                    vals[col] = v
            for req in ("normalized_filename", "original_filename",
                        "local_image_path", "sha256_hash"):
                if pick_col(phc, req) and \
                        pick_col(phc, req) not in vals:
                    surprise(f"photo row is missing NOT NULL field "
                             f"{req}:", doc["row"].get(
                                 "local_image_path"))
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
                photos_created += 1
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

        bf2 = fact_row(b["fact_id"])
        burial_cites = cites_of_fact(b["fact_id"])
        gates = [
            ("persons total unchanged",
             cur.execute(f"SELECT COUNT(*) FROM {persons_t}")
             .fetchone()[0] == EXP["persons_total"]),
            ("sources delta equals sources created this run",
             cur.execute(f"SELECT COUNT(*) FROM {sources_t}")
             .fetchone()[0] - sources_before == len(sources_created)),
            ("sources created this run are the full set or zero",
             len(sources_created) in (0, EXP["sources_delta_fresh_run"])),
            ("burial fact carries the corrected values",
             (bf2[fdate_c], bf2[fplace_c], bf2[fval_c]) == new_vals),
            ("burial fact cited to the funeral program",
             cited(b["fact_id"], program_sid)),
            ("cemetery-survey citation detached from burial fact",
             not any(c[cite_sid] == b["expected_citation_source_id"]
                     for c in burial_cites)),
            ("burial fact citation count is 1",
             len(burial_cites) == EXP["citations_on_burial_fact"]),
            ("wrong grandparent link gone: 11253<->8147",
             not rel_exists(MD, rm["wrong_parent_id"],
                            ("child_of", "parent_of"))),
            ("father link present: 11253 child_of 8609",
             rel_exists(MD, add["parent_id"],
                        ("child_of", "parent_of"))),
            ("mother link kept: 11253 child_of 8146",
             rel_exists(MD, 8146, ("child_of", "parent_of"))),
            ("relationships touching 11253 = 2",
             count_rels_touching(MD) ==
             EXP["relationships_touching_maryland_after"]),
            ("facts on 11253 = 13",
             len(facts_of(MD)) == EXP["facts_on_maryland_after"]),
            ("facts created this run are the full set or zero",
             len(facts_created) in (0, len(DATA["new_facts"]))),
            ("program notes append present",
             na["marker"] in (cur.execute(
                 f"SELECT {notes_c} FROM {persons_t} WHERE {pid_c}=?",
                 (MD,)).fetchone()[0] or "")),
            ("register entries this run are the full set or zero",
             len(register_entries) in
             (0, EXP["register_entries_fresh_run"])),
            ("PRAGMA integrity_check",
             cur.execute("PRAGMA integrity_check").fetchone()[0]
             == "ok"),
        ]
        for spec in DATA["new_facts"]:
            sid = source_by_key[spec["source"]]
            match = [f for f in facts_of(MD)
                     if f[ftype_c] == spec["fact_type"]
                     and f[fval_c] == spec["value_string"]]
            gates.append((
                f"{spec['fact_type']} fact present and cited: "
                f"{spec['key']}",
                len(match) == 1 and cited(match[0][fid_c], sid)))
        if flags_t:
            gates.append((
                "marriage fact carries a quality flag",
                bool(cur.execute(
                    f"SELECT 1 FROM {flags_t} WHERE "
                    f"{pick_col(cols(cur, flags_t), 'fact_id')}=?",
                    (mf["fact_id"],)).fetchone())))
        for doc in DATA["documents"]:
            prow = cur.execute(
                f"SELECT {phid_c} FROM {photos_t} WHERE {path_c}=?",
                (doc["row"]["local_image_path"],)).fetchone()
            nlinks = 0
            if prow:
                nlinks = cur.execute(
                    f"SELECT COUNT(*) FROM {link_t} WHERE {lph}=?",
                    (prow[0],)).fetchone()[0]
            gates.append((
                f"photo row + {len(doc['link_person_ids'])} link(s): "
                f"{doc['row']['local_image_path']}",
                bool(prow) and
                nlinks == len(doc["link_person_ids"])))
        gates.append((
            "photo rows created this run are the full set or zero",
            photos_created in (0, EXP["photos_delta_fresh_run"])))
        for name, ok in gates:
            print(("PASS " if ok else "FAIL ") + name)
        failed = [name for name, ok in gates if not ok]
        if failed:
            surprise("final gate failed:", "; ".join(failed))
        print(f"Final gates passed ({len(gates)} checks).")
        print(f"Field changes this run: sources created "
              f"{len(sources_created)}, facts created "
              f"{len(facts_created)}, photo rows created "
              f"{photos_created}, register entries "
              f"{len(register_entries)}.")

        con.commit()
        if register_entries:
            existing = []
            if os.path.exists(REGISTER_PATH):
                with open(REGISTER_PATH) as fh:
                    existing = json.load(fh)
            existing.extend(register_entries)
            with open(REGISTER_PATH, "w") as fh:
                json.dump(existing, fh, indent=1)
            print(f"Register updated: {REGISTER_PATH} "
                  f"(+{len(register_entries)} entries).")
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
