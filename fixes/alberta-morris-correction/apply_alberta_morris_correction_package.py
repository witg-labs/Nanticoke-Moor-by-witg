#!/usr/bin/env python3
"""Alberta Morris (8345) correction package (2026-11-27).

Implements Jequan Davis's conflation ruling of 2026-11-22: profile
8345 is ONE woman, no split. Birth 27 Sep 1939 and death 26 Apr 1983
(aged 43) are adopted on the person row. The GEDCOM birth fact 7798
(5 Mar 1937) is flagged 'superseded' in fact_quality_flags and stays
visible. The GEDCOM fact 7799, the entry '1971 Residence' mis-typed
as a death, is retyped to a Residence in 1971. Two vital-record
citations that quote the GEDCOM dates (30505, 30506) move from the
adopted facts onto the GEDCOM facts they describe, per the
prevention rule (a citation attaches to the fact whose date it
quotes). Citation 30508 (1950 census text on the 1940 census fact
24506) is marked SUPERSEDED in place, the William Jackson 439
precedent. A correction note is appended to the profile.

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
    HERE, "alberta_morris_correction_package.json")))
MARKER = " [Marked SUPERSEDED by alberta-morris-correction package "\
    "2026-11-27: "


def abort(msg):
    print(f"ABORT: {msg}")
    sys.exit(3)


def table_exists(cur, name):
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,)).fetchone() is not None


def main():
    if len(sys.argv) != 2:
        print("usage: apply_alberta_morris_correction_package.py "
              "<db path>")
        return 2
    db_path = sys.argv[1]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{db_path}.backup-{stamp}"
    shutil.copy2(db_path, backup)
    print(f"Backup written: {backup}")

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    p = SPEC["person"]
    pid = p["person_id"]
    pre = SPEC["expected_pre_state"]

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

    applied = (row["birth_info"] == p["birth_info_to"]
               and row["death_info"] == p["death_info_to"])
    if not applied:
        n_persons = cur.execute(
            "SELECT COUNT(*) FROM persons").fetchone()[0]
        n_sources = cur.execute(
            "SELECT COUNT(*) FROM sources").fetchone()[0]
        print(f"Pre-state: persons {n_persons}, sources "
              f"{n_sources}.")
        if n_persons != pre["persons"]:
            abort(f"persons {n_persons} != expected {pre['persons']}")
        if n_sources != pre["sources"]:
            abort(f"sources {n_sources} != expected {pre['sources']}")
        if row["birth_info"] != p["birth_info_from"]:
            abort(f"birth_info {row['birth_info']!r} != expected "
                  f"{p['birth_info_from']!r}")
        if row["death_info"] != p["death_info_from"]:
            abort(f"death_info {row['death_info']!r} != expected "
                  f"{p['death_info_from']!r}")
        fact_ids = {r["fact_id"] for r in cur.execute(
            "SELECT fact_id FROM facts WHERE person_id = ?",
            (pid,))}
        if fact_ids != set(SPEC["facts_expected_on_person"]):
            abort(f"facts on {pid} {sorted(fact_ids)} != expected "
                  f"{SPEC['facts_expected_on_person']}")
        fs = SPEC["fact_supersede"]
        frow = cur.execute("SELECT * FROM facts WHERE fact_id = ?",
                           (fs["fact_id"],)).fetchone()
        if (frow is None or frow["person_id"] != pid
                or frow["fact_type"] != fs["fact_type"]
                or frow["date_string"] != fs["date_string"]):
            abort("supersede target fact 7798 does not match spec")
        rt = SPEC["fact_retype"]
        rrow = cur.execute("SELECT * FROM facts WHERE fact_id = ?",
                           (rt["fact_id"],)).fetchone()
        if (rrow is None or rrow["person_id"] != pid
                or rrow["fact_type"] != rt["from_type"]
                or rrow["date_string"] != rt["from_date"]):
            abort("retype target fact 7799 does not match spec")
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

    try:
        cur.execute("BEGIN")

        cur.execute(
            "UPDATE persons SET birth_info = ?, death_info = ? "
            "WHERE person_id = ?",
            (p["birth_info_to"], p["death_info_to"], pid))
        print(f"Person {pid} dates adopted: "
              f"{p['birth_info_to']} / {p['death_info_to']}.")

        fs = SPEC["fact_supersede"]
        existing = cur.execute(
            "SELECT flag FROM fact_quality_flags WHERE fact_id = ?",
            (fs["fact_id"],)).fetchone()
        if existing is None:
            cur.execute(
                "INSERT INTO fact_quality_flags "
                "(fact_id, flag, note, applied_at) VALUES (?, ?, ?, ?)",
                (fs["fact_id"], fs["flag"], fs["flag_note"],
                 datetime.now().isoformat(timespec="seconds")))
            print(f"Fact {fs['fact_id']} flagged "
                  f"{fs['flag']}.")
        elif existing[0] != fs["flag"]:
            abort(f"fact {fs['fact_id']} already flagged "
                  f"{existing[0]!r}")

        rt = SPEC["fact_retype"]
        cur.execute(
            "UPDATE facts SET fact_type = ?, date_string = ? "
            "WHERE fact_id = ?",
            (rt["to_type"], rt["to_date"], rt["fact_id"]))
        print(f"Fact {rt['fact_id']} retyped: {rt['from_type']} "
              f"'{rt['from_date']}' -> {rt['to_type']} "
              f"'{rt['to_date']}'.")

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

        notes = row["notes"] or ""
        if SPEC["note_marker"] not in notes:
            cur.execute(
                "UPDATE persons SET notes = ? WHERE person_id = ?",
                ((notes + "\n\n" if notes else "")
                 + SPEC["note_text"], pid))
            print("Correction note appended.")

        results = []

        def gate(label, ok):
            results.append(ok)
            print(("PASS " if ok else "FAIL ") + label)

        gate("persons total unchanged",
             cur.execute("SELECT COUNT(*) FROM persons")
             .fetchone()[0] == pre["persons"])
        gate("sources total unchanged",
             cur.execute("SELECT COUNT(*) FROM sources")
             .fetchone()[0] == pre["sources"])
        prow = cur.execute(
            "SELECT birth_info, death_info, notes FROM persons "
            "WHERE person_id = ?", (pid,)).fetchone()
        gate("person dates adopted",
             prow[0] == p["birth_info_to"]
             and prow[1] == p["death_info_to"])
        gate("facts on person = 9",
             cur.execute("SELECT COUNT(*) FROM facts "
                         "WHERE person_id = ?",
                         (pid,)).fetchone()[0] == 9)
        gate("fact 7798 flagged superseded",
             cur.execute("SELECT flag FROM fact_quality_flags "
                         "WHERE fact_id = 7798").fetchone()[0]
             == "superseded")
        frow = cur.execute(
            "SELECT fact_type, date_string FROM facts "
            "WHERE fact_id = 7799").fetchone()
        gate("fact 7799 retyped to Residence 1971",
             frow[0] == "Residence" and frow[1] == "1971")
        for fid, expected in SPEC["citations_expected_after"].items():
            got = sorted(r[0] for r in cur.execute(
                "SELECT citation_id FROM citations "
                "WHERE fact_id = ?", (int(fid),)))
            gate(f"citations on fact {fid} = {expected}",
                 got == sorted(expected))
        gate("citation 30508 SUPERSEDED",
             "SUPERSEDED" in (cur.execute(
                 "SELECT evidence_text FROM citations "
                 "WHERE citation_id = 30508").fetchone()[0] or ""))
        gate("notes carry the correction marker",
             SPEC["note_marker"] in (prow[2] or ""))
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
