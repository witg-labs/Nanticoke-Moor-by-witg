#!/usr/bin/env python3
"""Lydia J Harmon (9928) split package (2026-11-27).

Implements Jequan Davis's conflation ruling of 2026-11-22: profile
9928 keeps Lydia J Harmon (b. 16 Jan 1776, d. 6 Mar 1851; Find a
Grave #86408962 burial, census facts). The 1848-1927 woman becomes
a new profile, "Lydia J. Harmon", flagged unproven
(evidence_level copied at runtime from split-created profile
12007), taking facts 9912, 9913, 9914 and the generic marriage
fact 25647, plus the spouse link to Simon Harmon (10514). The
spouse link is stored in the live DB as type 'spouse' in
reciprocal rows (9928 -> 10514 and 10514 -> 9928); both rows are
re-pointed to the new profile. The child_of links to Raymond
Harmon (9931) and Hattie Miller (8860), parents born 1902 and
1905 who fit neither woman, are detached to the package's
unassigned-evidence register, held as a couple; nothing is
deleted outright.

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
    HERE, "lydia_j_harmon_split_package.json")))


def abort(msg):
    print(f"ABORT: {msg}")
    sys.exit(3)


def rows_where(cur, table, col, val):
    cur.execute(f"SELECT * FROM {table} WHERE {col} = ?", (val,))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def main():
    if len(sys.argv) != 3:
        print("usage: apply_lydia_j_harmon_split_package.py "
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
    p = SPEC["person_9928"]
    pid = p["person_id"]
    pre, post = SPEC["expected_pre_state"], SPEC["expected_post_state"]
    np_spec = SPEC["new_profile"]
    move_ids = list(np_spec["facts_move"])
    spouse_b = SPEC["relationships_move_spouse"]["person_b_id"]
    detach_specs = SPEC["relationships_detach_to_register"]

    row = cur.execute("SELECT * FROM persons WHERE person_id = ?",
                      (pid,)).fetchone()
    if row is None:
        abort(f"person {pid} not found")
    if row["name"] != p["name"]:
        abort(f"person {pid} name is {row['name']!r}, "
              f"expected {p['name']!r}")
    print(f"Person verified: {pid} {row['name']}")

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
              f"{n_sources}, 9928 facts "
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
        rels_out = {(r["relationship_type"], r["person_b_id"])
                    for r in rows_where(cur, "relationships",
                                        "person_a_id", pid)}
        expected_rels = {(d["relationship_type"], d["person_b_id"])
                         for d in detach_specs}
        expected_rels.add(("spouse", spouse_b))
        if rels_out != expected_rels:
            abort(f"9928 outgoing relationships "
                  f"{sorted(rels_out)} != expected "
                  f"{sorted(expected_rels)}")
        recip = cur.execute(
            "SELECT COUNT(*) FROM relationships WHERE "
            "person_a_id = ? AND person_b_id = ? AND "
            "relationship_type = 'spouse'",
            (spouse_b, pid)).fetchone()[0]
        if recip != 1:
            abort(f"reciprocal spouse row ({spouse_b} -> {pid}) "
                  f"count {recip} != 1")

    register = {
        "package": SPEC["package"],
        "date": SPEC["date"],
        "detached_from_person_id": pid,
        "detached_relationships": [],
        "note": ("Parentage held as a couple: Raymond Harmon "
                 "(9931) and Hattie Miller (8860), recorded as "
                 "parents of Lydia on profile 9928, fit neither "
                 "the 1776-1851 woman who keeps 9928 nor the "
                 "1848-1927 woman split off to her own profile. "
                 "Detached under the 2026-11-22 ruling, not "
                 "deleted; may belong to a Lydia not yet in the "
                 "archive."),
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
            if src_donor is None:
                abort("dataset donor profile "
                      f"{np_spec['copy_dataset_from_person_id']} "
                      "not found")
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

            for fid in move_ids:
                cur.execute(
                    "UPDATE facts SET person_id = ? WHERE "
                    "fact_id = ? AND person_id = ?",
                    (new_id, fid, pid))
                if cur.rowcount != 1:
                    abort(f"fact {fid} was not on {pid} to move")
            print(f"Facts moved to {new_id}: {move_ids}")

            cur.execute(
                "UPDATE relationships SET person_a_id = ? WHERE "
                "person_a_id = ? AND person_b_id = ? AND "
                "relationship_type = 'spouse'",
                (new_id, pid, spouse_b))
            if cur.rowcount != 1:
                abort("outgoing spouse row to "
                      f"{spouse_b} was not on {pid} to move")
            cur.execute(
                "UPDATE relationships SET person_b_id = ? WHERE "
                "person_a_id = ? AND person_b_id = ? AND "
                "relationship_type = 'spouse'",
                (new_id, spouse_b, pid))
            if cur.rowcount != 1:
                abort("reciprocal spouse row from "
                      f"{spouse_b} was not pointing at {pid}")
            print(f"Spouse link to {spouse_b} moved to {new_id} "
                  f"(both reciprocal 'spouse' rows re-pointed).")

            for d in detach_specs:
                found = rows_where(cur, "relationships",
                                   "person_a_id", pid)
                match = [r for r in found
                         if r["relationship_type"]
                         == d["relationship_type"]
                         and r["person_b_id"] == d["person_b_id"]]
                if len(match) != 1:
                    abort(f"detach target ({pid} -> "
                          f"{d['person_b_id']}, "
                          f"{d['relationship_type']}) found "
                          f"{len(match)} rows, expected 1")
                register["detached_relationships"].append(match[0])
                cur.execute(
                    "DELETE FROM relationships WHERE id = ?",
                    (match[0]["id"],))
            print(f"Detached {len(register['detached_relationships'])} "
                  f"relationships to the register (held couple).")

            notes = row["notes"] or ""
            if p["note_marker"] not in notes:
                cur.execute(
                    "UPDATE persons SET notes = ? "
                    "WHERE person_id = ?",
                    ((notes + "\n\n" if notes else "")
                     + p["note_text"], pid))
                print("Split note appended to 9928.")

        results = []

        def gate(label, ok):
            results.append(ok)
            print(("PASS " if ok else "FAIL ") + label)

        gate("persons total = 3806",
             cur.execute("SELECT COUNT(*) FROM persons")
             .fetchone()[0] == post["persons"])
        gate("sources total unchanged",
             cur.execute("SELECT COUNT(*) FROM sources")
             .fetchone()[0] == post["sources"])
        gate("9928 facts = the 5 kept facts",
             {r["fact_id"] for r in rows_where(
                 cur, "facts", "person_id", pid)}
             == set(p["facts_keep"]))
        gate("new profile facts = the 4 moved facts",
             {r["fact_id"] for r in rows_where(
                 cur, "facts", "person_id", new_id)}
             == set(move_ids))
        gate("new profile outgoing relationships = {(spouse, 10514)}",
             {(r["relationship_type"], r["person_b_id"])
              for r in rows_where(cur, "relationships",
                                  "person_a_id", new_id)}
             == {("spouse", spouse_b)})
        gate("reciprocal spouse row (10514 -> new profile) exists",
             cur.execute(
                 "SELECT COUNT(*) FROM relationships WHERE "
                 "person_a_id = ? AND person_b_id = ? AND "
                 "relationship_type = 'spouse'",
                 (spouse_b, new_id)).fetchone()[0] == 1)
        gate("zero relationship rows leave 9928",
             cur.execute(
                 "SELECT COUNT(*) FROM relationships WHERE "
                 "person_a_id = ?", (pid,)).fetchone()[0] == 0)
        gate("9928 notes carry the split marker",
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
                  f"({len(register['detached_relationships'])} "
                  f"relationships)")
        return 0
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        con.rollback()
        abort(f"unexpected error, rolled back: {exc!r}")


if __name__ == "__main__":
    sys.exit(main())
