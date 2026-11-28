#!/usr/bin/env python3
"""Simulation harness for the ep8-davis-corrections package.

Builds a full-scale mock of the live database (3,807 persons /
2,693 sources with fillers) carrying the audited pre-state of
profiles 8192 and 8159, with the live constraints in place
(persons.name UNIQUE; unified_photo_catalog NOT NULL on
normalized_filename, original_filename, local_image_path,
sha256_hash), and runs the apply script against it as a
subprocess, exactly as the live run will run.

11 tests:
 1. clean run with a reciprocal parent_of row present
 2. idempotent re-run (full DB dump equality, register unchanged)
 3. abort on a wrong armed expected_relationship_id
 4. abort when fact 7596 carries an unexpected date
 5. abort when photo 611 carries an unexpected year
 6. clean run without reciprocal, id gate armed with the right id
 7. photo year present in both catalog tables: both are fixed
 8. photo year in neither catalog table: abort
 9. fact 24332 with the 'given' value variant accepted
10. the 24333 folding guard: the new 1920 Census fact stays
    distinct and 8159 reaches 9 facts
11. audit_ep8.py smoke test against the mock

Usage: python3 test_ep8_harness.py
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
    (HERE / "ep8_davis_corrections_package.json").read_text(
        encoding="utf-8"))
APPLY = "apply_ep8_davis_corrections_package.py"
AUDIT = "audit_ep8.py"
SPEC_FILE = "ep8_davis_corrections_package.json"
REGISTER_FILE = "unassigned_evidence_register.json"

DETACH_ID = 5003
RECIPROCAL_ID = 5004
DETACH_EVIDENCE = SPEC["detach"]["primary"]["evidence_text"]
DETACH_CERTAINTY = SPEC["detach"]["primary"]["certainty"]
NOTES_8159_ORIGINAL = (
    "Buried at Harmony Cemetery, Millsboro, Sussex County, "
    "Delaware. Verified via FindAGrave Memorial 36969032. "
    "Son of Morris Davis and Hester A. Morris Davis.")

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


def build_mock(db_path, *, with_reciprocal=True,
               death_7596="1 Feb 1932", photo_mode="both",
               value_24332="Interred in historical Delmarva "
                           "cemetery"):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript(SCHEMA)
    p8159 = SPEC["persons"]["8159"]

    explicit_persons = [
        (8192, "Ethel Gwendolyn Clark",
         "15 Nov 1918 Milton, Sussex, Delaware, USA",
         "25 Feb 1997 Beebe Medical Center, Lewes, Sussex, "
         "Delaware, USA", ""),
        (8159, "Harry Edward Davis", p8159["birth_info_from"],
         p8159["death_info_from"], NOTES_8159_ORIGINAL),
        (8193, "John Wesley Clark Jr", "13 May 1894",
         "5 Oct 1964", ""),
        (8194, "Lulu Rae Clark", "abt 1895", "1988", ""),
        (3591, "John Clark", "unknown", "1918", ""),
        (8248, "Sheila Kathleen Davis", "9 Feb 1939",
         "5 Aug 2010", ""),
        (12006, "Morris Davis", "1858", "1916", ""),
        (11247, "Hester A. Morris Davis", "1877", "1944", ""),
        (3000, "Filler Anchor Person", "", "", ""),
    ]
    for pid, name, b, d, notes in explicit_persons:
        cur.execute(
            "INSERT INTO persons (person_id, name, birth_info, "
            "death_info, notes, evidence_level) VALUES "
            "(?, ?, ?, ?, ?, 3)", (pid, name, b, d, notes))
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
        667: "mitsawokett_obits", 860: "Delaware Federal Census",
        1274: "cemetery_survey",
        1281: "social_security_administration",
        2698: "familysearch", 2699: "familysearch",
        622: "gedcom", 859: "census", 862: "census",
        991: "findagrave", 1270: "vital_records",
    }
    for sid, ds in explicit_sources.items():
        cur.execute(
            "INSERT INTO sources (source_id, title, url, dataset) "
            "VALUES (?, ?, '', ?)", (sid, f"Reference Source {sid}",
                                     ds))
    skip = set(range(2000, 2020))
    for sid in range(1, 2714):
        if sid in explicit_sources or sid in skip:
            continue
        cur.execute(
            "INSERT INTO sources (source_id, title, url, dataset) "
            "VALUES (?, ?, '', 'filler')",
            (sid, f"Filler Source {sid}"))
    total_sources = cur.execute(
        "SELECT COUNT(*) FROM sources").fetchone()[0]
    assert total_sources == SPEC["expected_pre_state"]["sources"], \
        total_sources

    edit24332 = [e for e in SPEC["fact_edits"]
                 if e["fact_id"] == 24332][0]
    facts = [
        (7654, 8192, "Name", None, None, None),
        (7655, 8192, "Birth",
         "15 Nov 1918 Milton, Sussex, Delaware, USA", None, None),
        (7656, 8192, "Death",
         "25 Feb 1997 Beebe Medical Center, Lewes, Sussex, "
         "Delaware, USA", None, None),
        (16060, 8192, "Census", "1930",
         "Milton, Sussex County, Delaware",
         "1930 Census: John Clark head 37, Lulu wife 35, "
         "Ethel 12, Carlisie 11, Millie 10, Wilfred 9, Arlie 4 "
         "(Milton, Sussex, Delaware)."),
        (24386, 8192, "Social Security Application", "1918",
         "United States", None),
        (24387, 8192, "Marriage", None, "Delaware",
         "Marriage record documented for Ethel Gwendolyn Clark"),
        (7594, 8159, "Name", None, None, None),
        (7595, 8159, "Birth", "unknown", None, None),
        (7596, 8159, "Death", death_7596, None, None),
        (24332, 8159, "Burial",
         edit24332["guard"]["date_string"][0],
         "Delmarva", value_24332),
        (24333, 8159, "Census", "1920", None,
         "Census record documented for Harry Edward Davis"),
        (24334, 8159, "Social Security Application", "1916",
         "United States", None),
        (24335, 8159, "Marriage", None, "Delaware",
         "Marriage record documented for Harry Edward Davis"),
    ]
    cur.executemany(
        "INSERT INTO facts (fact_id, person_id, fact_type, "
        "date_string, place_string, value_string) VALUES "
        "(?, ?, ?, ?, ?, ?)", facts)

    citations = [
        (7649, 7655, 622, "GEDCOM import citation."),
        (30244, 7655, 1270, "Vital record documented."),
        (7650, 7656, 622, "GEDCOM import citation."),
        (30245, 7656, 1270, "Vital record documented."),
        (14870, 16060, 860, "1930 US Federal Census household "
                            "of John Clark, Milton."),
        (30246, 16060, 859, "1920 census boilerplate."),
        (30247, 16060, 862, "1950 census boilerplate."),
        (30248, 24386, 1281, "Social Security record documented."),
        (30249, 24387, 1270, "Marriage record documented."),
        (7589, 7595, 622, "GEDCOM import citation."),
        (30134, 7595, 1270, "Birth record documented (b. 1916)."),
        (7590, 7596, 622, "GEDCOM import citation."),
        (30135, 7596, 1270, "Death record documented (d. 1999)."),
        (30136, 24332, 1274, "Burial record documented."),
        (30137, 24333, 859, "1920 census boilerplate."),
        (30138, 24333, 862, "1950 census boilerplate."),
        (30139, 24334, 1281, "Social Security record documented."),
        (30140, 24335, 1270, "Marriage record documented."),
    ]
    cur.executemany(
        "INSERT INTO citations (citation_id, fact_id, source_id, "
        "evidence_text) VALUES (?, ?, ?, ?)", citations)

    rels = [
        (5001, 8192, 8193, "child_of", DETACH_EVIDENCE,
         DETACH_CERTAINTY),
        (5002, 8192, 8194, "child_of", DETACH_EVIDENCE,
         DETACH_CERTAINTY),
        (DETACH_ID, 8192, 3591, "child_of", DETACH_EVIDENCE,
         DETACH_CERTAINTY),
        (5005, 8192, 8159, "spouse", "", ""),
        (5006, 8159, 8192, "spouse", "", ""),
        (5007, 8248, 8192, "child_of", "", ""),
        (5008, 8192, 3000, "cross_dataset_match",
         "Cross-dataset identity link.", ""),
        (5010, 8159, 12006, "child_of", "", ""),
        (5011, 8159, 11247, "child_of", "", ""),
        (5012, 8248, 8159, "child_of", "", ""),
    ]
    if with_reciprocal:
        rels.append((RECIPROCAL_ID, 3591, 8192, "parent_of",
                     "Reciprocal of child_of row.",
                     DETACH_CERTAINTY))
    cur.executemany(
        "INSERT INTO relationships (id, person_a_id, person_b_id, "
        "relationship_type, evidence_text, certainty) VALUES "
        "(?, ?, ?, ?, ?, ?)", rels)

    def upc(photo_id, person_id, fname, year, dates):
        cur.execute(
            "INSERT INTO unified_photo_catalog (photo_id, "
            "title_or_caption, normalized_filename, "
            "original_filename, local_image_path, sha256_hash, "
            "approximate_year, dates_mentioned, primary_person_id, "
            "dataset_source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "'mitsawokett')",
            (photo_id, fname, fname, fname,
             f"assets/archive_media/people/{fname}", "a" * 64,
             year, dates, person_id))

    def pc(photo_id, fname, year, dates):
        cur.execute(
            "INSERT INTO photo_catalog (photo_id, "
            "title_or_caption, approximate_year, dates_mentioned) "
            "VALUES (?, ?, ?, ?)", (photo_id, fname, year, dates))

    y611 = SPEC["photo_fix"]["pre"]["approximate_year"]
    d611 = SPEC["photo_fix"]["pre"]["dates_mentioned"]
    upc(617, 8159, "Davis_Harry_E.jpg", "1916", "[\"1916\"]")
    pc(617, "Davis_Harry_E.jpg", "1916", "[\"1916\"]")
    if photo_mode in ("both", "unified_only"):
        upc(611, 8192, "Davis_Ethel_Gwendolyn.jpg", y611, d611)
    if photo_mode == "both":
        pc(611, "Davis_Ethel_Gwendolyn.jpg", y611, d611)
    if photo_mode == "bad_year":
        upc(611, 8192, "Davis_Ethel_Gwendolyn.jpg", "1920",
            "[\"1920\"]")
    cur.executemany(
        "INSERT INTO person_photos (id, person_id, photo_id, "
        "confidence_score, is_primary) VALUES (?, ?, ?, 1.0, 1)",
        [(1, 8192, 611), (2, 8159, 617)])
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


def test1_clean_with_reciprocal(tmp):
    t = "1 clean run with reciprocal"
    pkg, db = scenario(tmp)
    pre617u = query(db, "SELECT * FROM unified_photo_catalog "
                        "WHERE photo_id = 617")
    pre617p = query(db, "SELECT * FROM photo_catalog "
                        "WHERE photo_id = 617")
    r = run_script(pkg, APPLY, db)
    check(t, "exit 0", r.returncode == 0, r.stdout + r.stderr)
    check(t, "COMMITTED printed", "COMMITTED." in r.stdout)
    check(t, "persons 3807",
          query(db, "SELECT COUNT(*) FROM persons")[0][0] == 3807)
    check(t, "sources 2701",
          query(db, "SELECT COUNT(*) FROM sources")[0][0] == 2701)
    new_ids = {row[1]: row[0] for row in query(
        db, "SELECT source_id, title FROM sources "
            "WHERE source_id > 2713")}
    expect = {s["title"]: 2714 + i
              for i, s in enumerate(SPEC["new_sources"])}
    check(t, "new source ids 2714-2721 in spec order",
          new_ids == expect, f"{new_ids} vs {expect}")
    check(t, "facts 8192 = 8",
          query(db, "SELECT COUNT(*) FROM facts "
                    "WHERE person_id = 8192")[0][0] == 8)
    check(t, "facts 8159 = 9",
          query(db, "SELECT COUNT(*) FROM facts "
                    "WHERE person_id = 8159")[0][0] == 9)
    f = query(db, "SELECT date_string, place_string, value_string "
                  "FROM facts WHERE fact_id = 24387")[0]
    edit = [e for e in SPEC["fact_edits"]
            if e["fact_id"] == 24387][0]
    check(t, "fact 24387 corrected",
          f[0] == "8 Apr 1938" and f[1] == ""
          and f[2] == edit["set"]["value_string"])
    cits = {row[0] for row in query(
        db, "SELECT source_id FROM citations WHERE fact_id = 24387")}
    check(t, "fact 24387 citations (program + bride index)",
          {expect[SPEC['new_sources'][0]['title']],
           expect[SPEC['new_sources'][6]['title']]} <= cits)
    check(t, "fact 7596 = 31 Jan 1999",
          query(db, "SELECT date_string FROM facts "
                    "WHERE fact_id = 7596")[0][0] == "31 Jan 1999")
    check(t, "detach rows gone",
          query(db, "SELECT COUNT(*) FROM relationships "
                    "WHERE id IN (5003, 5004)")[0][0] == 0)
    check(t, "cross_dataset_match row 5008 untouched",
          query(db, "SELECT COUNT(*) FROM relationships "
                    "WHERE id = 5008")[0][0] == 1)
    reg = json.loads((pkg / REGISTER_FILE).read_text(
        encoding="utf-8"))
    entries = reg["detached_relationships"]
    check(t, "register holds the primary row",
          len(entries) == 1 and entries[0]["id"] == DETACH_ID)
    check(t, "register holds the reciprocal row",
          entries and entries[0].get("reciprocal_row", {})
          .get("id") == RECIPROCAL_ID)
    check(t, "register reason matches spec",
          entries and entries[0].get("reason")
          == SPEC["detach"]["reason"])
    n8192 = query(db, "SELECT notes FROM persons "
                      "WHERE person_id = 8192")[0][0]
    check(t, "8192 notes = the append text alone (was empty)",
          n8192 == SPEC["notes_appends"][0]["text"])
    n8159 = query(db, "SELECT notes FROM persons "
                      "WHERE person_id = 8159")[0][0]
    check(t, "8159 notes appended, original preserved",
          n8159.startswith(NOTES_8159_ORIGINAL)
          and SPEC["notes_appends"][1]["marker"] in n8159)
    for table in ("unified_photo_catalog", "photo_catalog"):
        row = query(db, f"SELECT approximate_year, "
                        f"dates_mentioned FROM {table} "
                        f"WHERE photo_id = 611")[0]
        check(t, f"{table}: photo 611 corrected",
              tuple(row) == ("unknown", "[]"))
    check(t, "photo 617 unchanged (unified)",
          query(db, "SELECT * FROM unified_photo_catalog "
                    "WHERE photo_id = 617") == pre617u)
    check(t, "photo 617 unchanged (photo_catalog)",
          query(db, "SELECT * FROM photo_catalog "
                    "WHERE photo_id = 617") == pre617p)
    prow = query(db, "SELECT birth_info, death_info FROM persons "
                     "WHERE person_id = 8159")[0]
    check(t, "8159 person row corrected",
          prow == (SPEC["persons"]["8159"]["birth_info_to"],
                   SPEC["persons"]["8159"]["death_info_to"]))
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


def test3_wrong_armed_id(tmp):
    t = "3 abort on wrong expected_relationship_id"
    pkg = fresh_pkg(
        tmp, lambda d: d["detach"].update(
            expected_relationship_id=424242))
    db = Path(tmp) / "mock.db"
    build_mock(db)
    before = dump(db)
    r = run_script(pkg, APPLY, db)
    check(t, "exit 3", r.returncode == 3, r.stdout + r.stderr)
    check(t, "DB unchanged", dump(db) == before)


def test4_bad_death_date(tmp):
    t = "4 abort on fact 7596 = '5 May 1945'"
    pkg, db = scenario(tmp, death_7596="5 May 1945")
    before = dump(db)
    r = run_script(pkg, APPLY, db)
    check(t, "exit 3", r.returncode == 3, r.stdout + r.stderr)
    check(t, "DB unchanged", dump(db) == before)


def test5_bad_photo_year(tmp):
    t = "5 abort on photo year '1920'"
    pkg, db = scenario(tmp, photo_mode="bad_year")
    before = dump(db)
    r = run_script(pkg, APPLY, db)
    check(t, "exit 3", r.returncode == 3, r.stdout + r.stderr)
    check(t, "DB unchanged", dump(db) == before)


def test6_no_reciprocal_armed(tmp):
    t = "6 clean run without reciprocal, id gate armed"
    pkg = fresh_pkg(
        tmp, lambda d: d["detach"].update(
            expected_relationship_id=DETACH_ID))
    db = Path(tmp) / "mock.db"
    build_mock(db, with_reciprocal=False)
    r = run_script(pkg, APPLY, db)
    check(t, "exit 0", r.returncode == 0, r.stdout + r.stderr)
    check(t, "primary row gone",
          query(db, "SELECT COUNT(*) FROM relationships "
                    "WHERE id = 5003")[0][0] == 0)
    reg = json.loads((pkg / REGISTER_FILE).read_text(
        encoding="utf-8"))
    entries = reg["detached_relationships"]
    check(t, "register entry has no reciprocal_row",
          len(entries) == 1 and "reciprocal_row" not in entries[0])


def test7_both_photo_tables(tmp):
    t = "7 photo year in both tables: both fixed"
    pkg, db = scenario(tmp, with_reciprocal=False,
                       photo_mode="both")
    r = run_script(pkg, APPLY, db)
    check(t, "exit 0", r.returncode == 0, r.stdout + r.stderr)
    for table in ("unified_photo_catalog", "photo_catalog"):
        row = query(db, f"SELECT approximate_year, "
                        f"dates_mentioned FROM {table} "
                        f"WHERE photo_id = 611")[0]
        check(t, f"{table}: photo 611 corrected",
              tuple(row) == ("unknown", "[]"))


def test8_photo_neither(tmp):
    t = "8 photo year in neither table: abort"
    pkg, db = scenario(tmp, photo_mode="neither")
    before = dump(db)
    r = run_script(pkg, APPLY, db)
    check(t, "exit 3", r.returncode == 3, r.stdout + r.stderr)
    check(t, "DB unchanged", dump(db) == before)


def test9_value_variant(tmp):
    t = "9 fact 24332 'given' value variant accepted"
    pkg, db = scenario(
        tmp, value_24332="Burial record documented for "
                         "Harry Edward Davis")
    r = run_script(pkg, APPLY, db)
    check(t, "exit 0", r.returncode == 0, r.stdout + r.stderr)
    edit = [e for e in SPEC["fact_edits"]
            if e["fact_id"] == 24332][0]
    row = query(db, "SELECT date_string, place_string, "
                    "value_string FROM facts "
                    "WHERE fact_id = 24332")[0]
    check(t, "fact 24332 in post-state",
          tuple(row) == (edit["set"]["date_string"],
                         edit["set"]["place_string"],
                         edit["set"]["value_string"]))


def test10_folding_guard(tmp):
    t = "10 the 24333 folding guard"
    pkg, db = scenario(tmp)
    r = run_script(pkg, APPLY, db)
    check(t, "exit 0", r.returncode == 0, r.stdout + r.stderr)
    rows = query(db, "SELECT fact_id, value_string FROM facts "
                     "WHERE person_id = 8159 "
                     "AND fact_type = 'Census' "
                     "AND date_string = '1920' ORDER BY fact_id")
    check(t, "two distinct Census 1920 facts on 8159",
          len(rows) == 2 and rows[0][0] == 24333
          and rows[1][0] != 24333)
    check(t, "fact 24333 value untouched",
          rows[0][1] == "Census record documented for "
                        "Harry Edward Davis")
    check(t, "8159 reaches 9 facts",
          query(db, "SELECT COUNT(*) FROM facts "
                    "WHERE person_id = 8159")[0][0] == 9)


def test11_audit_smoke(tmp):
    t = "11 audit_ep8.py smoke test"
    pkg = fresh_pkg(tmp)
    db = Path(tmp) / "mock.db"
    build_mock(db)
    r = run_script(pkg, AUDIT, db)
    check(t, "exit 0", r.returncode == 0, r.stdout + r.stderr)
    check(t, "prints the detach row id",
          f"DETACH child_of row id (8192 -> 3591): {DETACH_ID}"
          in r.stdout)
    check(t, "dumps PRAGMA table_info",
          "PRAGMA table_info(persons)" in r.stdout
          and "PRAGMA table_info(unified_photo_catalog)"
          in r.stdout)
    check(t, "prints reference datasets",
          "mitsawokett_obits" in r.stdout
          and "social_security_administration" in r.stdout)


def main():
    root = Path(tempfile.mkdtemp(prefix="ep8-harness-"))
    print(f"Harness workspace: {root}")
    pkg1, db1 = test1_clean_with_reciprocal(root / "t1")
    test2_idempotent_rerun(root / "t1", pkg1, db1)
    test3_wrong_armed_id(root / "t3")
    test4_bad_death_date(root / "t4")
    test5_bad_photo_year(root / "t5")
    test6_no_reciprocal_armed(root / "t6")
    test7_both_photo_tables(root / "t7")
    test8_photo_neither(root / "t8")
    test9_value_variant(root / "t9")
    test10_folding_guard(root / "t10")
    test11_audit_smoke(root / "t11")
    failed = [r for r in RESULTS if not r[2]]
    print()
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} checks "
          f"passed across 11 tests.")
    if failed:
        print("FAILURES:")
        for test, label, _ in failed:
            print(f"  {test}: {label}")
        return 1
    print("ALL 11 TESTS PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
