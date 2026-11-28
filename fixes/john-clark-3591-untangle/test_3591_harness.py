#!/usr/bin/env python3
"""Simulation harness for the john-clark-3591-untangle package.

Builds a full-scale mock of the live database (3,807 persons /
2,693 sources with fillers) carrying the audited pre-state of
profiles 3591, 8193, 8194 and the Clark children, with the live
constraints in place (persons.name UNIQUE;
unified_photo_catalog NOT NULL on normalized_filename,
original_filename, local_image_path, sha256_hash), in the
POST-Ep8 state (no relationship rows between 8192 and 3591:
the ep8-davis-corrections package runs first), and runs the
apply script against it as a subprocess, exactly as the live
run will run.

8 tests:
 1. clean run: reciprocal spouse pair; children with and
    without stored parent_of reciprocals; a cross_dataset_match
    row touching 3591 is left in place and does not abort
 2. idempotent re-run (full DB dump equality, register
    unchanged)
 3. abort when an 8192 -> 3591 row is still present (the Ep8
    dependency gate)
 4. abort when fact 11986 carries an unexpected date ('1900')
 5. abort on an unexpected relationship type between 3591 and
    a child (a 'sibling' row)
 6. single-spouse-row variant (forward row only)
 7. single-spouse-row variant (reverse row only)
 8. audit_3591.py smoke test against the mock

Usage: python3 test_3591_harness.py
Exit code 0 only when every test passes.
"""
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = json.loads(
    (HERE / "john_clark_3591_untangle_package.json").read_text(
        encoding="utf-8"))
APPLY = "apply_john_clark_3591_untangle_package.py"
AUDIT = "audit_3591.py"
SPEC_FILE = "john_clark_3591_untangle_package.json"
REGISTER_FILE = "unassigned_evidence_register.json"

TARGET = 3591
SPOUSE_EVIDENCE = ("Confirmed in 1930 US Federal Census household "
                   "(Milton, Sussex, Delaware, USA)")
DAUGHTER_EVIDENCE = ("Confirmed in 1930 US Federal Census as "
                     "Daughter of household head (Milton, Sussex, "
                     "Delaware, USA)")
SON_EVIDENCE = ("Confirmed in 1930 US Federal Census as Son of "
                "household head (Milton, Sussex, Delaware, USA)")
GEDCOM_EVIDENCE = "GEDCOM Family tree linkage"
CENSUS_1930_VALUE = (
    "1930 US Federal Census: Head, age 37. Household: John Clark "
    "(Head, age 37), Lulu Clark (Wife, age 35), Ethel Clark "
    "(Daughter, age 12), Carlisie Clark (Daughter, age 11), "
    "Millie Clark (Daughter, age 10), Wilfred Clark (Son, age "
    "9), Arlie Clark (Son, age 4)")
CIT_14868 = ("1930 United States Federal Census, Delaware, "
             "Milton, Sussex, Delaware, USA. Dwelling record "
             "#121401511")
DEATH_VALUE_POST = SPEC["fact_edits"][0]["set"]["value_string"]
NOTES_POST = SPEC["target_person"]["post"]["notes"]

SCHEMA = """
CREATE TABLE persons (
    person_id INTEGER PRIMARY KEY, name TEXT UNIQUE,
    source_page TEXT, birth_info TEXT, death_info TEXT,
    notes TEXT, dataset_source TEXT, first_name TEXT,
    middle_name TEXT, maiden_name TEXT, married_last_name TEXT,
    evidence_level INTEGER, suffix TEXT);
CREATE TABLE relationships (
    id INTEGER PRIMARY KEY, person_a_id INTEGER,
    person_b_id INTEGER, relationship_type TEXT,
    evidence_text TEXT, certainty TEXT);
CREATE TABLE facts (
    fact_id INTEGER PRIMARY KEY, person_id INTEGER,
    fact_type TEXT, date_string TEXT, place_string TEXT,
    value_string TEXT, place_id INTEGER);
CREATE TABLE citations (
    citation_id INTEGER PRIMARY KEY, fact_id INTEGER,
    source_id INTEGER, evidence_text TEXT);
CREATE TABLE sources (
    source_id INTEGER PRIMARY KEY, title TEXT, url TEXT,
    dataset TEXT);
CREATE TABLE fact_quality_flags (
    fact_id INTEGER PRIMARY KEY, flag TEXT, note TEXT,
    applied_at TEXT);
CREATE TABLE person_photos (
    id INTEGER PRIMARY KEY, person_id INTEGER, photo_id INTEGER,
    confidence_score REAL, is_primary INTEGER);
CREATE TABLE unified_photo_catalog (
    photo_id INTEGER PRIMARY KEY, title_or_caption TEXT,
    normalized_filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    local_image_path TEXT NOT NULL,
    sha256_hash TEXT NOT NULL,
    approximate_year TEXT, dates_mentioned TEXT,
    primary_person_id INTEGER, dataset_source TEXT);
CREATE TABLE photo_catalog (
    photo_id INTEGER PRIMARY KEY, title_or_caption TEXT,
    approximate_year TEXT, dates_mentioned TEXT);
"""


def build_mock(db_path, *, spouse_mode="pair",
               with_8192_rows=False, death_11986="1918",
               unexpected_type=False):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript(SCHEMA)
    tp = SPEC["target_person"]

    # (person_id, name, source_page, birth_info, death_info,
    #  notes, dataset_source)
    explicit_persons = [
        (3591, "John Clark", tp["pre"]["source_page"], None,
         tp["pre"]["death_info"], tp["pre"]["notes"],
         tp["pre"]["dataset_source"]),
        (8193, "John Wesley Clark Jr", "Davis Family Tree.ged",
         "13 May 1894 Milton, Delaware, USA",
         "5 October 1964 Sussex County, Delaware, USA",
         "[Suffix 'Jr' realigned from surname field]",
         "davis_family_gedcom"),
        (8194, "Lulu Rae Clark", "Davis Family Tree.ged",
         "30 July 1897 Kent County, Delaware, USA",
         "21 November 1988 Lewes, Sussex County, Delaware, USA",
         "", "davis_family_gedcom"),
        (8192, "Ethel Gwendolyn Clark", "Davis Family Tree.ged",
         "15 Nov 1918 Milton, Sussex, Delaware, USA",
         "25 Feb 1997 Beebe Medical Center, Lewes, Sussex, "
         "Delaware, USA", "", "davis_family_gedcom"),
        (8195, "Carlisie Clark", None, None, None, "",
         "davis_family_gedcom"),
        (8210, "Millie Clark", None, None, None, "",
         "davis_family_gedcom"),
        (8196, "Wilfred Clark", None, None, None, "",
         "davis_family_gedcom"),
        (8207, "Arlie Benjamin Clark", None, None, None, "",
         "davis_family_gedcom"),
        (9350, "Levin Clark", "Davis Family Tree.ged",
         "27 Aug 1755", "1 Sep 1835", "", "davis_family_gedcom"),
        (8514, "Elizabeth Morris", "Davis Family Tree.ged",
         "1761", None, "", "davis_family_gedcom"),
        (9622, "John Wesley Clark Sr", "Davis Family Tree.ged",
         "Jan 1874 Delaware", "1963 Milton, Delaware",
         "[Suffix 'Sr' realigned from surname field]",
         "davis_family_gedcom"),
        (3000, "Filler Anchor Person", None, "", "", "", ""),
    ]
    for row in explicit_persons:
        cur.execute(
            "INSERT INTO persons (person_id, name, source_page, "
            "birth_info, death_info, notes, dataset_source, "
            "evidence_level) VALUES (?, ?, ?, ?, ?, ?, ?, 3)",
            row)
    explicit_ids = {p[0] for p in explicit_persons}
    n = cur.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    cand = 1
    while n < SPEC["expected_pre_state"]["persons"]:
        if cand not in explicit_ids:
            cur.execute(
                "INSERT INTO persons (person_id, name, "
                "evidence_level) VALUES (?, ?, 1)",
                (cand, f"Filler Person {cand}"))
            n += 1
        cand += 1

    explicit_sources = {
        136: "mitsawokett_primary", 197: "mitsawokett_delaware",
        622: "gedcom", 836: "mitsawokett_primary",
        837: "mitsawokett_primary", 853: "census", 858: "census",
        860: "Delaware Federal Census", 861: "Delaware Federal "
        "Census", 1270: "vital_records",
        1281: "social_security_administration",
    }
    for sid, ds in explicit_sources.items():
        cur.execute(
            "INSERT INTO sources (source_id, title, url, dataset) "
            "VALUES (?, ?, '', ?)", (sid, f"Reference Source {sid}",
                                     ds))
    sid = 1
    total = cur.execute(
        "SELECT COUNT(*) FROM sources").fetchone()[0]
    while total < 2693:
        if sid not in explicit_sources:
            cur.execute(
                "INSERT INTO sources (source_id, title, url, "
                "dataset) VALUES (?, ?, '', 'filler')",
                (sid, f"Filler Source {sid}"))
            total += 1
        sid += 1

    facts = [
        (2967, 3591, "Name", None, None, "John Clark"),
        (11986, 3591, "Death", death_11986, None, "d. 1918"),
        (15220, 3591, "Document Mention", None,
         "Delmarva Peninsula", "Documented in primary record: "
         "Tax Lists"),
        (15255, 3591, "Document Mention", None,
         "Delmarva Peninsula", "Documented in primary record: "
         "Tax Lists"),
        (15454, 3591, "Document Mention", None,
         "Delmarva Peninsula", "Documented in primary record: "
         "Mitsawokett: A 17th Century Native American Community "
         "in Central Delaware"),
        (16058, 3591, "Census", "1930",
         "Milton, Sussex County, Delaware", CENSUS_1930_VALUE),
        (19493, 3591, "Marriage", None, "Delaware",
         "Marriage record documented for John Clark"),
        (7657, 8193, "Name", None, None, "John Wesley Clark Jr"),
        (7658, 8193, "Birth", "13 May 1894 Milton, Delaware, "
         "USA", None, None),
        (7659, 8193, "Death", "5 October 1964 Sussex County, "
         "Delaware, USA", None, None),
        (15224, 8193, "Document Mention", None,
         "Delmarva Peninsula", "Documented in primary record: "
         "Tax Lists"),
        (15258, 8193, "Document Mention", None,
         "Delmarva Peninsula", "Documented in primary record: "
         "Tax Lists"),
        (15455, 8193, "Document Mention", None,
         "Delmarva Peninsula", "Documented in primary record: "
         "Mitsawokett: A 17th Century Native American Community "
         "in Central Delaware"),
        (16097, 8193, "Census", "1940",
         "Milton, Sussex County, Delaware",
         "1940 US Federal Census: Head, age 46."),
        (24388, 8193, "Social Security Application", "1894",
         "United States", "Social Security Account Application "
         "(Form SS-5) on file for John Wesley Clark Jr"),
        (24389, 8193, "Marriage", None, "Delaware",
         "Marriage record documented for John Wesley Clark Jr"),
    ]
    cur.executemany(
        "INSERT INTO facts (fact_id, person_id, fact_type, "
        "date_string, place_string, value_string) VALUES "
        "(?, ?, ?, ?, ?, ?)", facts)

    citations = [
        (2961, 2967, 197, None),
        (15696, 11986, 197, "Archival assertion: d. 1918 (1918) "
                            "documented in primary lineage "
                            "manifest."),
        (21976, 11986, 1270, "Bureau of Vital Statistics, "
                             "Certificate and Return of Death; "
                             "Official vital registration "
                             "recording John Clark, deceased "
                             "1918."),
        (14022, 15220, 836, "...Hundred Geo Wright ...left the "
                            "place 1795 Tax List for Broadkill "
                            "Hundred, Sussex Co., DE Miers "
                            "Clark.............5 John "
                            "Clark..............5"),
        (14057, 15255, 837, "...Wm. "
                            "Prettiman.........................."
                            "1 1682 Titheables Robert "
                            "Burton..........................1 "
                            "John Clark.........................."
                            "...1"),
        (14256, 15454, 136, "...served under the command of Col. "
                            "David Hall. His children living in "
                            "1834 were: Whittington [various "
                            "spellings] Clark John Clark "
                            "Nathaniel Clark Comfort Miller "
                            "Elizabeth Rigware Levina Harmon"),
        (14868, 16058, 860, CIT_14868),
        (21977, 16058, 853, "1850 United States Federal Census "
                            "Schedule; Population schedule "
                            "enumeration record for John Clark in "
                            "Delmarva."),
        (21978, 16058, 858, "1910 United States Federal Census "
                            "Schedule; Population schedule "
                            "enumeration record for John Clark in "
                            "Delmarva."),
        (21979, 19493, 1270, "Delaware County Marriage Records, "
                             "Bonds and Licenses; Marriage record "
                             "on file for John Clark."),
        (7651, 7657, 622, None),
        (7652, 7658, 622, None),
        (7653, 7659, 622, None),
        (14907, 16097, 861, "1940 United States Federal Census, "
                            "Delaware, Milton, Sussex, Delaware. "
                            "Dwelling record #262160"),
        (30255, 24389, 1270, "Delaware County Marriage Records, "
                             "Bonds and Licenses; Marriage record "
                             "on file for John Wesley Clark Jr."),
    ]
    cur.executemany(
        "INSERT INTO citations (citation_id, fact_id, source_id, "
        "evidence_text) VALUES (?, ?, ?, ?)", citations)

    rels = [
        (6001, 3591, 9350, "child_of", GEDCOM_EVIDENCE,
         "confirmed"),
        (6002, 3591, 8514, "child_of", GEDCOM_EVIDENCE,
         "confirmed"),
        (6020, 8195, 3591, "child_of", DAUGHTER_EVIDENCE,
         "census_confirmed"),
        (6021, 3591, 8195, "parent_of",
         "Reciprocal of child_of row.", "census_confirmed"),
        (6030, 8210, 3591, "child_of", DAUGHTER_EVIDENCE,
         "census_confirmed"),
        (6040, 8196, 3591, "child_of", SON_EVIDENCE,
         "census_confirmed"),
        (6041, 3591, 8196, "parent_of",
         "Reciprocal of child_of row.", "census_confirmed"),
        (6050, 8207, 3591, "child_of", SON_EVIDENCE,
         "census_confirmed"),
        (6060, 8193, 9622, "child_of", GEDCOM_EVIDENCE,
         "confirmed"),
        (6061, 8193, 8194, "spouse",
         "Confirmed in 1940 US Federal Census household "
         "(Milton, Sussex, Delaware)", "census_confirmed"),
        (6062, 8192, 8193, "child_of", GEDCOM_EVIDENCE,
         "confirmed"),
        (6064, 8195, 8193, "child_of", GEDCOM_EVIDENCE,
         "confirmed"),
        (6070, 3591, 3000, "cross_dataset_match",
         "Cross-dataset identity link.", ""),
    ]
    if spouse_mode in ("pair", "single_forward"):
        rels.append((6010, 3591, 8194, "spouse", SPOUSE_EVIDENCE,
                     "census_confirmed"))
    if spouse_mode in ("pair", "single_reverse"):
        rels.append((6011, 8194, 3591, "spouse", SPOUSE_EVIDENCE,
                     "census_confirmed"))
    if with_8192_rows:
        rels.append((6080, 8192, 3591, "child_of",
                     DAUGHTER_EVIDENCE, "census_confirmed"))
        rels.append((6081, 3591, 8192, "parent_of",
                     "Reciprocal of child_of row.",
                     "census_confirmed"))
    if unexpected_type:
        rels.append((6090, 3591, 8196, "sibling", "", ""))
    cur.executemany(
        "INSERT INTO relationships (id, person_a_id, person_b_id, "
        "relationship_type, evidence_text, certainty) VALUES "
        "(?, ?, ?, ?, ?, ?)", rels)
    con.commit()
    con.close()


def fresh_pkg(tmp, spec_mutator=None):
    pkg = Path(tmp) / "pkg"
    pkg.mkdir(parents=True)
    for name in (APPLY, AUDIT, SPEC_FILE, REGISTER_FILE):
        shutil.copy2(HERE / name, pkg / name)
    if spec_mutator:
        p = pkg / SPEC_FILE
        data = json.loads(p.read_text(encoding="utf-8"))
        spec_mutator(data)
        p.write_text(json.dumps(data, indent=2, sort_keys=True),
                     encoding="utf-8")
    return pkg


def run_script(pkg, script, db):
    return subprocess.run(
        [sys.executable, str(pkg / script), str(db)],
        capture_output=True, text=True, timeout=300)


def dump(db):
    con = sqlite3.connect(db)
    out = "\n".join(con.iterdump())
    con.close()
    return out


def query(db, sql, args=()):
    con = sqlite3.connect(db)
    rows = con.execute(sql, args).fetchall()
    con.close()
    return rows


RESULTS = []


def check(test, label, ok, detail=""):
    RESULTS.append((test, label, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not ok else ""))


def scenario(tmp, **mock_kw):
    pkg = fresh_pkg(tmp)
    db = Path(tmp) / "mock.db"
    build_mock(db, **mock_kw)
    return pkg, db


DELETED_IDS = (6010, 6011, 6020, 6021, 6030, 6040, 6041, 6050)
KEPT_IDS = (6001, 6002, 6060, 6061, 6062, 6064, 6070)


def test1_clean(tmp):
    t = "1 clean run (reciprocal spouse, mixed child reciprocals)"
    pkg, db = scenario(tmp)
    r = run_script(pkg, APPLY, db)
    check(t, "exit 0", r.returncode == 0, r.stdout + r.stderr)
    check(t, "COMMITTED printed", "COMMITTED." in r.stdout)
    check(t, "persons 3807",
          query(db, "SELECT COUNT(*) FROM persons")[0][0] == 3807)
    check(t, "sources unchanged (2693)",
          query(db, "SELECT COUNT(*) FROM sources")[0][0] == 2693)
    check(t, "facts on 3591 = {2967, 11986, 15454}",
          sorted(row[0] for row in query(
              db, "SELECT fact_id FROM facts WHERE person_id = "
                  "3591")) == [2967, 11986, 15454])
    check(t, "facts on 8193 = 10 incl. moved 16058",
          sorted(row[0] for row in query(
              db, "SELECT fact_id FROM facts WHERE person_id = "
                  "8193")) == sorted(
              SPEC["person_8193"]["facts_pre"] + [16058]))
    f = query(db, "SELECT date_string, value_string FROM facts "
                  "WHERE fact_id = 11986")[0]
    check(t, "fact 11986 corrected to 1834",
          f == ("1834", DEATH_VALUE_POST))
    check(t, "fact 16058 on 8193",
          query(db, "SELECT person_id FROM facts WHERE "
                    "fact_id = 16058")[0][0] == 8193)
    for cid in (21977, 21978, 15696, 21976):
        txt = query(db, "SELECT evidence_text FROM citations "
                        "WHERE citation_id = ?", (cid,))[0][0]
        check(t, f"citation {cid} marked SUPERSEDED",
              "Marked SUPERSEDED by john-clark-3591-untangle "
              "package" in txt)
    check(t, "citation 14868 stays live, text unchanged",
          query(db, "SELECT evidence_text FROM citations WHERE "
                    "citation_id = 14868")[0][0] == CIT_14868)
    for fid in (19493, 15220, 15255):
        check(t, f"fact {fid} detached (absent)",
              query(db, "SELECT COUNT(*) FROM facts WHERE "
                        "fact_id = ?", (fid,))[0][0] == 0)
    for cid in (21979, 14022, 14057):
        check(t, f"citation {cid} detached (absent)",
              query(db, "SELECT COUNT(*) FROM citations WHERE "
                        "citation_id = ?", (cid,))[0][0] == 0)
    prow = query(db, "SELECT death_info, source_page, "
                     "dataset_source, notes, birth_info FROM "
                     "persons WHERE person_id = 3591")[0]
    post = SPEC["target_person"]["post"]
    check(t, "person 3591 row in post-state",
          prow == (post["death_info"], post["source_page"],
                   post["dataset_source"], post["notes"], None))
    check(t, "deleted relationship rows gone",
          query(db, "SELECT COUNT(*) FROM relationships WHERE "
                    "id IN %s" % (DELETED_IDS,))[0][0] == 0)
    check(t, "kept relationship rows remain (incl. "
             "cross_dataset_match 6070)",
          query(db, "SELECT COUNT(*) FROM relationships WHERE "
                    "id IN %s" % (KEPT_IDS,))[0][0]
          == len(KEPT_IDS))
    reg = json.loads((pkg / REGISTER_FILE).read_text(
        encoding="utf-8"))
    rel_entries = reg["detached_relationships"]
    check(t, "register holds 5 relationship entries",
          len(rel_entries) == 5)
    by_pair = {}
    for e in rel_entries:
        pair = frozenset((e["person_a_id"], e["person_b_id"]))
        by_pair[pair] = e
    spouse = by_pair.get(frozenset((3591, 8194)), {})
    check(t, "spouse entry holds reciprocal row 6011",
          spouse.get("reciprocal_row", {}).get("id") == 6011)
    c8195 = by_pair.get(frozenset((3591, 8195)), {})
    check(t, "child 8195 entry holds reciprocal row 6021",
          c8195.get("reciprocal_row", {}).get("id") == 6021)
    c8210 = by_pair.get(frozenset((3591, 8210)), {})
    check(t, "child 8210 entry has no reciprocal_row",
          "reciprocal_row" not in c8210)
    check(t, "register holds 3 detached facts with citations",
          sorted(e["fact"]["fact_id"]
                 for e in reg["detached_facts"])
          == [15220, 15255, 19493]
          and all(e["citations"] for e in reg["detached_facts"]))
    mv = reg["moved_facts"]
    check(t, "register holds the moved fact 16058",
          len(mv) == 1 and mv[0]["fact"]["fact_id"] == 16058
          and mv[0]["from_person_id"] == 3591
          and mv[0]["to_person_id"] == 8193
          and mv[0]["superseded_citation_ids"] == [21977, 21978])
    return pkg, db


def test2_idempotent_rerun(tmp, pkg, db):
    t = "2 idempotent re-run"
    before_dump = dump(db)
    before_reg = (pkg / REGISTER_FILE).read_bytes()
    r = run_script(pkg, APPLY, db)
    check(t, "exit 0", r.returncode == 0, r.stdout + r.stderr)
    check(t, "verify-only mode reported",
          "already applied" in r.stdout)
    check(t, "DB dump identical", dump(db) == before_dump)
    check(t, "register unchanged",
          (pkg / REGISTER_FILE).read_bytes() == before_reg)


def test3_dependency_abort(tmp):
    t = "3 abort when an 8192 row is still present (Ep8 gate)"
    pkg, db = scenario(tmp, with_8192_rows=True)
    before = dump(db)
    r = run_script(pkg, APPLY, db)
    check(t, "exit 3", r.returncode == 3, r.stdout + r.stderr)
    check(t, "dependency message names the Ep8 package",
          "ep8-davis-corrections" in r.stdout)
    check(t, "DB unchanged", dump(db) == before)


def test4_bad_death(tmp):
    t = "4 abort when fact 11986 date is '1900'"
    pkg, db = scenario(tmp, death_11986="1900")
    before = dump(db)
    r = run_script(pkg, APPLY, db)
    check(t, "exit 3", r.returncode == 3, r.stdout + r.stderr)
    check(t, "DB unchanged", dump(db) == before)


def test5_unexpected_type(tmp):
    t = "5 abort on unexpected relationship type (sibling row)"
    pkg, db = scenario(tmp, unexpected_type=True)
    before = dump(db)
    r = run_script(pkg, APPLY, db)
    check(t, "exit 3", r.returncode == 3, r.stdout + r.stderr)
    check(t, "DB unchanged", dump(db) == before)


def test6_single_spouse_forward(tmp):
    t = "6 single-spouse-row variant (forward only)"
    pkg, db = scenario(tmp, spouse_mode="single_forward")
    r = run_script(pkg, APPLY, db)
    check(t, "exit 0", r.returncode == 0, r.stdout + r.stderr)
    check(t, "forward spouse row 6010 gone",
          query(db, "SELECT COUNT(*) FROM relationships WHERE "
                    "id = 6010")[0][0] == 0)
    reg = json.loads((pkg / REGISTER_FILE).read_text(
        encoding="utf-8"))
    spouse = [e for e in reg["detached_relationships"]
              if {e["person_a_id"], e["person_b_id"]}
              == {3591, 8194}]
    check(t, "spouse entry has no reciprocal_row",
          len(spouse) == 1 and "reciprocal_row" not in spouse[0])


def test7_single_spouse_reverse(tmp):
    t = "7 single-spouse-row variant (reverse only)"
    pkg, db = scenario(tmp, spouse_mode="single_reverse")
    r = run_script(pkg, APPLY, db)
    check(t, "exit 0", r.returncode == 0, r.stdout + r.stderr)
    check(t, "reverse spouse row 6011 gone",
          query(db, "SELECT COUNT(*) FROM relationships WHERE "
                    "id = 6011")[0][0] == 0)
    check(t, "facts on 3591 = 3 after the run",
          query(db, "SELECT COUNT(*) FROM facts WHERE "
                    "person_id = 3591")[0][0] == 3)


def test8_audit_smoke(tmp):
    t = "8 audit_3591.py smoke test"
    pkg = fresh_pkg(tmp)
    db = Path(tmp) / "mock.db"
    build_mock(db)
    r = run_script(pkg, AUDIT, db)
    check(t, "exit 0", r.returncode == 0, r.stdout + r.stderr)
    check(t, "prints the Ep8 dependency line (0 rows)",
          "EP8 DEPENDENCY: rows between 8192 and 3591: 0"
          in r.stdout)
    check(t, "prints WILL DELETE lines with ids",
          "WILL DELETE rel id 6010" in r.stdout
          and "WILL DELETE rel id 6050" in r.stdout)
    check(t, "full 3591 dump shows the cross_dataset_match row "
             "(left in place by design)",
          "'id': 6070" in r.stdout
          and "cross_dataset_match" in r.stdout)
    check(t, "dumps PRAGMA table_info",
          "PRAGMA table_info(persons)" in r.stdout
          and "PRAGMA table_info(relationships)" in r.stdout)
    check(t, "prints 9622 alignment (davis_family_gedcom)",
          "davis_family_gedcom" in r.stdout)


def main():
    root = Path(tempfile.mkdtemp(prefix="untangle3591-harness-"))
    print(f"Harness workspace: {root}")
    pkg1, db1 = test1_clean(root / "t1")
    test2_idempotent_rerun(root / "t1", pkg1, db1)
    test3_dependency_abort(root / "t3")
    test4_bad_death(root / "t4")
    test5_unexpected_type(root / "t5")
    test6_single_spouse_forward(root / "t6")
    test7_single_spouse_reverse(root / "t7")
    test8_audit_smoke(root / "t8")
    failed = [r for r in RESULTS if not r[2]]
    print()
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} checks "
          f"passed across 8 tests.")
    if failed:
        print("FAILURES:")
        for test, label, _ in failed:
            print(f"  {test}: {label}")
        return 1
    print("ALL 8 TESTS PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
