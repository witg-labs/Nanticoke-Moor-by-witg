#!/usr/bin/env python3
"""John H Davis (8890) three-way split package (2026-11-27).

Implements Jequan Davis's conflation ruling of 2026-11-22: profile
8890 held three men. It keeps John H. Davis (b. 3 Jan 1819, d. 19
Sep 1886) and is renamed to the punctuated name form its own kept
Name fact (8263) records, which frees the un-punctuated "John H
Davis" for the second man. The 1738-1840 man (Holy Trinity burial,
Find a Grave #137944370) becomes profile A, "John H Davis", taking
facts 8381, 8382, 8383, 24990, the Find a Grave note text, and the
two vital-record citations (31525, 31526) whose text quotes his
dates, reattached from the 1819 man's facts where they were
cross-attached. The abt 1889 son of Morris Davis becomes profile
B, "John H Davis (Son of Maurice)", taking the 1900 census fact
(15997), the two census-document photos (3462, 3482, with their
person_photos rows and unified_photo_catalog primary links), and
child_of links to Morris Davis (12006) and Hester A. Morris Davis
(11247). The 1790 and 1840 census citations (31528, 31529) sitting
on the 1900 census fact are marked SUPERSEDED in place. The
undated generic marriage fact 24991, assignable to none of the
three men, is detached to the package's unassigned-evidence
register with its citation intact; nothing is deleted outright.
Both new profiles are flagged unproven (evidence_level copied at
runtime from split-created profile 12007). The child_of link to
Joseph Henry Davis (8613) stays on 8890, untouched.

Rename order matters: persons.name is UNIQUE, so 8890 is renamed
to "John H. Davis" BEFORE profile A is created as "John H Davis".

Schema-discovering, backup-first, single transaction, idempotent,
stop-on-surprise. Gates only on what the package changes.
"""
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = json.load(open(os.path.join(
    HERE, "john_h_davis_split_package.json")))
MARKER = " [Marked SUPERSEDED by john-h-davis-split package "\
    "2026-11-27: "


def abort(msg):
    print(f"ABORT: {msg}")
    sys.exit(3)


def rows_where(cur, table, col, val):
    cur.execute(f"SELECT * FROM {table} WHERE {col} = ?", (val,))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def person_id_by_name(cur, name):
    r = cur.execute("SELECT person_id FROM persons WHERE name = ?",
                    (name,)).fetchone()
    return r[0] if r else None


def main():
    if len(sys.argv) != 3:
        print("usage: apply_john_h_davis_split_package.py "
              "<db path> <repo root>")
        return 2
    db_path, repo_root = sys.argv[1], sys.argv[2]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{db_path}.backup-{stamp}"
    shutil.copy2(db_path, backup)
    print(f"Backup written: {backup}")

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    p = SPEC["person_8890"]
    pid = p["person_id"]
    pre, post = SPEC["expected_pre_state"], SPEC["expected_post_state"]
    a_spec, b_spec = SPEC["new_profile_a"], SPEC["new_profile_b"]

    row = cur.execute("SELECT * FROM persons WHERE person_id = ?",
                      (pid,)).fetchone()
    if row is None:
        abort(f"person {pid} not found")

    b_id = person_id_by_name(cur, b_spec["name"])
    applied = b_id is not None
    expected_name = p["name_to"] if applied else p["name_from"]
    if row["name"] != expected_name:
        abort(f"person {pid} name is {row['name']!r}, "
              f"expected {expected_name!r}")
    print(f"Person verified: {pid} {row['name']}")
    a_id = person_id_by_name(cur, a_spec["name"]) if applied else None
    if applied and a_id is None:
        abort(f"profile B exists ({b_id}) but profile A "
              f"{a_spec['name']!r} not found; partial state")

    if not applied:
        n_persons = cur.execute(
            "SELECT COUNT(*) FROM persons").fetchone()[0]
        n_sources = cur.execute(
            "SELECT COUNT(*) FROM sources").fetchone()[0]
        print(f"Pre-state: persons {n_persons}, sources "
              f"{n_sources}, 8890 facts "
              f"{len(rows_where(cur, 'facts', 'person_id', pid))}.")
        if n_persons != pre["persons"]:
            abort(f"persons {n_persons} != expected {pre['persons']}")
        if n_sources != pre["sources"]:
            abort(f"sources {n_sources} != expected {pre['sources']}")
        fact_ids = {r["fact_id"] for r in rows_where(
            cur, "facts", "person_id", pid)}
        if fact_ids != set(p["facts_expected"]):
            abort(f"facts on {pid} {sorted(fact_ids)} != expected "
                  f"{p['facts_expected']}")
        for mv in SPEC["citation_moves"]:
            crow = cur.execute(
                "SELECT * FROM citations WHERE citation_id = ?",
                (mv["citation_id"],)).fetchone()
            if crow is None or crow["fact_id"] != mv["from_fact_id"]:
                abort(f"citation {mv['citation_id']} not on fact "
                      f"{mv['from_fact_id']} as expected")
        for ss in SPEC["citation_supersede"]:
            crow = cur.execute(
                "SELECT * FROM citations WHERE citation_id = ?",
                (ss["citation_id"],)).fetchone()
            if crow is None or crow["fact_id"] != ss["on_fact_id"]:
                abort(f"citation {ss['citation_id']} not on fact "
                      f"{ss['on_fact_id']} as expected")
            if "SUPERSEDED" in (crow["evidence_text"] or ""):
                abort(f"citation {ss['citation_id']} already marked")
        photo_ids = {r["photo_id"] for r in rows_where(
            cur, "person_photos", "person_id", pid)}
        if photo_ids != set(b_spec["photos_move"]):
            abort(f"person_photos on {pid} {sorted(photo_ids)} != "
                  f"expected {b_spec['photos_move']}")
        if p["remove_note_text"] not in (row["notes"] or ""):
            abort("Find a Grave note text to remove not found in "
                  f"{pid} notes")

    register = {
        "package": SPEC["package"],
        "date": SPEC["date"],
        "detached_from_person_id": pid,
        "detached_facts": [],
    }
    try:
        cur.execute("BEGIN")

        if not applied:
            donor = cur.execute(
                "SELECT evidence_level FROM persons "
                "WHERE person_id = ?",
                (a_spec["evidence_level_from_person_id"],)
            ).fetchone()
            if donor is None:
                abort("evidence_level donor profile "
                      f"{a_spec['evidence_level_from_person_id']} "
                      "not found")
            src_donor = cur.execute(
                "SELECT source_page, dataset_source FROM persons "
                "WHERE person_id = ?",
                (a_spec["copy_dataset_from_person_id"],)).fetchone()
            if src_donor is None:
                abort("dataset donor profile "
                      f"{a_spec['copy_dataset_from_person_id']} "
                      "not found")

            # Rename 8890 first: persons.name is UNIQUE and
            # profile A takes the name 8890 currently holds.
            notes = (row["notes"] or "").replace(
                p["remove_note_text"], "")
            notes = notes.strip().strip("|").strip()
            if p["note_marker"] not in notes:
                notes = ((notes + "\n\n") if notes else "") \
                    + p["note_text"]
            cur.execute(
                "UPDATE persons SET name = ?, birth_info = ?, "
                "death_info = ?, notes = ? WHERE person_id = ?",
                (p["name_to"], p["person_row_to"]["birth_info"],
                 p["person_row_to"]["death_info"], notes, pid))
            print(f"Profile {pid} renamed to {p['name_to']!r}, "
                  f"person row set to the 1819 man, Find a Grave "
                  f"note removed, split note appended.")

            for spec, label in ((a_spec, "A"), (b_spec, "B")):
                cur.execute(
                    "INSERT INTO persons (name, source_page, "
                    "birth_info, death_info, notes, dataset_source, "
                    "first_name, middle_name, evidence_level) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (spec["name"], src_donor[0], spec["birth_info"],
                     spec["death_info"], spec["notes"],
                     src_donor[1], spec["first_name"],
                     spec["middle_name"], donor[0]))
                new_id = cur.lastrowid
                if label == "A":
                    a_id = new_id
                else:
                    b_id = new_id
                print(f"New profile {label} created: {new_id} "
                      f"{spec['name']}")

            for fid in a_spec["facts_move"]:
                cur.execute(
                    "UPDATE facts SET person_id = ? WHERE fact_id = ?",
                    (a_id, fid))
            print(f"Facts moved to A ({a_id}): "
                  f"{a_spec['facts_move']}")
            for fid in b_spec["facts_move"]:
                cur.execute(
                    "UPDATE facts SET person_id = ? WHERE fact_id = ?",
                    (b_id, fid))
            print(f"Facts moved to B ({b_id}): "
                  f"{b_spec['facts_move']}")

            for mv in SPEC["citation_moves"]:
                cur.execute(
                    "UPDATE citations SET fact_id = ? "
                    "WHERE citation_id = ?",
                    (mv["to_fact_id"], mv["citation_id"]))
                print(f"Citation {mv['citation_id']} moved: fact "
                      f"{mv['from_fact_id']} -> {mv['to_fact_id']}.")

            for ss in SPEC["citation_supersede"]:
                crow = cur.execute(
                    "SELECT evidence_text FROM citations "
                    "WHERE citation_id = ?",
                    (ss["citation_id"],)).fetchone()
                text = crow[0] or ""
                if "SUPERSEDED" not in text:
                    cur.execute(
                        "UPDATE citations SET evidence_text = ? "
                        "WHERE citation_id = ?",
                        (text + MARKER + ss["reason"] + "]",
                         ss["citation_id"]))
                    print(f"Citation {ss['citation_id']} marked "
                          f"SUPERSEDED.")

            for photo_id in b_spec["photos_move"]:
                cur.execute(
                    "UPDATE person_photos SET person_id = ? "
                    "WHERE person_id = ? AND photo_id = ?",
                    (b_id, pid, photo_id))
                cur.execute(
                    "UPDATE unified_photo_catalog "
                    "SET primary_person_id = ? WHERE photo_id = ? "
                    "AND primary_person_id = ?",
                    (b_id, photo_id, pid))
            print(f"Photos moved to B ({b_id}): "
                  f"{b_spec['photos_move']} (person_photos rows "
                  f"and catalog primary links)")

            for rel in b_spec["relationships_add"]:
                found = cur.execute(
                    "SELECT COUNT(*) FROM relationships WHERE "
                    "person_a_id = ? AND person_b_id = ? AND "
                    "relationship_type = ?",
                    (b_id, rel["person_b_id"],
                     rel["relationship_type"])).fetchone()[0]
                if not found:
                    cur.execute(
                        "INSERT INTO relationships (person_a_id, "
                        "person_b_id, relationship_type, "
                        "evidence_text, certainty) VALUES "
                        "(?, ?, ?, ?, ?)",
                        (b_id, rel["person_b_id"],
                         rel["relationship_type"],
                         rel["evidence_text"], rel["certainty"]))
                    print(f"Profile B linked "
                          f"{rel['relationship_type']} "
                          f"{rel['person_b_id']}.")

            for fid in SPEC["facts_detach_to_register"]:
                frow = rows_where(cur, "facts", "fact_id", fid)[0]
                frow["citations"] = rows_where(
                    cur, "citations", "fact_id", fid)
                register["detached_facts"].append(frow)
                cur.execute(
                    "DELETE FROM citations WHERE fact_id = ?", (fid,))
                cur.execute(
                    "DELETE FROM facts WHERE fact_id = ?", (fid,))
            print(f"Detached {len(register['detached_facts'])} "
                  f"fact(s) to the register.")

        results = []

        def gate(label, ok):
            results.append(ok)
            print(("PASS " if ok else "FAIL ") + label)

        gate("persons total = 3805",
             cur.execute("SELECT COUNT(*) FROM persons")
             .fetchone()[0] == post["persons"])
        gate("sources total unchanged",
             cur.execute("SELECT COUNT(*) FROM sources")
             .fetchone()[0] == post["sources"])
        prow = cur.execute(
            "SELECT name, birth_info, death_info, notes FROM "
            "persons WHERE person_id = ?", (pid,)).fetchone()
        gate("8890 renamed to 'John H. Davis' with the 1819 "
             "man's dates",
             prow[0] == p["name_to"]
             and prow[1] == p["person_row_to"]["birth_info"]
             and prow[2] == p["person_row_to"]["death_info"])
        gate("8890 facts = the 5 kept facts",
             {r["fact_id"] for r in rows_where(
                 cur, "facts", "person_id", pid)}
             == set(p["facts_keep"]))
        gate("profile A facts = the 4 moved facts",
             {r["fact_id"] for r in rows_where(
                 cur, "facts", "person_id", a_id)}
             == set(a_spec["facts_move"]))
        gate("profile B facts = the 1900 census fact",
             {r["fact_id"] for r in rows_where(
                 cur, "facts", "person_id", b_id)}
             == set(b_spec["facts_move"]))
        gate("profile B holds both photo rows; 8890 holds none",
             {r["photo_id"] for r in rows_where(
                 cur, "person_photos", "person_id", b_id)}
             == set(b_spec["photos_move"])
             and rows_where(cur, "person_photos", "person_id",
                            pid) == [])
        gate("catalog primary_person_id = B for both photos",
             all(cur.execute(
                 "SELECT primary_person_id FROM "
                 "unified_photo_catalog WHERE photo_id = ?",
                 (ph,)).fetchone()[0] == b_id
                 for ph in b_spec["photos_move"]))
        gate("profile B relationships = child_of 12006 + 11247",
             {(r["relationship_type"], r["person_b_id"])
              for r in rows_where(cur, "relationships",
                                  "person_a_id", b_id)}
             == {(rel["relationship_type"], rel["person_b_id"])
                 for rel in b_spec["relationships_add"]})
        for mv in SPEC["citation_moves"]:
            gate(f"citation {mv['citation_id']} on fact "
                 f"{mv['to_fact_id']}",
                 cur.execute(
                     "SELECT fact_id FROM citations "
                     "WHERE citation_id = ?",
                     (mv["citation_id"],)).fetchone()[0]
                 == mv["to_fact_id"])
        for ss in SPEC["citation_supersede"]:
            gate(f"citation {ss['citation_id']} SUPERSEDED",
                 "SUPERSEDED" in (cur.execute(
                     "SELECT evidence_text FROM citations "
                     "WHERE citation_id = ?",
                     (ss["citation_id"],)).fetchone()[0] or ""))
        gate("detached fact 24991 gone from the database",
             cur.execute(
                 "SELECT COUNT(*) FROM facts WHERE fact_id = 24991"
             ).fetchone()[0] == 0)
        gate("8890 notes carry the split marker and the removed "
             "Find a Grave note line is gone",
             p["note_marker"] in (prow[3] or "")
             and "Verified via FindAGrave" not in (prow[3] or ""))
        gate("profile A notes carry the memorial 137944370 text",
             "137944370" in (cur.execute(
                 "SELECT notes FROM persons WHERE person_id = ?",
                 (a_id,)).fetchone()[0] or ""))
        gate("PRAGMA integrity_check",
             cur.execute("PRAGMA integrity_check").fetchone()[0]
             == "ok")

        if not all(results):
            con.rollback()
            abort(f"{results.count(False)} of {len(results)} final "
                  f"gates failed; rolled back")
        con.commit()
        print(f"Final gates passed ({len(results)} checks).")
        print("COMMITTED.")

        if not applied:
            reg_path = os.path.join(repo_root, SPEC["register_path"])
            os.makedirs(os.path.dirname(reg_path), exist_ok=True)
            with open(reg_path, "w") as fh:
                json.dump(register, fh, indent=2, sort_keys=True)
            print(f"Register written: {reg_path} "
                  f"({len(register['detached_facts'])} facts)")
        return 0
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        con.rollback()
        abort(f"unexpected error, rolled back: {exc!r}")


if __name__ == "__main__":
    sys.exit(main())
