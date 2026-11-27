#!/usr/bin/env python3
"""Samuel Thompson Jr correction package (built 2026-11-27).

Spec: SAMUEL_THOMPSON_JR_CORRECTION_PACKAGE_2026-11-27.md, sections
1-12. Addendum 2 (section 12) is folded in and supersedes sections
7b and 8a/8b where they overlap. Addendum 1 (section 11) items 1-3
(Jelly / Bradley / Deroy profiles) and items 4-5 (Wydell 8352,
Ruth Ann 8268 corrections) are FOLLOW-ON scope and are NOT applied
here, except that item 5's premise (Ruth Ann's parent link stands)
is respected: no relationship on 8268 is touched. Jequan's ruling
of 2026-11-27 that Shirley Thompson (8265) IS alive is folded in
per tasking, superseding the spec's section 8a flag-only treatment
of her 1992 death date.

What this package does, in one transaction:

  1. Profile 8169 (Samuel Thompson Jr): birth corrected to
     27 Sep 1930, Lewes under Jequan's obituary-override rule
     (persons.birth_info and Birth fact 7607); citation 30159
     (the asserted 1929 Newark registration, never read) STAYS on
     fact 7607 with its evidence_text prefixed SUPERSEDED; name
     "Samuel Thompson" -> "Samuel Thompson Jr"; a Nickname fact
     ("Bull") cited to Jequan's 2026-11-27 statement source (NOT
     to the funeral program, which does not carry the nickname);
     the program's family counts appended to persons.notes.
  2. The three wrong census-auto-link relationships on 8169 are
     captured in full into the unassigned-evidence register and
     deleted: spouse_of Martha E Thompson 8147 (his mother),
     parent_of Primrose Elizabeth Thompson 8168 (his sister),
     parent_of Maryland Phoebe Davis 11253 (his niece). Deletes
     are delete-if-present, keyed on the person pair and link
     kind, so the package is a no-op on any row the Maryland
     Davis package already removed.
  3. Census fact 16131 is reframed to Jr.'s position in the 1950
     household (value_string replaced with the plan text);
     citation 30161 (1930 Census, generic template text) is
     detached to the register. Citation 14941 (1950 Census)
     stays.
  4. Template-citation repair: citation 30160 comes off Death
     fact 7608 and citation 30163 comes off Marriage fact 24345
     (both to the register; source 1270 is a birth register
     ending 1930 and cannot evidence a 2006 death or a 1959
     marriage). The funeral program source (find-or-create on
     exact title) is cited on both facts. Marriage fact 24345 is
     set to date "1959", place "Delaware", and the plan's value
     text. SS-5 fact 24344 (dated "1929", impossible: the SS-5
     program began in 1936) is detached whole, with citation
     30162, to the register.
  5. Cross-profile name fixes: 8264 "Gerld Lee Thompson" ->
     "Gerald Lee Thompson"; 10097 "Tinnie Thompson" ->
     "Douglas Thompson (Tinnie)"; 10098 "Biggie Thompson" ->
     "Donnell Thompson (Biggie)" (Addendum 2 parenthesis form);
     8351 "David Thompson" -> "David Lee Thompson".
  6. David 8351 (Addendum 2: he IS David Lee Thompson): birth
     and death corrected to his own funeral program (20 May 1955
     Lewes; 19 Sep 2018 Milford) on persons.birth_info /
     death_info and on his Birth and Death facts; the
     source-1270 citations on those facts are prefixed
     SUPERSEDED in place; the David Lee program source
     (find-or-create) is cited on both facts; the pre-correction
     rows are captured in the register as superseded-in-place.
     His Burial, Census, SS-5, and Marriage facts are NOT
     touched: Addendum 2 does not order it (see BUILD_REPORT).
  7. Tinnie 10097 / Biggie 10098 (Addendum 2): dates removed,
     both men marked living (birth_info / death_info cleared to
     "unknown", the archive's no-value representation). Birth /
     Death facts carrying the wrong-life values (10097: b.
     10 Dec 1925, d. 5 May 1997; 10098: d. 24 Jun 1864) are
     detached to the register, quoted in full. Nickname facts
     ("Tinnie", "Biggie") cited to Jequan's statement; each
     profile's Name fact cited to Samuel's funeral program for
     the full names Douglas and Donnell. Other facts on these
     profiles (Burial, Census, SS-5, Marriage) are NOT touched.
  8. Shirley 8265 (Jequan's 2026-11-27 ruling: she is alive):
     persons.death_info cleared to "unknown"; her Death fact
     carrying 30 May 1992 is detached to the register as
     contradicted (Samuel's 2006 program, Annabelle's 2001
     program, and David Lee's 2018 program all name her among
     the living). Her Burial fact (FindAGrave, same date) is NOT
     touched: the ruling named the Death fact (see BUILD_REPORT).

The unassigned-evidence register is the file
unassigned_evidence_register.json in this script's directory:
every detached or superseded-in-place row is written there in
full (all columns, verbatim) with its detachment note, before
commit. Nothing captured there is deleted from the record; the
rows only leave the live profile. If the run rolls back, the
register file is restored to its pre-run contents.

Schema is discovered, never assumed (exact-name candidate lists,
PRAGMA table_info read including NOT NULL flags). One
transaction, timestamped backup first. Every field change is
gated on the current value being either the expected old value
(apply) or the expected new value (skip: already applied); any
other value aborts the run with a rollback. Final in-transaction
gates assert the plan's expected counts. Idempotent: a second
run is a no-op that passes all gates.

Usage: python3 apply_samuel_thompson_jr_correction.py [path-to-genealogy_preservation.db]
"""
import json, os, shutil, sqlite3, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE,
                                   "samuel_thompson_jr_correction.json")))
REGISTER_PATH = os.path.join(HERE, DATA["register_file"])
DEFAULT_DB = os.path.expanduser(
    "~/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/"
    "preservation_output/genealogy_preservation.db")
CLEARED = DATA["cleared_value"]
EXP = DATA["expected"]


def cols(cur, table):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]


def table_info(cur, table):
    # (name, type, notnull, default) per column
    return [(r[1], r[2], r[3], r[4])
            for r in cur.execute(f"PRAGMA table_info({table})")]


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
    register_before = None
    if os.path.exists(REGISTER_PATH):
        with open(REGISTER_PATH, "rb") as fh:
            register_before = fh.read()
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    register_entries = []
    changes = {"name": 0, "birth_info": 0, "death_info": 0}
    sources_created = []

    def register(kind, note, **payload):
        entry = {"registered_at": stamp, "package": "samuel-thompson-jr",
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
        rels_t = next((t for t in ("relationships",) if t in ts), None)
        if not all([persons_t, facts_t, cites_t, sources_t, rels_t]):
            surprise("tables =", ts)

        # --- schema: columns AND nullability (a name list is not
        # a schema). Inserts in this package must supply every
        # NOT NULL column with no default on the tables they hit.
        pc_info = table_info(cur, persons_t)
        pc = [c[0] for c in pc_info]
        pid_c = pick_col(pc, "person_id", "id")
        name_c = pick_col(pc, "name", "full_name")
        binfo_c = pick_col(pc, "birth_info")
        dinfo_c = pick_col(pc, "death_info")
        notes_c = pick_col(pc, "notes")
        if not all([pid_c, name_c, binfo_c, dinfo_c]):
            surprise("persons columns:", pc)
        nn = {c[0]: (c[2], c[3]) for c in pc_info}
        if not nn[name_c][0]:
            surprise("persons.name is not NOT NULL in the live "
                     "schema; the package's collision logic assumes "
                     "the UNIQUE/NOT NULL name column:", pc_info)
        fc = cols(cur, facts_t)
        fid_c = pick_col(fc, "fact_id", "id")
        fpid_c = pick_col(fc, "person_id", "person")
        ftype_c = pick_col(fc, "fact_type", "type")
        fdate_c = pick_col(fc, "date_string", "date")
        fplace_c = pick_col(fc, "place_string", "place")
        fval_c = pick_col(fc, "value_string", "value")
        if not all([fid_c, fpid_c, ftype_c]):
            surprise("facts columns:", fc)
        fnn = {c[0]: (c[2], c[3]) for c in table_info(cur, facts_t)}
        if not fnn[ftype_c][0]:
            surprise("facts.fact_type is not NOT NULL in the live "
                     "schema:", fc)
        cc = cols(cur, cites_t)
        cid_c = pick_col(cc, "citation_id", "id")
        cite_fid = pick_col(cc, "fact_id")
        cite_sid = pick_col(cc, "source_id")
        cite_evi = pick_col(cc, "evidence_text", "evidence", "notes")
        if not all([cid_c, cite_fid, cite_sid]):
            surprise("citations model not direct:", cc)
        sc = cols(cur, sources_t)
        sid_c = pick_col(sc, "source_id", "id")
        title_c = pick_col(sc, "title", "source_title", "name")
        if not all([sid_c, title_c]):
            surprise("sources columns:", sc)
        rc = cols(cur, rels_t)
        rid_c = pick_col(rc, "id", "relationship_id")
        ra_c = pick_col(rc, "person_a_id")
        rb_c = pick_col(rc, "person_b_id")
        rt_c = pick_col(rc, "relationship_type")
        re_c = pick_col(rc, "evidence_text")
        rcert_c = pick_col(rc, "certainty")
        if not all([ra_c, rb_c, rt_c]) or not rid_c:
            surprise("relationships columns:", rc)

        def row_dict(table, colnames, where, params):
            r = cur.execute(
                f"SELECT {','.join(colnames)} FROM {table} "
                f"WHERE {where}", params).fetchone()
            return dict(zip(colnames, r)) if r else None

        def person_row(pid):
            return row_dict(persons_t, pc, f"{pid_c}=?", (pid,))

        def fact_row(fid):
            return row_dict(facts_t, fc, f"{fid_c}=?", (fid,))

        def facts_of(pid):
            rows = cur.execute(
                f"SELECT {','.join(fc)} FROM {facts_t} "
                f"WHERE {fpid_c}=?", (pid,)).fetchall()
            return [dict(zip(fc, r)) for r in rows]

        def cites_of_fact(fid):
            rows = cur.execute(
                f"SELECT {','.join(cc)} FROM {cites_t} "
                f"WHERE {cite_fid}=?", (fid,)).fetchall()
            return [dict(zip(cc, r)) for r in rows]

        def cites_on_facts_of(pid):
            return cur.execute(
                f"SELECT COUNT(*) FROM {cites_t} c JOIN {facts_t} f "
                f"ON c.{cite_fid}=f.{fid_c} WHERE f.{fpid_c}=?",
                (pid,)).fetchone()[0]

        def rels_touching(pid):
            return cur.execute(
                f"SELECT COUNT(*) FROM {rels_t} WHERE {ra_c}=? OR "
                f"{rb_c}=?", (pid, pid)).fetchone()[0]

        # --- pre-state verification: people, with exact names ---
        named = {}
        for blk in (DATA["samuel"], DATA["gerald"], DATA["david"],
                    DATA["tinnie"], DATA["biggie"], DATA["shirley"]):
            named[blk["person_id"]] = blk
        for pid, blk in named.items():
            row = person_row(pid)
            if not row:
                surprise("person not found:", pid)
            cur_name = row[name_c]
            if cur_name not in (blk["expected_name"],
                                blk.get("new_name",
                                        blk["expected_name"])):
                surprise("person name check failed:", pid, cur_name)
        print("Persons verified:", ", ".join(
            f"{pid} {person_row(pid)[name_c]}" for pid in named))

        # --- rename collision check (persons.name UNIQUE): every
        # target name must be free or already on its own profile.
        for blk in named.values():
            new = blk.get("new_name")
            if not new:
                continue
            hit = cur.execute(
                f"SELECT {pid_c} FROM {persons_t} WHERE {name_c}=?",
                (new,)).fetchone()
            if hit and hit[0] != blk["person_id"]:
                surprise("rename collision: target name already on "
                         "another profile:", new, hit[0])
        print("Rename targets collision-free.")

        # --- pre-state counts (each must be the pristine or the
        # fully-applied value; anything else is a surprise) ---
        persons_before = cur.execute(
            f"SELECT COUNT(*) FROM {persons_t}").fetchone()[0]
        if persons_before != EXP["persons_total"]:
            surprise("persons total:", persons_before,
                     "expected", EXP["persons_total"])
        sam = DATA["samuel"]
        spid = sam["person_id"]
        facts_before = len(facts_of(spid))
        if facts_before not in (EXP["facts_on_samuel_before"],
                                EXP["facts_on_samuel_after"]):
            surprise("facts on 8169:", facts_before)
        cites_before = cites_on_facts_of(spid)
        if cites_before not in (
                EXP["citations_on_samuel_facts_before"],
                EXP["citations_on_samuel_facts_after"]):
            surprise("citations on 8169's facts:", cites_before)
        rels_before = rels_touching(spid)
        if rels_before not in (
                EXP["relationships_touching_samuel_before"],
                EXP["relationships_touching_samuel_after"]):
            surprise("relationships touching 8169:", rels_before)
        sources_before = cur.execute(
            f"SELECT COUNT(*) FROM {sources_t}").fetchone()[0]
        print(f"Pre-state: persons {persons_before}, facts on 8169 "
              f"{facts_before}, citations on his facts {cites_before}, "
              f"relationships touching him {rels_before}, sources "
              f"{sources_before}.")

        # --- verify 8169's facts and citations by id ---
        for fid, ftype in ((sam["birth_fact_id"], "Birth"),
                           (sam["death_fact_id"], "Death"),
                           (sam["census_fact_id"], "Census"),
                           (sam["marriage_fact_id"], "Marriage")):
            fr = fact_row(fid)
            if not fr or fr[fpid_c] != spid or fr[ftype_c] != ftype:
                surprise("fact check failed:", fid, fr)
        # The SS-5 fact must be present in pristine state and is
        # legitimately ABSENT after a completed run (it is the
        # fact this package detaches); any other state surprises.
        fr = fact_row(sam["ss5_fact_id"])
        if fr is not None and (fr[fpid_c] != spid or
                               fr[ftype_c] !=
                               "Social Security Application"):
            surprise("SS-5 fact check failed:", sam["ss5_fact_id"],
                     fr)
        for ckey in ("supersede_citation_id", "death_detach_citation_id",
                     "census_detach_citation_id",
                     "marriage_detach_citation_id"):
            crow = row_dict(cites_t, cc, f"{cid_c}=?", (sam[ckey],))
            if crow is not None and crow[cite_fid] not in (
                    sam["birth_fact_id"], sam["death_fact_id"],
                    sam["census_fact_id"], sam["marriage_fact_id"]):
                surprise("citation on unexpected fact:", sam[ckey],
                         crow)
        print("Samuel's facts and template citations verified.")

        # --- sources (find or create, keyed on exact title) ---
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
            sources_created.append(s["key"])
            print("Source created:", cur.lastrowid, "-",
                  s["title"][:60])
            return cur.lastrowid

        src = {k: find_or_create_source(DATA["sources"][k])
               for k in ("samuel_program", "david_program",
                         "jequan_statement")}

        # --- shared helpers ---
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

        def set_person_field(blk, col, expected_old, new_val,
                             counter):
            pid = blk["person_id"]
            cur_val = person_row(pid)[col]
            if cur_val == new_val:
                print(f"Person {pid} {col} already set; skipped.")
                return
            if cur_val != expected_old:
                surprise(f"person {pid} {col} is neither the "
                         "expected old nor the new value:", cur_val)
            cur.execute(
                f"UPDATE {persons_t} SET {col}=? WHERE {pid_c}=?",
                (new_val, pid))
            changes[counter] += 1
            print(f"Person {pid} {col}: {cur_val!r} -> {new_val!r}.")

        def rename(blk):
            set_person_field(blk, name_c, blk["expected_name"],
                             blk["new_name"], "name")

        def detach_citation(cid, note, person_id, fact_id):
            crow = row_dict(cites_t, cc, f"{cid_c}=?", (cid,))
            if crow is None:
                print(f"Citation {cid} already detached; skipped.")
                return
            if crow[cite_fid] != fact_id:
                surprise(f"citation {cid} is on fact "
                         f"{crow[cite_fid]}, expected {fact_id}")
            register("citation", note, person_id=person_id,
                     fact_id=fact_id, citation=crow)
            cur.execute(
                f"DELETE FROM {cites_t} WHERE {cid_c}=?", (cid,))
            print(f"Citation {cid} detached to the register.")

        def detach_fact_by_id(fid, note, person_id):
            fr = fact_row(fid)
            if fr is None:
                print(f"Fact {fid} already detached; skipped.")
                return
            if fr[fpid_c] != person_id:
                surprise(f"fact {fid} belongs to {fr[fpid_c]}, "
                         f"expected {person_id}")
            register("fact", note, person_id=person_id, fact=fr,
                     citations=cites_of_fact(fid))
            cur.execute(
                f"DELETE FROM {cites_t} WHERE {cite_fid}=?", (fid,))
            cur.execute(
                f"DELETE FROM {facts_t} WHERE {fid_c}=?", (fid,))
            print(f"Fact {fid} detached to the register.")

        def find_fact(pid, ftype, old_marker=None, new_date=None):
            cands = [f for f in facts_of(pid)
                     if f[ftype_c] == ftype]
            if len(cands) != 1:
                surprise(f"expected exactly one {ftype} fact on "
                         f"{pid}, found {len(cands)}")
            f = cands[0]
            d = f[fdate_c] or ""
            if old_marker and old_marker in d:
                return f, "old"
            if new_date and d == new_date:
                return f, "new"
            surprise(f"{ftype} fact on {pid} carries an unexpected "
                     f"date:", d)

        def detach_fact_by_type_date(pid, ftype, marker, note):
            cands = [f for f in facts_of(pid)
                     if f[ftype_c] == ftype
                     and marker in (f[fdate_c] or "")]
            if not cands:
                print(f"No {ftype} fact carrying {marker!r} on "
                      f"{pid}; already detached, skipped.")
                return
            if len(cands) > 1:
                surprise(f"multiple {ftype} facts carry {marker!r} "
                         f"on {pid}")
            detach_fact_by_id(cands[0][fid_c], note, pid)

        def add_nickname_fact(blk):
            spec = blk["nickname_fact"]
            pid = blk["person_id"]
            sid = src[spec["source_key"]]
            existing = [f for f in facts_of(pid)
                        if f[ftype_c] == spec["fact_type"]
                        and f[fval_c] == spec["value_string"]]
            if existing:
                fid = existing[0][fid_c]
                print(f"Nickname fact already present on {pid}: "
                      f"{fid}")
            else:
                cur.execute(
                    f"INSERT INTO {facts_t} ({fpid_c}, {ftype_c}, "
                    f"{fval_c}) VALUES (?,?,?)",
                    (pid, spec["fact_type"], spec["value_string"]))
                fid = cur.lastrowid
                print(f"Nickname fact created on {pid}: {fid}")
            cite(fid, sid, spec["evidence"])

        def cite_name_fact_to_program(blk):
            pid = blk["person_id"]
            names = [f for f in facts_of(pid)
                     if f[ftype_c] == "Name"]
            if len(names) != 1:
                surprise(f"expected exactly one Name fact on {pid}, "
                         f"found {len(names)}")
            cite(names[0][fid_c], src["samuel_program"],
                 blk["name_fact_program_evidence"])

        SPOUSE_TYPES = ("spouse_of", "spouse", "spouses")
        PARENT_TYPES = ("parent_of", "child_of")

        def rel_rows_for_pair(a, b, types):
            ph = ",".join("?" * len(types))
            return cur.execute(
                f"SELECT {','.join(rc)} FROM {rels_t} WHERE "
                f"{rt_c} IN ({ph}) AND (({ra_c}=? AND {rb_c}=?) OR "
                f"({ra_c}=? AND {rb_c}=?))",
                (*types, a, b, b, a)).fetchall()

        def remove_relationship(spid_, spec):
            other = spec["other_id"]
            if spec["kind"] == "spouse":
                rows = [dict(zip(rc, r)) for r in
                        rel_rows_for_pair(spid_, other,
                                          SPOUSE_TYPES)]
            else:
                fwd = cur.execute(
                    f"SELECT {','.join(rc)} FROM {rels_t} WHERE "
                    f"{rt_c}='parent_of' AND {ra_c}=? AND {rb_c}=?",
                    (spid_, other)).fetchall()
                rev = cur.execute(
                    f"SELECT {','.join(rc)} FROM {rels_t} WHERE "
                    f"{rt_c}='child_of' AND {ra_c}=? AND {rb_c}=?",
                    (other, spid_)).fetchall()
                rows = [dict(zip(rc, r)) for r in fwd + rev]
            if not rows:
                print(f"Relationship {spid_}<->{other} "
                      f"({spec['kind']}) already absent; skipped.")
                return
            for row in rows:
                register("relationship", spec["note"],
                         person_id=spid_, relationship=row)
                cur.execute(
                    f"DELETE FROM {rels_t} WHERE {rid_c}=?",
                    (row[rid_c],))
            print(f"Removed {len(rows)} relationship row(s): "
                  f"{spid_} <-> {other} ({spec['kind']}).")

        # ============ Samuel 8169 ============
        rename(sam)
        set_person_field(sam, binfo_c, sam["expected_birth_info"],
                         sam["new_birth_info"], "birth_info")

        # Birth fact 7607: new date; citation 30159 kept, prefixed
        fr = fact_row(sam["birth_fact_id"])
        if fr[fdate_c] == sam["birth_fact_new_date_string"]:
            print("Birth fact 7607 already corrected; skipped.")
        elif fr[fdate_c] == sam["expected_birth_info"]:
            cur.execute(
                f"UPDATE {facts_t} SET {fdate_c}=? WHERE {fid_c}=?",
                (sam["birth_fact_new_date_string"],
                 sam["birth_fact_id"]))
            print("Birth fact 7607 date corrected.")
        else:
            surprise("Birth fact 7607 date:", fr[fdate_c])
        crow = row_dict(cites_t, cc, f"{cid_c}=?",
                        (sam["supersede_citation_id"],))
        if crow is None:
            surprise("citation 30159 missing; it must be retained "
                     "as the superseded claim")
        if crow[cite_fid] != sam["birth_fact_id"]:
            surprise("citation 30159 on unexpected fact:",
                     crow[cite_fid])
        ev = crow[cite_evi] or ""
        if ev.startswith("SUPERSEDED"):
            print("Citation 30159 already marked superseded; "
                  "skipped.")
        else:
            cur.execute(
                f"UPDATE {cites_t} SET {cite_evi}=? WHERE {cid_c}=?",
                (sam["supersede_prefix"] + ev,
                 sam["supersede_citation_id"]))
            print("Citation 30159 evidence prefixed SUPERSEDED "
                  "(retained on fact 7607).")
        print("NOTE: the 1929 Newark birth registration behind "
              "citation 30159 has never been read; the citation is "
              "an asserted claim, retained as superseded under the "
              "obituary-override rule. Pulling it at the Delaware "
              "Public Archives is a research follow-up, not a "
              "blocker.")

        # Nickname fact + family counts note
        add_nickname_fact(sam)
        prow = person_row(spid)
        notes = prow[notes_c] or ""
        if sam["notes_marker"] in notes:
            print("Family-counts note already present; skipped.")
        else:
            cur.execute(
                f"UPDATE {persons_t} SET {notes_c}=? WHERE "
                f"{pid_c}=?", (notes + sam["notes_append"], spid))
            print("Family counts appended to Samuel's notes.")

        # Census fact 16131: reframe + detach the 1930 citation
        fr = fact_row(sam["census_fact_id"])
        if fr[fval_c] == sam["census_new_value_string"]:
            print("Census fact 16131 already reframed; skipped.")
        elif (fr[fval_c] or "").startswith(
                "1950 US Federal Census: Head, age 54"):
            cur.execute(
                f"UPDATE {facts_t} SET {fval_c}=? WHERE {fid_c}=?",
                (sam["census_new_value_string"],
                 sam["census_fact_id"]))
            print("Census fact 16131 reframed to Jr.'s position.")
        else:
            surprise("Census fact 16131 value:", fr[fval_c])
        detach_citation(sam["census_detach_citation_id"],
                        sam["census_detach_note"], spid,
                        sam["census_fact_id"])

        # Death fact 7608: detach 30160, cite the program
        detach_citation(sam["death_detach_citation_id"],
                        sam["death_detach_note"], spid,
                        sam["death_fact_id"])
        cite(sam["death_fact_id"], src["samuel_program"],
             sam["death_program_evidence"])

        # Marriage fact 24345: set fields, detach 30163, cite
        fr = fact_row(sam["marriage_fact_id"])
        if fr[fdate_c] == sam["marriage_new_date_string"] and \
                fr[fval_c] == sam["marriage_new_value_string"]:
            print("Marriage fact 24345 already set; skipped.")
        elif fr[fdate_c] in (None, "") and \
                fr[fval_c] == ("Marriage record documented for "
                               "Samuel Thompson"):
            cur.execute(
                f"UPDATE {facts_t} SET {fdate_c}=?, {fplace_c}=?, "
                f"{fval_c}=? WHERE {fid_c}=?",
                (sam["marriage_new_date_string"],
                 sam["marriage_place_string"],
                 sam["marriage_new_value_string"],
                 sam["marriage_fact_id"]))
            print("Marriage fact 24345 set to 1959.")
        else:
            surprise("Marriage fact 24345 state:", fr)
        detach_citation(sam["marriage_detach_citation_id"],
                        sam["marriage_detach_note"], spid,
                        sam["marriage_fact_id"])
        cite(sam["marriage_fact_id"], src["samuel_program"],
             sam["marriage_program_evidence"])

        # SS-5 fact 24344: detach whole, with its citation
        detach_fact_by_id(sam["ss5_fact_id"], sam["ss5_detach_note"],
                          spid)

        # The three wrong relationships
        for spec in sam["relationship_removals"]:
            remove_relationship(spid, spec)

        # ============ Gerald 8264: rename only ============
        rename(DATA["gerald"])

        # ============ David 8351 (Addendum 2) ============
        dav = DATA["david"]
        dpid = dav["person_id"]
        rename(dav)
        set_person_field(dav, binfo_c, dav["expected_birth_info"],
                         dav["new_birth_info"], "birth_info")
        set_person_field(dav, dinfo_c, dav["expected_death_info"],
                         dav["new_death_info"], "death_info")
        for ftype, marker, new_date, ev_key in (
                ("Birth", dav["birth_fact_old_marker"],
                 dav["birth_fact_new_date_string"],
                 "birth_program_evidence"),
                ("Death", dav["death_fact_old_marker"],
                 dav["death_fact_new_date_string"],
                 "death_program_evidence")):
            f, state = find_fact(dpid, ftype, marker, new_date)
            fid = f[fid_c]
            if state == "old":
                register("fact_superseded_in_place",
                         dav["register_note"], person_id=dpid,
                         fact=f, citations=cites_of_fact(fid))
                cur.execute(
                    f"UPDATE {facts_t} SET {fdate_c}=? WHERE "
                    f"{fid_c}=?", (new_date, fid))
                note = dav["correction_note"]
                val = f[fval_c]
                if not val:
                    cur.execute(
                        f"UPDATE {facts_t} SET {fval_c}=? WHERE "
                        f"{fid_c}=?", (note, fid))
                elif "Superseded value previously recorded" not in \
                        val:
                    cur.execute(
                        f"UPDATE {facts_t} SET {fval_c}=? WHERE "
                        f"{fid_c}=?", (val + " " + note, fid))
                for crow in cites_of_fact(fid):
                    if crow[cite_sid] == 1270:
                        ev = crow[cite_evi] or ""
                        if not ev.startswith("SUPERSEDED"):
                            cur.execute(
                                f"UPDATE {cites_t} SET {cite_evi}=? "
                                f"WHERE {cid_c}=?",
                                (dav["supersede_prefix"] + ev,
                                 crow[cid_c]))
                print(f"David's {ftype} fact {fid} corrected to "
                      f"{new_date}; source-1270 citation marked "
                      "superseded in place.")
            else:
                print(f"David's {ftype} fact {fid} already "
                      "corrected; skipped.")
            cite(fid, src["david_program"], dav[ev_key])

        # ============ Tinnie 10097 / Biggie 10098 (Addendum 2) ====
        for blk, has_birth in ((DATA["tinnie"], True),
                               (DATA["biggie"], False)):
            pid = blk["person_id"]
            rename(blk)
            set_person_field(blk, binfo_c,
                             blk.get("expected_birth_info", CLEARED),
                             CLEARED, "birth_info")
            set_person_field(blk, dinfo_c,
                             blk["expected_death_info"], CLEARED,
                             "death_info")
            if has_birth:
                detach_fact_by_type_date(
                    pid, "Birth", blk["birth_fact_old_marker"],
                    blk["birth_detach_note"])
            detach_fact_by_type_date(
                pid, "Death", blk["death_fact_old_marker"],
                blk["death_detach_note"])
            add_nickname_fact(blk)
            cite_name_fact_to_program(blk)

        # ============ Shirley 8265 (ruling: she is alive) ========
        shi = DATA["shirley"]
        set_person_field(shi, dinfo_c, shi["expected_death_info"],
                         CLEARED, "death_info")
        detach_fact_by_type_date(shi["person_id"], "Death",
                                 shi["death_fact_old_marker"],
                                 shi["death_detach_note"])
        print("Shirley Thompson marked living; her 1992 Death "
              "fact is in the register as contradicted.")

        # ============ final gates ============
        def person_field(pid, col):
            return person_row(pid)[col]

        gates = []
        gates.append(("persons total unchanged",
                      cur.execute(
                          f"SELECT COUNT(*) FROM {persons_t}"
                      ).fetchone()[0] == EXP["persons_total"]))
        for blk in named.values():
            new = blk.get("new_name")
            if new:
                gates.append((f"name set on {blk['person_id']}",
                              person_field(blk["person_id"],
                                           name_c) == new))
        gates.append(("8169 birth_info corrected",
                      person_field(spid, binfo_c) ==
                      sam["new_birth_info"]))
        gates.append(("8351 birth_info corrected",
                      person_field(dpid, binfo_c) ==
                      dav["new_birth_info"]))
        gates.append(("8351 death_info corrected",
                      person_field(dpid, dinfo_c) ==
                      dav["new_death_info"]))
        for pid in (10097, 10098, 8265):
            gates.append((f"{pid} death_info cleared (living)",
                          person_field(pid, dinfo_c) == CLEARED))
        gates.append(("10097 birth_info cleared (living)",
                      person_field(10097, binfo_c) == CLEARED))
        gates.append(("facts on 8169 = 6 (SS-5 out, Nickname in)",
                      len(facts_of(spid)) ==
                      EXP["facts_on_samuel_after"]))
        gates.append(("citations on 8169's facts = 8 (see "
                      "BUILD_REPORT on the spec's 9-after figure)",
                      cites_on_facts_of(spid) ==
                      EXP["citations_on_samuel_facts_after"]))
        gates.append(("relationships touching 8169 = 12",
                      rels_touching(spid) ==
                      EXP["relationships_touching_samuel_after"]))
        for spec in sam["relationship_removals"]:
            types = SPOUSE_TYPES if spec["kind"] == "spouse" \
                else PARENT_TYPES
            if spec["kind"] == "spouse":
                gone = not rel_rows_for_pair(spid, spec["other_id"],
                                             types)
            else:
                gone = not cur.execute(
                    f"SELECT 1 FROM {rels_t} WHERE "
                    f"({rt_c}='parent_of' AND {ra_c}=? AND "
                    f"{rb_c}=?) OR ({rt_c}='child_of' AND {ra_c}=? "
                    f"AND {rb_c}=?)",
                    (spid, spec["other_id"], spec["other_id"],
                     spid)).fetchone()
            gates.append((f"wrong link gone: 8169<->"
                          f"{spec['other_id']} ({spec['kind']})",
                          gone))
        gates.append(("citation 30159 retained, marked superseded",
                      (row_dict(cites_t, cc, f"{cid_c}=?",
                                (sam["supersede_citation_id"],))
                       or {}).get(cite_evi, "").startswith(
                          "SUPERSEDED")))
        for gone_cid in (sam["death_detach_citation_id"],
                         sam["census_detach_citation_id"],
                         sam["marriage_detach_citation_id"]):
            gates.append((f"citation {gone_cid} detached",
                          row_dict(cites_t, cc, f"{cid_c}=?",
                                   (gone_cid,)) is None))
        gates.append(("SS-5 fact 24344 detached",
                      fact_row(sam["ss5_fact_id"]) is None))
        for key in ("samuel_program", "david_program",
                    "jequan_statement"):
            gates.append((f"exactly one source: {key}",
                          cur.execute(
                              f"SELECT COUNT(*) FROM {sources_t} "
                              f"WHERE {title_c}=?",
                              (DATA["sources"][key]["title"],)
                          ).fetchone()[0] == 1))
        gates.append(("sources delta equals sources created this "
                      "run",
                      cur.execute(
                          f"SELECT COUNT(*) FROM {sources_t}"
                      ).fetchone()[0] - sources_before ==
                      len(sources_created)))
        total_changes = (changes["name"] + changes["birth_info"] +
                         changes["death_info"])
        expected_changes = (EXP["name_changes"] +
                            EXP["birth_info_changes"] +
                            EXP["death_info_changes"])
        gates.append(("field changes this run are the full set or "
                      "zero (idempotent re-run)",
                      total_changes in (0, expected_changes) and
                      changes["name"] in (0, EXP["name_changes"]) and
                      changes["birth_info"] in
                      (0, EXP["birth_info_changes"]) and
                      changes["death_info"] in
                      (0, EXP["death_info_changes"])))
        ic = cur.execute("PRAGMA integrity_check").fetchone()[0]
        gates.append(("PRAGMA integrity_check", ic == "ok"))
        failed = [name for name, ok in gates if not ok]
        for name, ok in gates:
            print(("PASS " if ok else "FAIL ") + name)
        if failed:
            surprise("final gate failed:", "; ".join(failed))
        print(f"Final gates passed ({len(gates)} checks).")
        print(f"Field changes this run: names {changes['name']}, "
              f"birth_info {changes['birth_info']}, death_info "
              f"{changes['death_info']}; sources created: "
              f"{len(sources_created)}; register entries: "
              f"{len(register_entries)}.")

        # --- write the register, then commit ---
        if register_entries:
            existing = []
            if register_before:
                existing = json.loads(register_before.decode("utf-8"))
            with open(REGISTER_PATH, "w", encoding="utf-8") as fh:
                json.dump(existing + register_entries, fh, indent=1,
                          ensure_ascii=False)
            print(f"Register updated: {REGISTER_PATH} "
                  f"(+{len(register_entries)} entries).")
        con.commit()
        print("COMMITTED.")
    except SystemExit as e:
        con.rollback()
        if register_before is None:
            if os.path.exists(REGISTER_PATH):
                os.remove(REGISTER_PATH)
        else:
            with open(REGISTER_PATH, "wb") as fh:
                fh.write(register_before)
        if e.code != 3:
            raise
        print("ROLLED BACK, nothing changed.")
        sys.exit(3)
    except Exception as e:
        con.rollback()
        if register_before is None:
            if os.path.exists(REGISTER_PATH):
                os.remove(REGISTER_PATH)
        else:
            with open(REGISTER_PATH, "wb") as fh:
                fh.write(register_before)
        print("ERROR, rolled back:", e); sys.exit(4)


if __name__ == "__main__":
    main()
