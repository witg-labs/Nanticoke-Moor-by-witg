#!/usr/bin/env python3
"""Lydia E Norwood un-redaction fix.

Lydia E Norwood (9334, d. 26 Dec 1856) is exported as a living
person: the exporter's is_probably_living() check matches the word
"living" in a person's notes, and her biographical notes say the
Nanticoke community "remains a living reality". The export
therefore shows her birth as "Private" and withholds all her facts
and notes. Her birth-year correction (abt 1768 -> abt 1790, 1850
census) landed in the database with the obituary-dates package on
2026-11-27 but is invisible on her public profile for the same
reason.

This package makes exactly one wording change: every occurrence
of "a living reality" in her notes becomes "a thriving reality"
(same meaning; the notes themselves use "continues to thrive" for
the same community elsewhere). Before editing, the script prints
every "living" occurrence with context; after editing, it gates
on zero remaining "living" substrings (case-insensitive) and on
the new notes being byte-identical to the old notes apart from
the swapped phrase. Any other "living" instance aborts the run
for review rather than guessing at more wording. It also flags
her two generic import facts (Census 25218 dated 1790, Marriage
25219) generic_unverified, the same soft treatment the
obituary-dates batch applied, so her profile is clean when it
appears. Nothing else is touched.

Safety: hard gates abort (rollback) on any surprise; idempotent
(a second run is a no-op); backup written first.

Usage: python3 apply_lydia_unredact_package.py <path-to-db>
"""
import json
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = json.loads(
    (HERE / "lydia_unredact_package.json").read_text(encoding="utf-8"))


def fail(msg):
    print(f"ABORT: {msg}")
    raise SystemExit(3)


def table_columns(cur, table):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]


def row_dict(cur, table, key_col, key_val):
    cols = table_columns(cur, table)
    row = cur.execute(
        f"SELECT {', '.join(cols)} FROM {table} WHERE {key_col} = ?",
        (key_val,),
    ).fetchone()
    return dict(zip(cols, row)) if row else None


def living_contexts(notes):
    out = []
    for m in re.finditer(r"living", notes, flags=re.IGNORECASE):
        start = max(0, m.start() - 45)
        end = min(len(notes), m.end() + 45)
        out.append(notes[start:end].replace("\n", " "))
    return out


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_lydia_unredact_package.py <db path>")
    db_path = Path(sys.argv[1])
    if not db_path.exists():
        fail(f"database not found: {db_path}")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = db_path.with_name(f"{db_path.name}.backup-{stamp}")
    shutil.copy2(db_path, backup)
    print(f"Backup written: {backup}")

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    gates = []

    def gate(name, ok):
        gates.append((name, bool(ok)))
        print(("PASS " if ok else "FAIL ") + name)
        if not ok:
            con.rollback()
            fail(f"gate failed: {name}")

    try:
        for table in ("persons", "sources", "facts"):
            if not table_columns(cur, table):
                fail(f"table missing: {table}")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS fact_quality_flags ("
            "fact_id INTEGER PRIMARY KEY, flag TEXT, note TEXT, "
            "applied_at TEXT)")

        pre = SPEC["expected_pre_state"]
        pspec = SPEC["person"]
        pid = pspec["person_id"]
        persons_now = cur.execute(
            "SELECT COUNT(*) FROM persons").fetchone()[0]
        sources_now = cur.execute(
            "SELECT COUNT(*) FROM sources").fetchone()[0]
        if persons_now != pre["persons"]:
            fail(f"persons {persons_now} != expected {pre['persons']}")
        if sources_now != pre["sources"]:
            fail(f"sources {sources_now} != expected {pre['sources']}")
        prow = row_dict(cur, "persons", "person_id", pid)
        if not prow or prow["name"] != pspec["name"]:
            fail(f"person {pid} is not {pspec['name']!r}")
        if prow["birth_info"] != pspec["expected_birth_info"]:
            fail(f"birth_info {prow['birth_info']!r} != expected "
                 f"{pspec['expected_birth_info']!r} (the obituary-dates "
                 f"package should have set it)")
        if prow["death_info"] != pspec["expected_death_info"]:
            fail(f"death_info {prow['death_info']!r} != expected "
                 f"{pspec['expected_death_info']!r}")
        print(f"Person verified: {pid} {pspec['name']}")
        print(f"Pre-state: persons {persons_now}, sources {sources_now}.")

        # ---- diagnostic: every 'living' occurrence -----------------------
        notes = prow["notes"] or ""
        contexts = living_contexts(notes)
        print(f"'living' occurrences in notes: {len(contexts)}")
        for i, ctx in enumerate(contexts, 1):
            print(f"  [{i}] ...{ctx}...")

        edit = SPEC["notes_edit"]
        old_phrase = edit["old_phrase"]
        new_phrase = edit["new_phrase"]
        phrase_count = notes.count(old_phrase)
        swapped = notes.replace(old_phrase, new_phrase)
        remaining = len(re.findall(r"living", swapped,
                                   flags=re.IGNORECASE))
        if phrase_count == 0 and remaining == 0:
            print("Notes already free of the trigger phrase; "
                  "no edit needed.")
            new_notes = notes
        else:
            if remaining != 0:
                fail(f"after swapping {phrase_count} occurrence(s) of "
                     f"{old_phrase!r}, {remaining} other 'living' "
                     f"instance(s) would remain; aborting for review "
                     f"rather than guessing at more wording")
            cur.execute(
                "UPDATE persons SET notes = ? WHERE person_id = ?",
                (swapped, pid),
            )
            new_notes = swapped
            print(f"Notes edited: {phrase_count} occurrence(s) of "
                  f"{old_phrase!r} -> {new_phrase!r}.")

        # ---- flags ---------------------------------------------------------
        for fspec in SPEC["flags"]:
            frow = row_dict(cur, "facts", "fact_id", fspec["fact_id"])
            if not frow or frow["person_id"] != pid:
                fail(f"flag fact {fspec['fact_id']} does not belong "
                     f"to {pid}")
            cur.execute(
                "INSERT OR IGNORE INTO fact_quality_flags "
                "(fact_id, flag, note, applied_at) VALUES (?, ?, ?, ?)",
                (fspec["fact_id"], fspec["flag"], fspec["note"],
                 fspec["applied_at"]),
            )
            print(f"Fact {fspec['fact_id']} flagged "
                  f"{fspec['flag']}.")

        # ---- final gates ---------------------------------------------------
        gate("persons total unchanged",
             cur.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
             == pre["persons"])
        gate("sources total unchanged",
             cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
             == pre["sources"])
        prow = row_dict(cur, "persons", "person_id", pid)
        gate("birth_info and death_info untouched",
             prow["birth_info"] == pspec["expected_birth_info"]
             and prow["death_info"] == pspec["expected_death_info"])
        final_notes = prow["notes"] or ""
        gate("notes contain no 'living' substring (case-insensitive)",
             len(re.findall(r"living", final_notes,
                            flags=re.IGNORECASE)) == 0)
        gate("notes equal the expected text (original, or phrase-swapped)",
             final_notes in (notes, new_notes)
             and (phrase_count == 0
                  or final_notes == notes.replace(old_phrase,
                                                   new_phrase)))
        gate("facts on 9334 = 5",
             cur.execute(
                 "SELECT COUNT(*) FROM facts WHERE person_id = ?",
                 (pid,)).fetchone()[0] == 5)
        for fspec in SPEC["flags"]:
            gate(f"fact {fspec['fact_id']} flagged",
                 cur.execute(
                     "SELECT COUNT(*) FROM fact_quality_flags "
                     "WHERE fact_id = ? AND flag = ?",
                     (fspec["fact_id"], fspec["flag"]),
                 ).fetchone()[0] == 1)
        gate("PRAGMA integrity_check",
             cur.execute("PRAGMA integrity_check").fetchone()[0] == "ok")

        con.commit()
        print(f"Final gates passed ({len(gates)} checks).")
        print("COMMITTED.")
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - rollback on any surprise
        con.rollback()
        fail(f"unexpected error, rolled back: {exc!r}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
