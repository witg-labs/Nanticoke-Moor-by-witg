#!/usr/bin/env python3
"""John S Thompson (9561) cleanup package (2026-11-27).

Implements Jequan Davis's conflation ruling of 2026-11-22: profile
9561 is NOT a conflation. It is one infant, John S Thompson
(b. 9 Feb 1928 Stockley, d. 12 Jul 1930 Georgetown); the
"abt 1927" birth fact is a precision variant of the same birth,
and its vital-record citation quotes the 1928 date. Cleanup only:
the undated marriage fact 25365, impossible for a child who died
aged 2, is detached to the package's unassigned-evidence register
with its citation intact, and the two Mitsawokett group photos
(2366 "Thompson John & Sarah", 2368 "Thompson John Family"),
which show an adult John Thompson and fit no part of this child's
life, are detached to the unidentified-photo pool: 9561's
person_photos rows for them are deleted (recorded in the
register) and unified_photo_catalog.primary_person_id is set to
NULL where it pointed at 9561. A correction note is appended to
the profile. Nothing else changes: no facts kept on the profile
are edited, no relationships are touched, no records are created.

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
    HERE, "john_s_thompson_cleanup_package.json")))


def abort(msg):
    print(f"ABORT: {msg}")
    sys.exit(3)


def rows_where(cur, table, col, val):
    cur.execute(f"SELECT * FROM {table} WHERE {col} = ?", (val,))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def main():
    if len(sys.argv) != 3:
        print("usage: apply_john_s_thompson_cleanup_package.py "
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
    p = SPEC["person_9561"]
    pid = p["person_id"]
    pre, post = SPEC["expected_pre_state"], SPEC["expected_post_state"]
    detach_facts = SPEC["facts_detach_to_register"]
    detach_photos = SPEC["photos_detach_to_unidentified"]

    row = cur.execute("SELECT * FROM persons WHERE person_id = ?",
                      (pid,)).fetchone()
    if row is None:
        abort(f"person {pid} not found")
    if row["name"] != p["name"]:
        abort(f"person {pid} name is {row['name']!r}, "
              f"expected {p['name']!r}")
    print(f"Person verified: {pid} {row['name']}")

    fact_present = cur.execute(
        "SELECT COUNT(*) FROM facts WHERE fact_id IN (%s)"
        % ",".join("?" * len(detach_facts)),
        detach_facts).fetchone()[0] > 0
    photo_rows = rows_where(cur, "person_photos", "person_id", pid)
    applied = not fact_present and not photo_rows

    if not applied:
        n_persons = cur.execute(
            "SELECT COUNT(*) FROM persons").fetchone()[0]
        n_sources = cur.execute(
            "SELECT COUNT(*) FROM sources").fetchone()[0]
        print(f"Pre-state: persons {n_persons}, sources "
              f"{n_sources}, 9561 facts "
              f"{len(rows_where(cur, 'facts', 'person_id', pid))}, "
              f"9561 photo rows {len(photo_rows)}.")
        if n_persons != pre["persons"]:
            abort(f"persons {n_persons} != expected {pre['persons']}")
        if n_sources != pre["sources"]:
            abort(f"sources {n_sources} != expected {pre['sources']}")
        fact_ids = {r["fact_id"] for r in rows_where(
            cur, "facts", "person_id", pid)}
        if fact_ids != set(p["facts_expected"]):
            abort(f"facts on {pid} {sorted(fact_ids)} != expected "
                  f"{p['facts_expected']}")
        photo_ids = sorted(r["photo_id"] for r in photo_rows)
        if photo_ids != sorted(detach_photos):
            abort(f"photo rows on {pid} {photo_ids} != expected "
                  f"{sorted(detach_photos)}")
        for phid in detach_photos:
            if not rows_where(cur, "unified_photo_catalog",
                              "photo_id", phid):
                abort(f"photo {phid} has no unified_photo_catalog "
                      f"row")

    register = {
        "package": SPEC["package"],
        "date": SPEC["date"],
        "detached_from_person_id": pid,
        "detached_facts": [],
        "detached_photos": [],
    }
    try:
        cur.execute("BEGIN")

        if not applied:
            for fid in detach_facts:
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

            for phid in detach_photos:
                entry = {
                    "photo_id": phid,
                    "person_photos_rows": [
                        r for r in photo_rows
                        if r["photo_id"] == phid],
                    "photo_catalog_row": rows_where(
                        cur, "unified_photo_catalog", "photo_id",
                        phid)[0],
                }
                register["detached_photos"].append(entry)
                cur.execute(
                    "DELETE FROM person_photos WHERE person_id = ? "
                    "AND photo_id = ?", (pid, phid))
                cur.execute(
                    "UPDATE unified_photo_catalog SET "
                    "primary_person_id = NULL WHERE photo_id = ? "
                    "AND primary_person_id = ?", (phid, pid))
            print(f"Detached {len(register['detached_photos'])} "
                  f"photo(s) to the unidentified pool.")

            notes = row["notes"] or ""
            if p["note_marker"] not in notes:
                cur.execute(
                    "UPDATE persons SET notes = ? "
                    "WHERE person_id = ?",
                    ((notes + "\n\n" if notes else "")
                     + p["note_text"], pid))
                print("Correction note appended to 9561.")

        results = []

        def gate(label, ok):
            results.append(ok)
            print(("PASS " if ok else "FAIL ") + label)

        gate("persons total unchanged",
             cur.execute("SELECT COUNT(*) FROM persons")
             .fetchone()[0] == post["persons"])
        gate("sources total unchanged",
             cur.execute("SELECT COUNT(*) FROM sources")
             .fetchone()[0] == post["sources"])
        gate("9561 facts = the 7 kept facts",
             {r["fact_id"] for r in rows_where(
                 cur, "facts", "person_id", pid)}
             == set(p["facts_keep"]))
        gate("detached marriage fact is gone from the database",
             cur.execute(
                 "SELECT COUNT(*) FROM facts WHERE fact_id IN (%s)"
                 % ",".join("?" * len(detach_facts)),
                 detach_facts).fetchone()[0] == 0)
        gate("9561 has no person_photos rows",
             cur.execute(
                 "SELECT COUNT(*) FROM person_photos "
                 "WHERE person_id = ?", (pid,)).fetchone()[0] == 0)
        gate("photos 2366/2368 no longer name 9561 as primary "
             "person",
             cur.execute(
                 "SELECT COUNT(*) FROM unified_photo_catalog "
                 "WHERE photo_id IN (%s) AND primary_person_id = ?"
                 % ",".join("?" * len(detach_photos)),
                 detach_photos + [pid]).fetchone()[0] == 0)
        gate("9561 notes carry the correction marker",
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
                  f"({len(register['detached_facts'])} facts, "
                  f"{len(register['detached_photos'])} photos)")
        return 0
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        con.rollback()
        abort(f"unexpected error, rolled back: {exc!r}")


if __name__ == "__main__":
    sys.exit(main())
