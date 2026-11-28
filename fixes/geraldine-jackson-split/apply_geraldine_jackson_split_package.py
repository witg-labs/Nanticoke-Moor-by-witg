#!/usr/bin/env python3
"""Geraldine Jackson (9968) split package (2026-11-27).

Implements Jequan Davis's conflation ruling of 2026-11-22: profile
9968 keeps the infant Geraldine Jackson (b. 30 Aug 1937, d. 16 Apr
1938, aged 7 months), her parents Blaine Jackson and Gladys Mae
Jackson, and her burial (Find a Grave #288073524). The adult
Geraldine Jackson (b. 8 Aug 1925, d. 22 Jul 1985, aged 59) becomes
her own profile, "Geraldine Jackson (1925-1985)", flagged unproven
(evidence_level copied at runtime from split-created profile
12007), taking facts 6881, 6882, 6883 and the marriage fact 25718.

The two vital-record citations that quote the infant's dates move
FIRST, per the prevention rule: citation 33152 (birth registration
quoting 30 Aug 1937) from the adult's birth fact 6882 to the
infant's birth fact 9335, and citation 33153 (death registration
quoting 16 Apr 1938) from the adult's death fact 6883 to the
infant's death fact 9336. The Social Security Application fact
25717, dated 1937, fits neither woman and is held UNASSIGNED on
9968, flagged 'unassigned_held' in fact_quality_flags. The
pedigree-diagram photo 1340 stays on 9968. Relationships are
untouched: the parents stay with the infant, per the ruling.

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
    HERE, "geraldine_jackson_split_package.json")))


def abort(msg):
    print(f"ABORT: {msg}")
    sys.exit(3)


def table_exists(cur, name):
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,)).fetchone() is not None


def rows_where(cur, table, col, val):
    cur.execute(f"SELECT * FROM {table} WHERE {col} = ?", (val,))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def main():
    if len(sys.argv) != 3:
        print("usage: apply_geraldine_jackson_split_package.py "
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
    p = SPEC["person_9968"]
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

    if not table_exists(cur, "fact_quality_flags"):
        abort("fact_quality_flags table missing (Package 3 table)")

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
              f"{n_sources}, 9968 facts "
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

    try:
        cur.execute("BEGIN")

        if not applied:
            for mv in SPEC["citation_moves"]:
                cur.execute(
                    "UPDATE citations SET fact_id = ? "
                    "WHERE citation_id = ?",
                    (mv["to_fact_id"], mv["citation_id"]))
                print(f"Citation {mv['citation_id']} moved: fact "
                      f"{mv['from_fact_id']} -> {mv['to_fact_id']}.")

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
                " evidence_level) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (np_spec["name"], src_donor[0], np_spec["birth_info"],
                 np_spec["death_info"], np_spec["notes"],
                 src_donor[1], np_spec["first_name"], donor[0]))
            new_id = cur.lastrowid
            print(f"New profile created: {new_id} "
                  f"{np_spec['name']}")

            for fid in np_spec["facts_move"]:
                cur.execute(
                    "UPDATE facts SET person_id = ? WHERE fact_id = ?",
                    (new_id, fid))
            print(f"Facts moved to {new_id}: "
                  f"{np_spec['facts_move']}")

            fh = SPEC["fact_flag_held"]
            flag_row = cur.execute(
                "SELECT flag FROM fact_quality_flags "
                "WHERE fact_id = ?", (fh["fact_id"],)).fetchone()
            if flag_row is None:
                cur.execute(
                    "INSERT INTO fact_quality_flags "
                    "(fact_id, flag, note, applied_at) "
                    "VALUES (?, ?, ?, ?)",
                    (fh["fact_id"], fh["flag"], fh["flag_note"],
                     datetime.now().isoformat(timespec="seconds")))
                print(f"Fact {fh['fact_id']} flagged {fh['flag']}.")
            elif flag_row[0] != fh["flag"]:
                abort(f"fact {fh['fact_id']} already flagged "
                      f"{flag_row[0]!r}")

            notes = row["notes"] or ""
            if p["note_marker"] not in notes:
                cur.execute(
                    "UPDATE persons SET notes = ? "
                    "WHERE person_id = ?",
                    ((notes + "\n\n" if notes else "")
                     + p["note_text"], pid))
                print("Split note appended to 9968.")

        results = []

        def gate(label, ok):
            results.append(ok)
            print(("PASS " if ok else "FAIL ") + label)

        gate("persons total = 3807",
             cur.execute("SELECT COUNT(*) FROM persons")
             .fetchone()[0] == post["persons"])
        gate("sources total unchanged",
             cur.execute("SELECT COUNT(*) FROM sources")
             .fetchone()[0] == post["sources"])
        gate("9968 facts = the 5 kept facts",
             {r["fact_id"] for r in rows_where(
                 cur, "facts", "person_id", pid)}
             == set(p["facts_keep"]))
        gate("new profile facts = the 4 moved facts",
             {r["fact_id"] for r in rows_where(
                 cur, "facts", "person_id", new_id)}
             == set(np_spec["facts_move"]))
        for fid, expected in SPEC["citations_expected_after"].items():
            got = sorted(r[0] for r in cur.execute(
                "SELECT citation_id FROM citations "
                "WHERE fact_id = ?", (int(fid),)))
            gate(f"citations on fact {fid} = {expected}",
                 got == sorted(expected))
        fh = SPEC["fact_flag_held"]
        gate("fact 25717 flagged unassigned_held",
             cur.execute("SELECT flag FROM fact_quality_flags "
                         "WHERE fact_id = 25717").fetchone()[0]
             == fh["flag"])
        gate("9968 keeps exactly 1 photo row (photo 1340)",
             [r["photo_id"] for r in rows_where(
                 cur, "person_photos", "person_id", pid)] == [1340])
        gate("9968 notes carry the split marker",
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
        return 0
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        con.rollback()
        abort(f"unexpected error, rolled back: {exc!r}")


if __name__ == "__main__":
    sys.exit(main())
