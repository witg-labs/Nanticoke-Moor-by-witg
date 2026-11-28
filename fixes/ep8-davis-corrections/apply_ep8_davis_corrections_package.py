#!/usr/bin/env python3
"""Episode 8 Davis corrections package (2026-11-28).

Record-backed corrections for Ethel Gwendolyn Clark (8192) and her
husband Harry Edward Davis (8159), from the Episode 8 research of
28 Nov 2026:

* Eight new sources: Ethel's funeral program (Harmony United
  Methodist Church, Millsboro, 1997; text preserved in the
  Mitsawokett obituaries collection, contributed by Henrietta Carey
  Johnson), both spouses' Social Security NUMIDENT records, Harry's
  VA gravesite record, the 1920 and 1950 census households, the New
  Jersey Bride Index entry, and Harry's WWII draft card. Dataset
  values are copied from live reference sources (the William
  Jackson package's dataset_from_source mechanism) or the verified
  literal 'familysearch'.
* 8192: marriage fact 24387 gains its date (8 Apr 1938, from the
  funeral program) and loses its unproven 'Delaware' place (no
  Delaware marriage record was found in the 28 Nov 2026 searches;
  a New Jersey Bride Index entry for 1938 exists and the place is
  unproven); new Burial fact (Harmony United Methodist Church
  Cemetery) and new 1950 Census fact; research note appended.
* 8192: the child_of link to John Clark (3591) is detached to the
  unassigned-evidence register. No record names him as her father
  (her birth record names John W. Clark; her Social Security file
  names John Clarke), and a man who died in 1918 cannot be the
  father of her siblings born in the 1920s. Whether 3591 is a
  different man or a duplicate of John Wesley Clark Jr (8193)
  remains open; nothing else on 3591 or any sibling is touched.
* 8159: Birth fact 7595 'unknown' -> 22 Aug 1916 (NUMIDENT, VA
  record, draft card); Death fact 7596 '1 Feb 1932' -> 31 Jan 1999
  (the 1932 date is GEDCOM-layer error, disproven by his 1938
  marriage, his daughter's 1939 birth, his 1940 draft registration
  and WWII service, and both his VA and Social Security records);
  Burial fact 24332 place 'Delmarva' -> Harmony Cemetery,
  Millsboro; new 1920 and 1950 Census facts; person-row dates
  corrected; correction note appended. His parentage (Morris
  Davis and Hester Morris) is record-confirmed by the NUMIDENT
  record and the 1920 household.
* Photo 611 (Ethel's portrait): the catalog year '1916' is an
  import artifact (she was born in 1918 and the portrait shows an
  older woman; the same value on her husband's portrait 617 is
  his birth year). Wherever a photo catalog table carries a year
  for 611 it is set to 'unknown'; each table is gated on its own
  audited (approximate_year, dates_mentioned) pair:
  unified_photo_catalog carries '["1916"]' -> '[]', while
  photo_catalog carries NULL dates_mentioned, which stays NULL
  (amendment 2026-11-28, see SPEC.md). Photo 617 is snapshotted
  and gated unchanged.

Safety: schema-discovering for the photo tables; backup written
first; single transaction; hard gates abort (rollback) on any
surprise; idempotent (a second run verifies only and changes
nothing); the register file is written only after the commit
succeeds, and only when this run detached rows.

Preflight step (see SPEC.md): run audit_ep8.py against the live
database first; it prints the live child_of row id for the detach.
"expected_relationship_id" in the spec JSON is armed at 28818,
the row id the 2026-11-28 live audit reported (amendment
2026-11-28, see SPEC.md). An unarmed (null) run still detaches
on the evidence/certainty match but prints a warning; the
harness re-arms the id to its own mock row.

Usage: python3 apply_ep8_davis_corrections_package.py <path-to-db>
"""
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = json.loads(
    (HERE / "ep8_davis_corrections_package.json").read_text(
        encoding="utf-8"))
REGISTER_PATH = HERE / "unassigned_evidence_register.json"


def fail(msg):
    print(f"ABORT: {msg}")
    raise SystemExit(3)


def norm(v):
    return None if v in (None, "") else v


def table_columns(cur, table):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]


def row_dict(cur, table, key_col, key_val):
    cols = table_columns(cur, table)
    row = cur.execute(
        f"SELECT {', '.join(cols)} FROM {table} WHERE {key_col} = ?",
        (key_val,),
    ).fetchone()
    return dict(zip(cols, row)) if row else None


def rows_where(cur, table, col, val):
    cols = table_columns(cur, table)
    out = []
    for row in cur.execute(
            f"SELECT {', '.join(cols)} FROM {table} WHERE {col} = ?",
            (val,)):
        out.append(dict(zip(cols, row)))
    return out


def fact_key_match(cur, fspec):
    """Find a fact by the 4-field idempotency key (William pattern)."""
    return cur.execute(
        "SELECT fact_id FROM facts WHERE person_id = ? AND "
        "fact_type = ? AND IFNULL(date_string, '') = IFNULL(?, '') "
        "AND IFNULL(value_string, '') = IFNULL(?, '')",
        (fspec["person_id"], fspec["fact_type"],
         fspec["date_string"], fspec["value_string"])).fetchone()


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_ep8_davis_corrections_package.py <db path>")
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
        post = SPEC["expected_post_state"]
        p8192 = SPEC["persons"]["8192"]
        p8159 = SPEC["persons"]["8159"]
        det = SPEC["detach"]
        pfix = SPEC["photo_fix"]

        # ---------- person verification -------------------------------
        prow8192 = row_dict(cur, "persons", "person_id", 8192)
        if not prow8192 or prow8192["name"] != p8192["name"]:
            fail(f"person 8192 is not {p8192['name']!r}")
        if prow8192["birth_info"] != p8192["birth_info"]:
            fail(f"8192 birth_info {prow8192['birth_info']!r} != "
                 f"expected {p8192['birth_info']!r}")
        if prow8192["death_info"] != p8192["death_info"]:
            fail(f"8192 death_info {prow8192['death_info']!r} != "
                 f"expected {p8192['death_info']!r}")
        prow8159 = row_dict(cur, "persons", "person_id", 8159)
        if not prow8159 or prow8159["name"] != p8159["name"]:
            fail(f"person 8159 is not {p8159['name']!r}")
        if prow8159["birth_info"] not in (p8159["birth_info_from"],
                                          p8159["birth_info_to"]):
            fail(f"8159 birth_info {prow8159['birth_info']!r} is "
                 f"neither the audited pre-state nor the post-state")
        if prow8159["death_info"] not in (p8159["death_info_from"],
                                          p8159["death_info_to"]):
            fail(f"8159 death_info {prow8159['death_info']!r} is "
                 f"neither the audited pre-state nor the post-state")
        print("Persons verified: 8192 Ethel Gwendolyn Clark, "
              "8159 Harry Edward Davis")

        # ---------- relationship pre-state capture --------------------
        def rel_ids(pid):
            return {r[0] for r in cur.execute(
                "SELECT id FROM relationships WHERE person_a_id = ? "
                "OR person_b_id = ?", (pid, pid))}

        rel_pre_8192 = rel_ids(8192)
        rel_pre_8159 = rel_ids(8159)

        pair_rows = [dict(zip(
            ["id", "person_a_id", "person_b_id", "relationship_type",
             "evidence_text", "certainty"], r)) for r in cur.execute(
            "SELECT id, person_a_id, person_b_id, relationship_type, "
            "evidence_text, certainty FROM relationships WHERE "
            "(person_a_id = ? AND person_b_id = ?) OR "
            "(person_a_id = ? AND person_b_id = ?)",
            (det["person_a_id"], det["person_b_id"],
             det["person_b_id"], det["person_a_id"]))]
        primary_rows = [r for r in pair_rows
                        if r["person_a_id"] == det["person_a_id"]
                        and r["person_b_id"] == det["person_b_id"]
                        and r["relationship_type"]
                        == det["primary"]["relationship_type"]]
        reciprocal_rows = [r for r in pair_rows
                           if r["person_a_id"] == det["person_b_id"]
                           and r["person_b_id"] == det["person_a_id"]
                           and r["relationship_type"]
                           == det["reciprocal"]["relationship_type"]]
        other_pair_rows = [r for r in pair_rows
                           if r not in primary_rows
                           and r not in reciprocal_rows]
        if other_pair_rows:
            fail(f"unexpected relationship rows between 8192 and "
                 f"3591: {other_pair_rows}")
        if len(primary_rows) > 1:
            fail(f"multiple child_of rows 8192 -> 3591: "
                 f"{primary_rows}")
        if len(reciprocal_rows) > 1:
            fail(f"multiple parent_of rows 3591 -> 8192: "
                 f"{reciprocal_rows}")
        if not primary_rows and reciprocal_rows:
            fail("orphan reciprocal parent_of row 3591 -> 8192 "
                 "with no primary child_of row; stop-on-surprise")

        # ---------- photo pre-state (schema-discovering) --------------
        photo_tables = []
        for tname in pfix["tables"]:
            cols = table_columns(cur, tname)
            if not cols:
                print(f"Photo table {tname}: not present, skipped.")
                continue
            if "approximate_year" not in cols \
                    or "dates_mentioned" not in cols \
                    or "photo_id" not in cols:
                print(f"Photo table {tname}: no year columns, "
                      f"skipped.")
                continue
            row611 = row_dict(cur, tname, "photo_id",
                              pfix["photo_id"])
            if row611 is None:
                print(f"Photo table {tname}: does not carry photo "
                      f"{pfix['photo_id']}.")
                continue
            photo_tables.append((tname, row611))
        if not photo_tables:
            fail("neither photo catalog table carries a year for "
                 f"photo {pfix['photo_id']}; aborting")
        photo617_before = {}
        for tname, _ in photo_tables:
            r617 = row_dict(cur, tname, "photo_id",
                            pfix["untouched_photo_id"])
            if r617 is not None:
                photo617_before[tname] = dict(r617)

        # ---------- applied detection ---------------------------------
        def fact_matches_post(fspec_edit):
            f = row_dict(cur, "facts", "fact_id",
                         fspec_edit["fact_id"])
            if not f:
                return False
            return all(norm(f[k]) == norm(v)
                       for k, v in fspec_edit["set"].items())

        sources_exist = all(
            cur.execute("SELECT 1 FROM sources WHERE title = ?",
                        (s["title"],)).fetchone()
            for s in SPEC["new_sources"])
        applied = (
            sources_exist
            and all(fact_matches_post(e) for e in SPEC["fact_edits"])
            and prow8159["birth_info"] == p8159["birth_info_to"]
            and prow8159["death_info"] == p8159["death_info_to"]
            and all(fact_key_match(cur, f) for f in SPEC["new_facts"])
            and not pair_rows
            and all(na["marker"] in (row_dict(
                cur, "persons", "person_id",
                na["person_id"])["notes"] or "")
                for na in SPEC["notes_appends"])
            and all(r["approximate_year"]
                    == pfix["per_table"][t]["post"]["approximate_year"]
                    and r["dates_mentioned"]
                    == pfix["per_table"][t]["post"]["dates_mentioned"]
                    for t, r in photo_tables))

        persons_now = cur.execute(
            "SELECT COUNT(*) FROM persons").fetchone()[0]
        sources_now = cur.execute(
            "SELECT COUNT(*) FROM sources").fetchone()[0]
        if applied:
            if persons_now != post["persons"]:
                fail(f"applied state but persons {persons_now} != "
                     f"{post['persons']}")
            if sources_now != post["sources"]:
                fail(f"applied state but sources {sources_now} != "
                     f"{post['sources']}")
            print("Package already applied; verifying only.")
        else:
            if persons_now != pre["persons"]:
                fail(f"persons {persons_now} != expected "
                     f"{pre['persons']}")
            if sources_now != pre["sources"]:
                fail(f"sources {sources_now} != expected "
                     f"{pre['sources']}")
            for pspec in (p8192, p8159):
                got = sorted(r["fact_id"] for r in rows_where(
                    cur, "facts", "person_id", pspec["person_id"]))
                if got != sorted(pspec["facts_pre"]):
                    fail(f"facts on {pspec['person_id']} {got} != "
                         f"audited {sorted(pspec['facts_pre'])}")
            for na in SPEC["notes_appends"]:
                nrow = row_dict(cur, "persons", "person_id",
                                na["person_id"])
                if na["marker"] in (nrow["notes"] or ""):
                    fail(f"notes marker already present on "
                         f"{na['person_id']} but the package is not "
                         f"fully applied; stop-on-surprise")
            if not primary_rows:
                fail("child_of row 8192 -> 3591 not found and the "
                     "package is not fully applied; stop-on-surprise")
            print(f"Pre-state: persons {persons_now}, sources "
                  f"{sources_now}, facts 8192 "
                  f"{len(p8192['facts_pre'])}, facts 8159 "
                  f"{len(p8159['facts_pre'])}.")

        # ---------- fact edit guards (both modes) ----------------------
        for espec in SPEC["fact_edits"]:
            f = row_dict(cur, "facts", "fact_id", espec["fact_id"])
            if not f or f["person_id"] != espec["person_id"]:
                fail(f"fact {espec['fact_id']} does not belong to "
                     f"person {espec['person_id']}")
            if f["fact_type"] != espec["fact_type"]:
                fail(f"fact {espec['fact_id']} type "
                     f"{f['fact_type']!r} != {espec['fact_type']!r}")
            for field, allowed in espec["guard"].items():
                if f[field] not in allowed:
                    fail(f"fact {espec['fact_id']} {field} "
                         f"{f[field]!r} is none of the allowed "
                         f"values {allowed!r}; stop-on-surprise")

        # ---------- sources --------------------------------------------
        source_ids = {}
        for sspec in SPEC["new_sources"]:
            row = cur.execute(
                "SELECT source_id FROM sources WHERE title = ?",
                (sspec["title"],)).fetchone()
            if row:
                source_ids[sspec["key"]] = row[0]
                continue
            if "dataset_from_source" in sspec:
                ref = row_dict(cur, "sources", "source_id",
                               sspec["dataset_from_source"])
                if not ref:
                    fail(f"dataset reference source "
                         f"{sspec['dataset_from_source']} missing")
                dataset = ref["dataset"]
            else:
                dataset = sspec["dataset"]
            cur.execute(
                "INSERT INTO sources (title, url, dataset) "
                "VALUES (?, ?, ?)",
                (sspec["title"], sspec["url"], dataset))
            source_ids[sspec["key"]] = cur.lastrowid
            print(f"Source created ({sspec['key']}): "
                  f"{source_ids[sspec['key']]}")

        # ---------- citations ------------------------------------------
        def add_citation(fact_id, source_id, text):
            found = cur.execute(
                "SELECT COUNT(*) FROM citations WHERE fact_id = ? "
                "AND source_id = ?", (fact_id, source_id)).fetchone()[0]
            if not found:
                cur.execute(
                    "INSERT INTO citations (fact_id, source_id, "
                    "evidence_text) VALUES (?, ?, ?)",
                    (fact_id, source_id, text))

        # ---------- fact edits ------------------------------------------
        for espec in SPEC["fact_edits"]:
            f = row_dict(cur, "facts", "fact_id", espec["fact_id"])
            changes = {k: v for k, v in espec["set"].items()
                       if f[k] != v}
            if changes:
                assignments = ", ".join(f"{k} = ?" for k in changes)
                cur.execute(
                    f"UPDATE facts SET {assignments} "
                    f"WHERE fact_id = ?",
                    (*changes.values(), espec["fact_id"]))
                print(f"Fact {espec['fact_id']} edited: "
                      f"{sorted(changes)}")
            for cspec in espec["add_citations"]:
                add_citation(espec["fact_id"],
                             source_ids[cspec["source_key"]],
                             cspec["evidence_text"])

        # ---------- new facts --------------------------------------------
        new_fact_ids = {}
        for fspec in SPEC["new_facts"]:
            found = fact_key_match(cur, fspec)
            if found:
                new_fact_ids[id(fspec)] = found[0]
                continue
            cur.execute(
                "INSERT INTO facts (person_id, fact_type, "
                "date_string, place_string, value_string) VALUES "
                "(?, ?, ?, ?, ?)",
                (fspec["person_id"], fspec["fact_type"],
                 fspec["date_string"], fspec["place_string"],
                 fspec["value_string"]))
            new_fact_ids[id(fspec)] = cur.lastrowid
            print(f"New fact on {fspec['person_id']}: "
                  f"{fspec['fact_type']} {fspec['date_string']!r} "
                  f"-> {cur.lastrowid}")
        for fspec in SPEC["new_facts"]:
            for cspec in fspec["citations"]:
                add_citation(new_fact_ids[id(fspec)],
                             source_ids[cspec["source_key"]],
                             cspec["evidence_text"])

        # ---------- person row 8159 ---------------------------------------
        prow8159 = row_dict(cur, "persons", "person_id", 8159)
        if prow8159["birth_info"] != p8159["birth_info_to"] \
                or prow8159["death_info"] != p8159["death_info_to"]:
            cur.execute(
                "UPDATE persons SET birth_info = ?, death_info = ? "
                "WHERE person_id = ?",
                (p8159["birth_info_to"], p8159["death_info_to"], 8159))
            print("Person 8159 dates corrected: "
                  f"{p8159['birth_info_to']} / "
                  f"{p8159['death_info_to']}")

        # ---------- notes appends -----------------------------------------
        for na in SPEC["notes_appends"]:
            nrow = row_dict(cur, "persons", "person_id",
                            na["person_id"])
            notes = nrow["notes"] or ""
            if na["marker"] not in notes:
                cur.execute(
                    "UPDATE persons SET notes = ? "
                    "WHERE person_id = ?",
                    ((notes + "\n\n" if notes else "") + na["text"],
                     na["person_id"]))
                print(f"Research note appended to {na['person_id']}.")

        # ---------- detach --------------------------------------------------
        register = {"package": SPEC["package"],
                    "run_date": SPEC["run_date"],
                    "detached_from_person": det["person_a_id"],
                    "detached_facts": [],
                    "detached_relationships": [],
                    "detached_photos": [],
                    "moved_relationships": []}
        detached_ids = []
        if primary_rows:
            prim = primary_rows[0]
            if prim["evidence_text"] != det["primary"]["evidence_text"]:
                fail(f"child_of row {prim['id']} evidence_text "
                     f"{prim['evidence_text']!r} != expected "
                     f"{det['primary']['evidence_text']!r}")
            if prim["certainty"] != det["primary"]["certainty"]:
                fail(f"child_of row {prim['id']} certainty "
                     f"{prim['certainty']!r} != expected "
                     f"{det['primary']['certainty']!r}")
            expected_id = det.get("expected_relationship_id")
            if expected_id is not None:
                if prim["id"] != expected_id:
                    fail(f"child_of row id {prim['id']} != armed "
                         f"expected_relationship_id {expected_id}")
            else:
                print("WARNING: expected_relationship_id is null "
                      "(unarmed); detaching the discovered row "
                      f"{prim['id']} on evidence/certainty match.")
            entry = {k: prim[k] for k in
                     ("id", "person_a_id", "person_b_id",
                      "relationship_type", "evidence_text",
                      "certainty")}
            entry["disposition"] = "register"
            entry["reason"] = det["reason"]
            if reciprocal_rows:
                entry["reciprocal_row"] = {
                    k: reciprocal_rows[0][k] for k in
                    ("id", "person_a_id", "person_b_id",
                     "relationship_type", "evidence_text",
                     "certainty")}
                cur.execute("DELETE FROM relationships "
                            "WHERE id = ?",
                            (reciprocal_rows[0]["id"],))
                detached_ids.append(reciprocal_rows[0]["id"])
                print(f"Reciprocal parent_of row removed: "
                      f"{reciprocal_rows[0]['id']} "
                      f"(3591 -> 8192)")
            cur.execute("DELETE FROM relationships WHERE id = ?",
                        (prim["id"],))
            detached_ids.append(prim["id"])
            register["detached_relationships"].append(entry)
            print(f"child_of row removed: {prim['id']} "
                  f"(8192 -> 3591), recorded in the register.")

        # ---------- photo fix ----------------------------------------------
        for tname, row611 in photo_tables:
            texp = pfix["per_table"][tname]
            cur_vals = (row611["approximate_year"],
                        row611["dates_mentioned"])
            pre_vals = (texp["pre"]["approximate_year"],
                        texp["pre"]["dates_mentioned"])
            post_vals = (texp["post"]["approximate_year"],
                         texp["post"]["dates_mentioned"])
            if cur_vals == post_vals:
                print(f"{tname}: photo 611 already corrected.")
            elif cur_vals == pre_vals:
                if post_vals[1] is not None:
                    cur.execute(
                        f"UPDATE {tname} SET approximate_year = ?, "
                        f"dates_mentioned = ? WHERE photo_id = ?",
                        (*post_vals, pfix["photo_id"]))
                else:
                    cur.execute(
                        f"UPDATE {tname} SET approximate_year = ? "
                        f"WHERE photo_id = ?",
                        (post_vals[0], pfix["photo_id"]))
                print(f"{tname}: photo 611 year "
                      f"{pre_vals[0]!r} -> {post_vals[0]!r}.")
            else:
                fail(f"{tname}: photo 611 year values {cur_vals!r} "
                     f"are neither the audited pre-state nor the "
                     f"post-state; stop-on-surprise")

        # ---------- final gates ----------------------------------------------
        gate("persons total = 3807",
             cur.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
             == post["persons"])
        gate("sources total = 2701",
             cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
             == post["sources"])
        gate("8192 facts = 8 (6 audited + 2 new)",
             cur.execute("SELECT COUNT(*) FROM facts "
                         "WHERE person_id = 8192").fetchone()[0]
             == p8192["facts_post_count"])
        gate("8159 facts = 9 (7 audited + 2 new)",
             cur.execute("SELECT COUNT(*) FROM facts "
                         "WHERE person_id = 8159").fetchone()[0]
             == p8159["facts_post_count"])
        gate("fact 24387 read-back: date '8 Apr 1938', place empty",
             (lambda r: r and r["date_string"] == "8 Apr 1938"
              and norm(r["place_string"]) is None)(
                 row_dict(cur, "facts", "fact_id", 24387)))
        gate("fact 7596 read-back: date '31 Jan 1999'",
             (lambda r: r and r["date_string"] == "31 Jan 1999")(
                 row_dict(cur, "facts", "fact_id", 7596)))
        gate("fact 7595 read-back: corrected birth date",
             (lambda r: r and r["date_string"]
              == "22 Aug 1916 Millsboro, Sussex, Delaware, USA")(
                 row_dict(cur, "facts", "fact_id", 7595)))
        gate("fact 24332 read-back: Harmony Cemetery, Millsboro",
             (lambda r: r and r["date_string"] == "1999"
              and r["place_string"]
              == "Harmony Cemetery, Millsboro, Sussex, Delaware, USA")(
                 row_dict(cur, "facts", "fact_id", 24332)))
        for fspec in SPEC["new_facts"]:
            gate(f"new fact read-back: {fspec['person_id']} "
                 f"{fspec['fact_type']} {fspec['date_string']!r}",
                 fact_key_match(cur, fspec) is not None)
        gate("8159 person row dates corrected",
             (lambda r: r["birth_info"] == p8159["birth_info_to"]
              and r["death_info"] == p8159["death_info_to"])(
                 row_dict(cur, "persons", "person_id", 8159)))
        gate("no relationship rows remain between 8192 and 3591",
             cur.execute(
                 "SELECT COUNT(*) FROM relationships WHERE "
                 "(person_a_id = 8192 AND person_b_id = 3591) OR "
                 "(person_a_id = 3591 AND person_b_id = 8192)"
                 ).fetchone()[0] == 0)
        gate("8192 relationship id set = pre-state minus detached",
             rel_ids(8192) == rel_pre_8192 - set(detached_ids))
        gate("8159 relationship id set unchanged",
             rel_ids(8159) == rel_pre_8159)
        for na in SPEC["notes_appends"]:
            gate(f"notes marker on {na['person_id']}",
                 na["marker"] in (row_dict(
                     cur, "persons", "person_id",
                     na["person_id"])["notes"] or ""))
        for tname, _ in photo_tables:
            tpost = pfix["per_table"][tname]["post"]
            gate(f"{tname}: photo 611 in post-state",
                 (lambda r: r["approximate_year"]
                  == tpost["approximate_year"]
                  and r["dates_mentioned"]
                  == tpost["dates_mentioned"])(
                     row_dict(cur, tname, "photo_id",
                              pfix["photo_id"])))
            if tname in photo617_before:
                gate(f"{tname}: photo 617 unchanged",
                     row_dict(cur, tname, "photo_id",
                              pfix["untouched_photo_id"])
                     == photo617_before[tname])
        gate("PRAGMA integrity_check",
             cur.execute("PRAGMA integrity_check").fetchone()[0]
             == "ok")

        con.commit()
        print(f"Final gates passed ({len(gates)} checks).")
        print("COMMITTED.")

        if register["detached_relationships"]:
            REGISTER_PATH.write_text(
                json.dumps(register, indent=2, sort_keys=True),
                encoding="utf-8")
            print(f"Register written: {REGISTER_PATH} "
                  f"({len(register['detached_relationships'])} "
                  f"relationship(s))")
        else:
            print("No detachments this run (already applied); "
                  "register file left as it stands.")
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - rollback on any surprise
        con.rollback()
        fail(f"unexpected error, rolled back: {exc!r}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
