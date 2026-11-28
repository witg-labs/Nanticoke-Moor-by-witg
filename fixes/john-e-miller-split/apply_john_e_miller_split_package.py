#!/usr/bin/env python3
"""John E Miller (8857) split package (2026-11-27).

Implements Jequan Davis's conflation ruling of 2026-11-22: profile
8857 keeps John E Miller (b. 1856, m. 11 Mar 1875, d. 4 Jun 1927;
vital records and Find a Grave #107225416). The GEDCOM-only Lewes
life (facts 9082, 9083, 9084: b. Mar 1873 Delaware, d. 24 Feb 1950
Lewes) moves to a new profile under the name form its own Name
fact records, "John E. Miller", flagged unproven (evidence_level
copied at runtime from split-created profile 12007). Four
same-name facts that fit neither man (14635, 14673, 15175, 15675)
are detached to the package's unassigned-evidence register with
citations intact; nothing is deleted outright. Citation 31469
(1920 census text on the 1860 census fact 24964) is marked
SUPERSEDED in place. Relationships are untouched: the two
GEDCOM-linked children stay on 8857, as no evidence on the profile
ties them to one man over the other.

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
    HERE, "john_e_miller_split_package.json")))
MARKER = " [Marked SUPERSEDED by john-e-miller-split package "\
    "2026-11-27: "


def abort(msg):
    print(f"ABORT: {msg}")
    sys.exit(3)


def rows_where(cur, table, col, val):
    cur.execute(f"SELECT * FROM {table} WHERE {col} = ?", (val,))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def main():
    if len(sys.argv) != 3:
        print("usage: apply_john_e_miller_split_package.py "
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
    p = SPEC["person_8857"]
    pid = p["person_id"]
    pre, post = SPEC["expected_pre_state"], SPEC["expected_post_state"]

    row = cur.execute("SELECT * FROM persons WHERE person_id = ?",
                      (pid,)).fetchone()
    if row is None:
        abort(f"person {pid} not found")
    if row["name"] != p["name"]:
        abort(f"person {pid} name is {row['name']!r}, "
              f"expected {p['name']!r}")
    print(f"Person verified: {pid} {row['name']}")

    np_spec = SPEC["new_profile"]
    existing = cur.execute(
        "SELECT person_id FROM persons WHERE name = ?",
        (np_spec["name"],)).fetchone()
    applied = existing is not None
    new_id = existing[0] if applied else None

    if not applied:
        n_persons = cur.execute(
            "SELECT COUNT(*) FROM persons").fetchone()[0]
        n_sources = cur.execute(
            "SELECT COUNT(*) FROM sources").fetchone()[0]
        print(f"Pre-state: persons {n_persons}, sources "
              f"{n_sources}, 8857 facts "
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
        for ss in SPEC["citation_supersede"]:
            crow = cur.execute(
                "SELECT * FROM citations WHERE citation_id = ?",
                (ss["citation_id"],)).fetchone()
            if crow is None or crow["fact_id"] != ss["on_fact_id"]:
                abort(f"citation {ss['citation_id']} not on fact "
                      f"{ss['on_fact_id']} as expected")
            if "SUPERSEDED" in (crow["evidence_text"] or ""):
                abort(f"citation {ss['citation_id']} already marked")

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
                (np_spec["evidence_level_from_person_id"],)
            ).fetchone()
            if donor is None:
                abort("evidence_level donor profile "
                      f"{np_spec['evidence_level_from_person_id']} "
                      "not found")
            src_donor = cur.execute(
                "SELECT source_page, dataset_source FROM persons "
                "WHERE person_id = ?",
                (np_spec["copy_dataset_from_person_id"],)).fetchone()
            cur.execute(
                "INSERT INTO persons (name, source_page, birth_info,"
                " death_info, notes, dataset_source, first_name,"
                " middle_name, evidence_level) VALUES (?, ?, ?, ?,"
                " ?, ?, ?, ?, ?)",
                (np_spec["name"], src_donor[0], np_spec["birth_info"],
                 np_spec["death_info"], np_spec["notes"],
                 src_donor[1], np_spec["first_name"],
                 np_spec["middle_name"], donor[0]))
            new_id = cur.lastrowid
            print(f"New profile created: {new_id} "
                  f"{np_spec['name']}")

            for fid in SPEC["facts_move_to_new_profile"]:
                cur.execute(
                    "UPDATE facts SET person_id = ? WHERE fact_id = ?",
                    (new_id, fid))
            print(f"Facts moved to {new_id}: "
                  f"{SPEC['facts_move_to_new_profile']}")

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
                  f"facts to the register.")

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

            notes = row["notes"] or ""
            if p["note_marker"] not in notes:
                cur.execute(
                    "UPDATE persons SET notes = ? "
                    "WHERE person_id = ?",
                    ((notes + "\n\n" if notes else "")
                     + p["note_text"], pid))
                print("Split note appended to 8857.")

        results = []

        def gate(label, ok):
            results.append(ok)
            print(("PASS " if ok else "FAIL ") + label)

        gate("persons total = 3803",
             cur.execute("SELECT COUNT(*) FROM persons")
             .fetchone()[0] == post["persons"])
        gate("sources total unchanged",
             cur.execute("SELECT COUNT(*) FROM sources")
             .fetchone()[0] == post["sources"])
        gate("8857 facts = the 6 kept facts",
             {r["fact_id"] for r in rows_where(
                 cur, "facts", "person_id", pid)}
             == set(p["facts_keep"]))
        gate("new profile facts = the 3 moved facts",
             {r["fact_id"] for r in rows_where(
                 cur, "facts", "person_id", new_id)}
             == set(SPEC["facts_move_to_new_profile"]))
        gate("detached facts are gone from the database",
             cur.execute(
                 "SELECT COUNT(*) FROM facts WHERE fact_id IN "
                 "(14635, 14673, 15175, 15675)").fetchone()[0] == 0)
        gate("citation 31469 SUPERSEDED",
             "SUPERSEDED" in (cur.execute(
                 "SELECT evidence_text FROM citations "
                 "WHERE citation_id = 31469").fetchone()[0] or ""))
        gate("8857 notes carry the split marker",
             p["note_marker"] in (cur.execute(
                 "SELECT notes FROM persons WHERE person_id = ?",
                 (pid,)).fetchone()[0] or ""))
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
