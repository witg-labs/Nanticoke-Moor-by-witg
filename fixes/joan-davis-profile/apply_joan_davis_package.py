#!/usr/bin/env python3
"""Joan Ellen Davis living-profile package.

Creates ONE new person (Joan Ellen Davis, living: birth_info/death_info
'unknown', no Birth or Death fact, per the archive's living-people rule),
links her to her parents William Wesley Davis Sr (8609) and Phoebe
Thompson (8146), and adds two cited facts (Name, 1950 Census). One new
source: Jequan Davis's 2026-11-27 family-knowledge statement.

Safety: schema discovered at runtime; hard gates abort (rollback) on any
surprise; idempotent (a second run is a no-op); backup written first.

Usage: python3 apply_joan_davis_package.py <path-to-genealogy_preservation.db>
"""
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "joan_davis_package.json").read_text(encoding="utf-8"))


def fail(msg):
    print(f"ABORT: {msg}")
    raise SystemExit(3)


def table_columns(cur, table):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]


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


def find_or_create_fact(cur, person_id, spec):
    row = cur.execute(
        "SELECT fact_id FROM facts WHERE person_id = ? AND fact_type = ? "
        "AND value_string IS ?",
        (person_id, spec["fact_type"], spec["value_string"]),
    ).fetchone()
    if row:
        return row[0], False
    cur.execute(
        "INSERT INTO facts (person_id, fact_type, date_string, place_string, "
        "value_string, place_id) VALUES (?, ?, ?, ?, ?, NULL)",
        (
            person_id,
            spec["fact_type"],
            spec["date_string"],
            spec["place_string"],
            spec["value_string"],
        ),
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


def ensure_relationship(cur, child_id, parent_id, rel_type, evidence, certainty):
    row = cur.execute(
        "SELECT id FROM relationships WHERE "
        "((person_a_id = ? AND person_b_id = ?) OR "
        " (person_a_id = ? AND person_b_id = ?)) AND relationship_type = ?",
        (child_id, parent_id, parent_id, child_id, rel_type),
    ).fetchone()
    if row:
        return row[0], False
    cur.execute(
        "INSERT INTO relationships (person_a_id, person_b_id, "
        "relationship_type, evidence_text, certainty) VALUES (?, ?, ?, ?, ?)",
        (child_id, parent_id, rel_type, evidence, certainty),
    )
    return cur.lastrowid, True


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_joan_davis_package.py <db path>")
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
        for table in ("persons", "sources", "facts", "citations",
                      "relationships"):
            if not table_columns(cur, table):
                fail(f"table missing: {table}")

        pre = SPEC["expected_pre_state"]
        pspec = SPEC["person"]

        # ---- pre-state verification -------------------------------------
        persons_now = cur.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
        sources_now = cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        max_id_now = cur.execute(
            "SELECT MAX(person_id) FROM persons").fetchone()[0]
        existing = cur.execute(
            "SELECT person_id FROM persons WHERE name = ?",
            (pspec["name"],),
        ).fetchone()
        fresh = existing is None
        if fresh:
            if persons_now != pre["persons"]:
                fail(f"persons count {persons_now} != expected {pre['persons']}")
            if max_id_now != pre["max_person_id"]:
                fail(f"max person_id {max_id_now} != expected "
                     f"{pre['max_person_id']}")
            if sources_now != pre["sources"]:
                fail(f"sources count {sources_now} != expected {pre['sources']}")
        for pid, want in SPEC["verify_persons"].items():
            row = cur.execute(
                "SELECT name FROM persons WHERE person_id = ?",
                (int(pid),),
            ).fetchone()
            if not row or row[0] != want:
                fail(f"person {pid} is {row!r}, expected {want!r}")
        for sid, want in SPEC["verify_sources"].items():
            row = cur.execute(
                "SELECT title, dataset FROM sources WHERE source_id = ?",
                (int(sid),),
            ).fetchone()
            if not row:
                fail(f"source {sid} missing")
            if "title" in want and row[0] != want["title"]:
                fail(f"source {sid} title {row[0]!r} != {want['title']!r}")
            if "dataset" in want and row[1] != want["dataset"]:
                fail(f"source {sid} dataset {row[1]!r} != {want['dataset']!r}")
        print("Persons verified: " + ", ".join(
            f"{pid} {name}" for pid, name in SPEC["verify_persons"].items()))
        print(f"Pre-state: persons {persons_now}, sources {sources_now}, "
              f"max person_id {max_id_now}, Joan exists: {not fresh}.")

        # ---- statement source -------------------------------------------
        sspec = SPEC["statement_source"]
        statement_id, s_created = find_or_create_source(
            cur, sspec["dataset"], sspec["title"], sspec.get("url", ""))
        print(f"Source {'created' if s_created else 'found'}: "
              f"{statement_id} - {sspec['title'][:60]}")

        # ---- create the person (fresh run) -------------------------------
        if fresh:
            cols = table_columns(cur, "persons")
            values = {
                "name": pspec["name"],
                "birth_info": pspec["birth_info"],
                "death_info": pspec["death_info"],
                "notes": pspec["notes"],
                "dataset_source": pspec["dataset_source"],
                "first_name": pspec["first_name"],
                "middle_name": pspec["middle_name"],
                "maiden_name": pspec["maiden_name"],
                "evidence_level": pspec["evidence_level"],
            }
            use = {k: v for k, v in values.items() if k in cols}
            col_sql = ", ".join(use.keys())
            ph = ", ".join("?" for _ in use)
            cur.execute(
                f"INSERT INTO persons ({col_sql}) VALUES ({ph})",
                tuple(use.values()),
            )
            joan_id = cur.lastrowid
            print(f"Person created: {joan_id} {pspec['name']}")
        else:
            joan_id = existing[0]
            print(f"Person found: {joan_id} {pspec['name']}")

        # ---- facts --------------------------------------------------------
        facts_created = 0
        for fspec in SPEC["facts"]:
            fid, f_created = find_or_create_fact(cur, joan_id, fspec)
            facts_created += 1 if f_created else 0
            cite = fspec["cite"]
            if cite == "statement":
                src_id = statement_id
            elif cite.startswith("source:"):
                src_id = int(cite.split(":", 1)[1])
            else:
                fail(f"unknown cite target: {cite}")
            _, c_created = ensure_citation(
                cur, fid, src_id, fspec["evidence_text"])
            print(f"{'Fact created' if f_created else 'Fact found'} on "
                  f"{joan_id}: {fid} ({fspec['fact_type']})"
                  + (f"; citation added from source {src_id}" if c_created
                     else ""))

        # ---- relationships --------------------------------------------------
        rels_created = 0
        for rspec in SPEC["relationships"]:
            _, r_created = ensure_relationship(
                cur, joan_id, rspec["parent_id"], rspec["relationship_type"],
                rspec["evidence_text"], rspec["certainty"])
            rels_created += 1 if r_created else 0
            print(f"{'Parent link created' if r_created else 'Parent link found'}"
                  f": {joan_id} child_of {rspec['parent_id']}.")

        # ---- final gates ----------------------------------------------------
        persons_after = cur.execute(
            "SELECT COUNT(*) FROM persons").fetchone()[0]
        sources_after = cur.execute(
            "SELECT COUNT(*) FROM sources").fetchone()[0]
        gate("person id is the expected new id",
             joan_id == SPEC["expected_new_person_id"])
        gate("persons total = pre + 1",
             persons_after == pre["persons"] + 1)
        gate("sources delta equals sources created this run",
             sources_after - sources_now == (1 if s_created else 0))
        prow = cur.execute(
            "SELECT birth_info, death_info, dataset_source, evidence_level "
            "FROM persons WHERE person_id = ?", (joan_id,)).fetchone()
        gate("living fields: birth_info and death_info are 'unknown'",
             prow and prow[0] == "unknown" and prow[1] == "unknown")
        gate("no Birth or Death fact on the living profile",
             cur.execute(
                 "SELECT COUNT(*) FROM facts WHERE person_id = ? AND "
                 "fact_type IN ('Birth', 'Death')", (joan_id,)
             ).fetchone()[0] == 0)
        gate("facts on Joan = 2",
             cur.execute(
                 "SELECT COUNT(*) FROM facts WHERE person_id = ?",
                 (joan_id,)).fetchone()[0] == 2)
        for fspec in SPEC["facts"]:
            row = cur.execute(
                "SELECT f.fact_id FROM facts f JOIN citations c "
                "ON c.fact_id = f.fact_id WHERE f.person_id = ? AND "
                "f.fact_type = ?", (joan_id, fspec["fact_type"])).fetchone()
            gate(f"{fspec['fact_type']} fact present and cited: "
                 f"{fspec['key']}", row is not None)
        gate("relationships touching Joan = 2",
             cur.execute(
                 "SELECT COUNT(*) FROM relationships WHERE "
                 "person_a_id = ? OR person_b_id = ?", (joan_id, joan_id)
             ).fetchone()[0] == 2)
        for rspec in SPEC["relationships"]:
            row = cur.execute(
                "SELECT id FROM relationships WHERE "
                "((person_a_id = ? AND person_b_id = ?) OR "
                " (person_a_id = ? AND person_b_id = ?)) AND "
                "relationship_type = ?",
                (joan_id, rspec["parent_id"], rspec["parent_id"], joan_id,
                 rspec["relationship_type"])).fetchone()
            gate(f"parent link present: {joan_id} child_of "
                 f"{rspec['parent_id']}", row is not None)
        gate("facts created this run are the full set or zero",
             facts_created in (0, len(SPEC["facts"])))
        gate("relationships created this run are the full set or zero",
             rels_created in (0, len(SPEC["relationships"])))
        gate("PRAGMA integrity_check",
             cur.execute("PRAGMA integrity_check").fetchone()[0] == "ok")

        con.commit()
        print(f"Final gates passed ({len(gates)} checks).")
        print(f"Field changes this run: person created "
              f"{1 if fresh else 0}, sources created "
              f"{1 if s_created else 0}, facts created {facts_created}, "
              f"relationships created {rels_created}.")
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
