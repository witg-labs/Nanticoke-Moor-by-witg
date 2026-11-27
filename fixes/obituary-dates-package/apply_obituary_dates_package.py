#!/usr/bin/env python3
"""Obituary-override date-correction batch package.

Applies Jequan Davis's obituary-override rule (2026-11-23: a funeral
program or obituary he supplies beats the archive's dates for the same
person) to six profiles, plus the Lydia E Norwood birth-year
correction settled by the 1850 census analysis filed 2026-11-23:

- Annabell Thompson (8212): birth 28 Oct 1928 Temperanceville VA,
  death 21 Aug 2001 (funeral program; former 1925 / 24 Aug 2001
  citations marked SUPERSEDED; SS-5 and Marriage facts flagged).
- George A. Davis (8157): the 1912 Birth and Dec 1923 Death facts
  (a child George Davis) detached to the register as a pair; new
  Death fact Sep 1986 and Burial corrected to Harmony Cemetery,
  interment 12 Sep 1986 (Watson service card); Marriage flagged.
- Hersel R. Davis (8158): new Death fact 9 Aug 2005, Green Valley
  Terrace, Millsboro (program + memorial card + newspaper obituary;
  the program cover's July 9 is a misprint); Burial corrected to
  Harmony Cemetery; death_info fixed. His duplicated infant facts
  are a separate conflation item and are NOT touched.
- Pearl Mae Thompson (8863): birth 16 Mar 1916, Millsboro (memorial
  card + newspaper obituary; former 'abt 1917' citations SUPERSEDED;
  SS-5 and Marriage facts flagged).
- Delphine Mae Davis (8182): birth 6 Oct 1939, death 20 Aug 2002
  (funeral program; the 1918-1968 dates and the Valhalla Gardens
  Find a Grave memorial belong to a different woman: that citation
  and the impossible 1920 Census fact are detached to the register;
  SS-5 and Marriage facts flagged).
- Sheila Kathleen Davis (8248): birth 9 Feb 1939, death 5 Aug 2010
  (funeral program; the 1953-2021 dates and the Sheila Hill Davis
  memorial belong to a different woman: that burial citation is
  detached to the register; SS-5 and Marriage facts flagged).
- Lydia E Norwood (9334): birth year abt 1768 -> abt 1790 on the
  1850 census (Indian River Hundred, dwelling 32, age 60), with
  1768 and the gravestone's implied abt 1781 recorded in her notes
  as conflicting accounts. Her Birth fact is discovered dynamically
  and her full database state is printed for the record, because
  her export is currently redacted.

Safety: schema discovered at runtime; hard gates abort (rollback)
on any surprise; idempotent (a second run is a no-op); backup
written first; the register file is written only after a
successful commit.

Usage: python3 apply_obituary_dates_package.py <path-to-db>
"""
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = json.loads(
    (HERE / "obituary_dates_package.json").read_text(encoding="utf-8"))
REGISTER_PATH = HERE / "unassigned_evidence_register.json"
SUPERSEDED_PREFIX = "SUPERSEDED (obituary-dates package, 2026-11-27): "


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


def find_or_create_source(cur, dataset, title, url=""):
    row = cur.execute(
        "SELECT source_id FROM sources WHERE dataset = ? AND title = ?",
        (dataset, title),
    ).fetchone()
    if row:
        return row[0], False
    cur.execute(
        "INSERT INTO sources (title, url, dataset) VALUES (?, ?, ?)",
        (title, url, dataset),
    )
    return cur.lastrowid, True


def ensure_citation(cur, fact_id, source_id, evidence_text):
    row = cur.execute(
        "SELECT citation_id FROM citations WHERE fact_id = ? AND source_id = ?",
        (fact_id, source_id),
    ).fetchone()
    if row:
        return row[0], False
    cur.execute(
        "INSERT INTO citations (fact_id, source_id, evidence_text) "
        "VALUES (?, ?, ?)",
        (fact_id, source_id, evidence_text),
    )
    return cur.lastrowid, True


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_obituary_dates_package.py <db path>")
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
    register_additions = []
    sources_created = 0

    def gate(name, ok):
        gates.append((name, bool(ok)))
        print(("PASS " if ok else "FAIL ") + name)
        if not ok:
            con.rollback()
            fail(f"gate failed: {name}")

    try:
        for table in ("persons", "sources", "facts", "citations"):
            if not table_columns(cur, table):
                fail(f"table missing: {table}")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS fact_quality_flags ("
            "fact_id INTEGER PRIMARY KEY, flag TEXT, note TEXT, "
            "applied_at TEXT)")

        pre = SPEC["expected_pre_state"]
        persons_now = cur.execute(
            "SELECT COUNT(*) FROM persons").fetchone()[0]
        sources_now = cur.execute(
            "SELECT COUNT(*) FROM sources").fetchone()[0]
        fresh = persons_now == pre["persons"] and sources_now in (
            pre["sources"], pre["sources"] + 6)
        if persons_now != pre["persons"]:
            fail(f"persons {persons_now} != expected {pre['persons']}")
        print(f"Pre-state: persons {persons_now}, sources {sources_now}.")

        final_counts = {}

        # ---- the six obituary-override profiles -------------------------
        for pspec in SPEC["persons"]:
            pid = pspec["person_id"]
            prow = row_dict(cur, "persons", "person_id", pid)
            if not prow or prow["name"] != pspec["name"]:
                fail(f"person {pid} is not {pspec['name']!r}")
            pre_count = cur.execute(
                "SELECT COUNT(*) FROM facts WHERE person_id = ?",
                (pid,)).fetchone()[0]
            if ("expected_facts_count" in pspec
                    and pre_count not in (
                        pspec["expected_facts_count"],
                        pspec["expected_facts_count"]
                        + len(pspec["new_facts"])
                        - len(pspec["detach_facts"]))):
                fail(f"facts on {pid} {pre_count} != expected "
                     f"{pspec['expected_facts_count']}")
            applied = (
                (pspec["new_birth_info"] is None
                 or prow["birth_info"] == pspec["new_birth_info"])
                and (pspec["new_death_info"] is None
                     or prow["death_info"] == pspec["new_death_info"])
                and pspec["notes_marker"] in (prow["notes"] or ""))
            if not applied:
                if prow["birth_info"] != pspec["expected_birth_info"]:
                    fail(f"{pid} birth_info {prow['birth_info']!r} != "
                         f"expected {pspec['expected_birth_info']!r}")
                if prow["death_info"] != pspec["expected_death_info"]:
                    fail(f"{pid} death_info {prow['death_info']!r} != "
                         f"expected {pspec['expected_death_info']!r}")
            final_counts[pid] = (
                pre_count if applied else
                pre_count + len(pspec["new_facts"])
                - len(pspec["detach_facts"]))
            print(f"Person verified: {pid} {pspec['name']} "
                  f"({pre_count} facts).")

            sspec = pspec["source"]
            source_id, s_created = find_or_create_source(
                cur, sspec["dataset"], sspec["title"], sspec.get("url", ""))
            sources_created += 1 if s_created else 0
            print(f"  Source {'created' if s_created else 'found'}: "
                  f"{source_id} - {sspec['title'][:60]}")

            for cspec in pspec["corrections"]:
                frow = row_dict(cur, "facts", "fact_id", cspec["fact_id"])
                if (not frow or frow["person_id"] != pid
                        or frow["fact_type"] != cspec["fact_type"]):
                    fail(f"fact {cspec['fact_id']} shape mismatch")
                cur.execute(
                    "UPDATE facts SET date_string = ?, place_string = ?, "
                    "value_string = ? WHERE fact_id = ?",
                    (cspec["date_string"], cspec["place_string"],
                     cspec["value_string"], cspec["fact_id"]),
                )
                ensure_citation(cur, cspec["fact_id"], source_id,
                                cspec["citation_evidence"])
                print(f"  {cspec['fact_type']} fact {cspec['fact_id']} "
                      f"corrected.")

            for sspec2 in pspec["supersede_citations"]:
                crow = row_dict(cur, "citations", "citation_id",
                                sspec2["citation_id"])
                if crow is None:
                    fail(f"citation {sspec2['citation_id']} missing")
                old = crow["evidence_text"] or ""
                if not old.startswith(SUPERSEDED_PREFIX):
                    new = SUPERSEDED_PREFIX + sspec2["note"]
                    if old:
                        new += f" Original text: {old}"
                    cur.execute(
                        "UPDATE citations SET evidence_text = ? "
                        "WHERE citation_id = ?",
                        (new, sspec2["citation_id"]),
                    )
                    print(f"  Citation {sspec2['citation_id']} marked "
                          f"SUPERSEDED.")

            for dspec in pspec["detach_citations"]:
                crow = row_dict(cur, "citations", "citation_id",
                                dspec["citation_id"])
                if crow is not None:
                    register_additions.append({
                        "kind": "citation",
                        "person_id": pid,
                        "detached_from_fact_id": dspec["fact_id"],
                        "citation": crow,
                        "reason": dspec["reason"],
                    })
                    cur.execute(
                        "DELETE FROM citations WHERE citation_id = ?",
                        (dspec["citation_id"],))
                    print(f"  Citation {dspec['citation_id']} detached "
                          f"to the register.")

            for dspec in pspec["detach_facts"]:
                frow = row_dict(cur, "facts", "fact_id", dspec["fact_id"])
                if frow is not None:
                    if frow["person_id"] != pid:
                        fail(f"detach fact {dspec['fact_id']} belongs to "
                             f"{frow['person_id']}, not {pid}")
                    cites = [row_dict(cur, "citations", "citation_id", cid)
                             for cid in dspec["citation_ids"]]
                    register_additions.append({
                        "kind": "fact",
                        "person_id": pid,
                        "fact": frow,
                        "citations": cites,
                        "reason": dspec["reason"],
                    })
                    cur.execute(
                        "DELETE FROM citations WHERE fact_id = ?",
                        (dspec["fact_id"],))
                    cur.execute(
                        "DELETE FROM facts WHERE fact_id = ?",
                        (dspec["fact_id"],))
                    print(f"  Fact {dspec['fact_id']} detached to the "
                          f"register with its {len(cites)} citations.")

            for nspec in pspec["new_facts"]:
                existing = cur.execute(
                    "SELECT fact_id FROM facts WHERE person_id = ? "
                    "AND fact_type = ? AND date_string IS ?",
                    (pid, nspec["fact_type"], nspec["date_string"]),
                ).fetchone()
                if existing:
                    fact_id = existing[0]
                else:
                    cur.execute(
                        "INSERT INTO facts (person_id, fact_type, "
                        "date_string, place_string, value_string) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (pid, nspec["fact_type"], nspec["date_string"],
                         nspec["place_string"], nspec["value_string"]),
                    )
                    fact_id = cur.lastrowid
                    print(f"  New {nspec['fact_type']} fact created: "
                          f"{fact_id} ({nspec['date_string']}).")
                ensure_citation(cur, fact_id, source_id,
                                nspec["citation_evidence"])

            for fspec in pspec["flags"]:
                cur.execute(
                    "INSERT OR IGNORE INTO fact_quality_flags "
                    "(fact_id, flag, note, applied_at) "
                    "VALUES (?, ?, ?, ?)",
                    (fspec["fact_id"], fspec["flag"], fspec["note"],
                     SPEC["run_date"]),
                )
            if pspec["flags"]:
                print(f"  {len(pspec['flags'])} fact(s) flagged "
                      f"generic_unverified.")

            updates = {}
            if pspec["new_birth_info"] is not None:
                updates["birth_info"] = pspec["new_birth_info"]
            if pspec["new_death_info"] is not None:
                updates["death_info"] = pspec["new_death_info"]
            if updates:
                set_sql = ", ".join(f"{k} = ?" for k in updates)
                cur.execute(
                    f"UPDATE persons SET {set_sql} WHERE person_id = ?",
                    (*updates.values(), pid),
                )
            prow = row_dict(cur, "persons", "person_id", pid)
            notes = prow["notes"] or ""
            if pspec["notes_marker"] not in notes:
                new_notes = (notes.rstrip() + "\n" + pspec["notes_append"]
                             if notes.strip() else pspec["notes_append"])
                cur.execute(
                    "UPDATE persons SET notes = ? WHERE person_id = ?",
                    (new_notes, pid),
                )
                print(f"  Correction notes appended to {pid}.")

        # ---- Lydia E Norwood (9334), dynamic discovery -------------------
        lspec = SPEC["lydia"]
        lid = lspec["person_id"]
        lrow = row_dict(cur, "persons", "person_id", lid)
        if not lrow or lrow["name"] != lspec["name"]:
            fail(f"person {lid} is not {lspec['name']!r}")
        print(f"Person verified: {lid} {lspec['name']}.")
        print(f"  DB birth_info: {lrow['birth_info']!r}; "
              f"death_info: {lrow['death_info']!r}")
        print(f"  DB notes: {(lrow['notes'] or '')!r}")
        lfact_ids_before = [r[0] for r in cur.execute(
            "SELECT fact_id FROM facts WHERE person_id = ?", (lid,))]
        for fid in lfact_ids_before:
            f = row_dict(cur, "facts", "fact_id", fid)
            print(f"  DB fact {fid}: {f['fact_type']} | "
                  f"{f['date_string']!r} | {f['place_string']!r} | "
                  f"{(f['value_string'] or '')[:60]!r}")
        frag = lspec["old_year_fragment"]
        birth_facts = [row_dict(cur, "facts", "fact_id", fid)
                       for fid in lfact_ids_before
                       if row_dict(cur, "facts", "fact_id", fid)[
                           "fact_type"] == "Birth"]
        targets = [f for f in birth_facts
                   if frag in (f["date_string"] or "")]
        already = [f for f in birth_facts
                   if (f["date_string"] or "") == lspec["new_birth_date"]]
        if len(targets) > 1:
            fail(f"Lydia: {len(targets)} Birth facts carry {frag}; "
                 f"expected at most one")
        if not targets and not already:
            fail(f"Lydia: no Birth fact carries {frag} and none reads "
                 f"{lspec['new_birth_date']!r}; aborting for review")
        census_id, c_created = find_or_create_source(
            cur, lspec["census_source"]["dataset"],
            lspec["census_source"]["title"],
            lspec["census_source"].get("url", ""))
        sources_created += 1 if c_created else 0
        print(f"  Census source {'created' if c_created else 'found'}: "
              f"{census_id}")
        target_fact = targets[0] if targets else already[0]
        if targets:
            old_date = target_fact["date_string"] or ""
            new_place = target_fact["place_string"]
            if not new_place and "Sussex" in old_date:
                new_place = lspec["new_place_if_date_held_it"]
            cur.execute(
                "UPDATE facts SET date_string = ?, place_string = ? "
                "WHERE fact_id = ?",
                (lspec["new_birth_date"], new_place,
                 target_fact["fact_id"]),
            )
            print(f"  Birth fact {target_fact['fact_id']} corrected: "
                  f"{old_date!r} -> {lspec['new_birth_date']!r}.")
        ensure_citation(cur, target_fact["fact_id"], census_id,
                        lspec["citation_evidence"])
        if frag in (lrow["birth_info"] or ""):
            cur.execute(
                "UPDATE persons SET birth_info = ? WHERE person_id = ?",
                (lspec["new_birth_info"], lid),
            )
            print(f"  birth_info corrected to "
                  f"{lspec['new_birth_info']!r}.")
        lrow = row_dict(cur, "persons", "person_id", lid)
        lnotes = lrow["notes"] or ""
        if lspec["notes_marker"] not in lnotes:
            new_notes = (lnotes.rstrip() + "\n" + lspec["notes_append"]
                         if lnotes.strip() else lspec["notes_append"])
            cur.execute(
                "UPDATE persons SET notes = ? WHERE person_id = ?",
                (new_notes, lid),
            )
            print(f"  Conflict notes appended to {lid}.")

        # ---- final gates ---------------------------------------------------
        gate("persons total unchanged",
             cur.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
             == pre["persons"])
        gate("sources delta equals sources created this run",
             cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
             - sources_now == sources_created)
        for pspec in SPEC["persons"]:
            pid = pspec["person_id"]
            prow = row_dict(cur, "persons", "person_id", pid)
            ok = True
            if pspec["new_birth_info"] is not None:
                ok = ok and prow["birth_info"] == pspec["new_birth_info"]
            if pspec["new_death_info"] is not None:
                ok = ok and prow["death_info"] == pspec["new_death_info"]
            gate(f"{pid} person fields carry the corrected values", ok)
            gate(f"{pid} fact count as expected",
                 cur.execute(
                     "SELECT COUNT(*) FROM facts WHERE person_id = ?",
                     (pid,)).fetchone()[0] == final_counts[pid])
            for cspec in pspec["corrections"]:
                frow = row_dict(cur, "facts", "fact_id", cspec["fact_id"])
                gate(f"{pid} fact {cspec['fact_id']} corrected",
                     frow["date_string"] == cspec["date_string"]
                     and frow["place_string"] == cspec["place_string"]
                     and frow["value_string"] == cspec["value_string"])
            for sspec2 in pspec["supersede_citations"]:
                crow = row_dict(cur, "citations", "citation_id",
                                sspec2["citation_id"])
                gate(f"citation {sspec2['citation_id']} SUPERSEDED",
                     crow is not None
                     and (crow["evidence_text"] or "").startswith(
                         SUPERSEDED_PREFIX))
            for dspec in pspec["detach_citations"]:
                gate(f"citation {dspec['citation_id']} detached",
                     cur.execute(
                         "SELECT COUNT(*) FROM citations "
                         "WHERE citation_id = ?",
                         (dspec["citation_id"],)).fetchone()[0] == 0)
            for dspec in pspec["detach_facts"]:
                gate(f"fact {dspec['fact_id']} detached",
                     cur.execute(
                         "SELECT COUNT(*) FROM facts WHERE fact_id = ?",
                         (dspec["fact_id"],)).fetchone()[0] == 0)
            for nspec in pspec["new_facts"]:
                gate(f"{pid} new {nspec['fact_type']} fact present",
                     cur.execute(
                         "SELECT COUNT(*) FROM facts WHERE person_id = ? "
                         "AND fact_type = ? AND date_string IS ?",
                         (pid, nspec["fact_type"],
                          nspec["date_string"])).fetchone()[0] == 1)
            for fspec in pspec["flags"]:
                gate(f"fact {fspec['fact_id']} flagged",
                     cur.execute(
                         "SELECT COUNT(*) FROM fact_quality_flags "
                         "WHERE fact_id = ? AND flag = ?",
                         (fspec["fact_id"], fspec["flag"]),
                     ).fetchone()[0] == 1)
            gate(f"{pid} correction notes present",
                 pspec["notes_marker"] in (prow["notes"] or ""))
        lrow = row_dict(cur, "persons", "person_id", lid)
        gate("Lydia fact count unchanged",
             cur.execute(
                 "SELECT COUNT(*) FROM facts WHERE person_id = ?",
                 (lid,)).fetchone()[0] == len(lfact_ids_before))
        lf = row_dict(cur, "facts", "fact_id", target_fact["fact_id"])
        gate("Lydia Birth fact reads abt 1790",
             lf["date_string"] == lspec["new_birth_date"])
        gate("Lydia Birth fact cited to the 1850 census source",
             cur.execute(
                 "SELECT COUNT(*) FROM citations WHERE fact_id = ? "
                 "AND source_id = ?",
                 (target_fact["fact_id"], census_id)).fetchone()[0] == 1)
        gate("Lydia conflict notes present",
             lspec["notes_marker"] in (lrow["notes"] or ""))
        gate("register entries this run are the full set or zero",
             len(register_additions) in (0, 5))
        gate("PRAGMA integrity_check",
             cur.execute("PRAGMA integrity_check").fetchone()[0] == "ok")

        con.commit()
        print(f"Final gates passed ({len(gates)} checks).")
        print(f"Field changes this run: sources created "
              f"{sources_created}, register entries "
              f"{len(register_additions)}.")

        if register_additions:
            existing_register = []
            if REGISTER_PATH.exists():
                existing_register = json.loads(
                    REGISTER_PATH.read_text(encoding="utf-8"))
            existing_register.extend(register_additions)
            REGISTER_PATH.write_text(
                json.dumps(existing_register, indent=2), encoding="utf-8")
            print(f"Register updated: {REGISTER_PATH} "
                  f"(+{len(register_additions)} entries).")
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
