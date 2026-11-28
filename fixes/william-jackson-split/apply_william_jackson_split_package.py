#!/usr/bin/env python3
"""William Jackson (439) conflation split.

Profile 439 mixes at least four men named William Jackson.
Under Jequan Davis's ruling of 2026-11-22 it keeps exactly one:
William Jackson (b. 1931, d. 10 Dec 1971), son of Samuel and
Agnes Jackson. This package:

* Moves the GEDCOM-only cluster for William Edward Jackson Sr
  (Name/Birth/Death facts 10129/10130/10131) to a new profile
  built from the 2026-11-22 split research (register item 1:
  PROFILE HOLDS): b. Oct 1930 (7 Oct per SSDI-derived listings,
  9 Oct per the Mitsawokett pages; carried at month precision),
  d. 15 Jul 2003 Millsboro, buried Harmony Cemetery, son of
  Samuel Jackson (10725) and Agnes Beatrice Wright (9964),
  husband of Allece Dorene Clark (no profile yet; named in a
  Marriage fact and in the notes, not linked). The moved Birth
  fact is corrected to Oct 1930 / Millsboro and gains SSDI,
  Mitsawokett, and statement citations; its two cross-attached
  citations are marked SUPERSEDED. New Burial, Marriage, and
  Nickname ("Billy") facts are added, and the Hall obituary
  source is cited on the moved Name fact.
* Detaches all pre-1931 same-name material from 439 (27 facts:
  the two 1893 Ruth Both marriage facts and every Document
  Mention and Racial Classification fact, spanning 1746-1989),
  the spouse link to Ruth Both (11882, stored as reciprocal 'spouse' rows), and every photo row
  on 439 (the ruling packet found all of them are other
  subjects). Nothing is deleted from the record: detached
  material is written, with its citations, to
  unassigned_evidence_register.json beside this script.
* Moves 439's GEDCOM child_of link to Agnes Beatrice Wright
  (9964) onto the new profile (she is his mother per the
  research); 439 keeps its census-evidenced child_of links to
  Samuel Jackson (10725) and Agnes Jackson (11663) per the
  ruling.
* Marks six cross-attached citations SUPERSEDED in place
  (the 1746 baptism narrative riding on the 1931 man's Name,
  Birth, and Death facts and on the moved Birth fact; the 1950
  census boilerplate on the 1940 census fact; the 1971 man's
  vital-registration boilerplate on the moved Birth fact).
* Appends the split note to 439's notes.

Safety: hard gates abort (rollback) on any surprise;
idempotent (a second run is a no-op); backup written first;
the register file is written only after the commit succeeds.

Usage: python3 apply_william_jackson_split_package.py <path-to-db>
"""
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = json.loads(
    (HERE / "william_jackson_split_package.json").read_text(
        encoding="utf-8"))
REGISTER_PATH = HERE / "unassigned_evidence_register.json"
MARKER = (" [Marked SUPERSEDED by william-jackson-split package "
          "2026-11-27: ")

CITATION_TEXTS = {
    (10130, "ssdi"): (
        "SSDI-derived listings: William E Jackson, b. 7 Oct 1930, "
        "d. 15 Jul 2003, last residence Millsboro, Delaware (ZIP "
        "19966). Supports an October 1930 birth; the Mitsawokett "
        "pages give 9 Oct 1930, so the birth is carried at month "
        "precision."),
    (10130, "mitsawokett"): (
        "Mitsawokett family-history pages: William Edward Jackson "
        "Sr (Billy), b. 9 Oct 1930, son of Samuel Benton Jackson "
        "Sr and Agnes Beatrice Wright."),
    (10130, "statement"): (
        "Split research register item 1 (2026-11-22): the 2003 "
        "Millsboro cluster is a real, coherent man, William Edward "
        "Jackson Sr; this profile was created under Jequan "
        "Davis's conflation ruling of 2026-11-22."),
    (10131, "ssdi"): (
        "SSDI-derived listings: William E Jackson, d. 15 Jul 2003, "
        "last residence Millsboro, Delaware (ZIP 19966)."),
    (10129, "hall_obit"): (
        "Watson Funeral Home obituary of Betty Bernice (Jackson) "
        "Hall: names her parents as Samuel and Agnes Wright "
        "Jackson and lists her brother William Jackson among those "
        "who predeceased her, consistent with this man's parentage "
        "and his 2003 death."),
}
NEW_FACT_CITATION_TEXTS = {
    "Burial": ("Mitsawokett family-history pages: William Edward "
               "Jackson Sr buried 19 Jul 2003, Harmony Cemetery, "
               "Millsboro."),
    "Marriage": ("Mitsawokett family-history pages: William Edward "
                 "Jackson Sr married Allece Dorene Clark, daughter "
                 "of Walter Linford Clark and Arzelia Ellen Morris."),
    "Nickname": ("Mitsawokett family-history pages: William Edward "
                 "Jackson Sr was known as Billy."),
}


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


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_william_jackson_split_package.py <db path>")
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
                      "relationships", "person_photos",
                      "unified_photo_catalog"):
            if not table_columns(cur, table):
                fail(f"table missing: {table}")

        pre = SPEC["expected_pre_state"]
        post = SPEC["expected_post_state"]
        p439 = SPEC["person_439"]
        pid = p439["person_id"]
        keep_ids = [f["fact_id"] for f in p439["keep_facts"]]
        move_ids = [f["fact_id"] for f in SPEC["move_facts"]]
        detach_ids = [f["fact_id"] for f in SPEC["detach_facts"]]
        all_ids = keep_ids + move_ids + detach_ids

        persons_now = cur.execute(
            "SELECT COUNT(*) FROM persons").fetchone()[0]
        sources_now = cur.execute(
            "SELECT COUNT(*) FROM sources").fetchone()[0]
        prow = row_dict(cur, "persons", "person_id", pid)
        if not prow or prow["name"] != p439["name"]:
            fail(f"person {pid} is not {p439['name']!r}")
        if prow["birth_info"] != p439["expected_birth_info"]:
            fail(f"439 birth_info {prow['birth_info']!r} != expected "
                 f"{p439['expected_birth_info']!r}")
        if prow["death_info"] != p439["expected_death_info"]:
            fail(f"439 death_info {prow['death_info']!r} != expected")
        print(f"Person verified: {pid} {p439['name']}")

        facts_439 = {r["fact_id"]: r
                     for r in rows_where(cur, "facts", "person_id", pid)}
        nspec = SPEC["new_profile"]
        existing_new = cur.execute(
            "SELECT person_id FROM persons WHERE name = ?",
            (nspec["name"],)).fetchone()
        applied = (existing_new is not None
                   and sorted(facts_439) == sorted(keep_ids))
        if applied:
            if persons_now != post["persons"]:
                fail(f"applied state but persons {persons_now} != "
                     f"{post['persons']}")
            print("Package already applied; verifying only.")
        else:
            if persons_now != pre["persons"]:
                fail(f"persons {persons_now} != expected "
                     f"{pre['persons']}")
            if sources_now != pre["sources"]:
                fail(f"sources {sources_now} != expected "
                     f"{pre['sources']}")
            if sorted(facts_439) != sorted(all_ids):
                fail(f"439 fact set {sorted(facts_439)} != audited "
                     f"{sorted(all_ids)}")
            for entry in (p439["keep_facts"] + SPEC["move_facts"]
                          + SPEC["detach_facts"]):
                f = facts_439[entry["fact_id"]]
                if f["fact_type"] != entry["fact_type"]:
                    fail(f"fact {entry['fact_id']} type "
                         f"{f['fact_type']!r} != {entry['fact_type']!r}")
                exp_date = entry["date_string"]
                if entry["fact_id"] == 10130:
                    exp_date = ("abt 1931 Delaware"
                                if norm(f["date_string"])
                                == "abt 1931 Delaware" else exp_date)
                if norm(f["date_string"]) != norm(exp_date):
                    fail(f"fact {entry['fact_id']} date "
                         f"{f['date_string']!r} != {exp_date!r}")
            print(f"Pre-state: persons {persons_now}, sources "
                  f"{sources_now}, 439 facts {len(facts_439)}.")

        # relationships on 439 (pre-state check or applied check)
        rels_439 = {(r["relationship_type"], r["person_b_id"]): r
                    for r in rows_where(cur, "relationships",
                                        "person_a_id", pid)}
        if not applied:
            expected_rels = {(e["relationship_type"], e["person_b_id"])
                             for e in p439["relationships_expected"]}
            if set(rels_439) != expected_rels:
                fail(f"439 relationships {sorted(rels_439)} != "
                     f"expected {sorted(expected_rels)}")

        # ---- sources ---------------------------------------------------
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

        # ---- new profile -------------------------------------------------
        ref_level = row_dict(cur, "persons", "person_id",
                             nspec["evidence_level_from_person"])
        if not ref_level:
            fail("evidence_level reference profile missing")
        if existing_new:
            new_id = existing_new[0]
        else:
            cur.execute(
                "INSERT INTO persons (name, source_page, birth_info, "
                "death_info, notes, dataset_source, first_name, "
                "middle_name, suffix, evidence_level) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (nspec["name"], nspec["source_page"],
                 nspec["birth_info"], nspec["death_info"],
                 nspec["notes"], nspec["dataset_source"],
                 nspec["first_name"], nspec["middle_name"],
                 nspec["suffix"], ref_level["evidence_level"]))
            new_id = cur.lastrowid
            print(f"New profile created: {new_id} {nspec['name']}")

        # ---- move facts + birth correction ------------------------------
        for fid in move_ids:
            cur.execute(
                "UPDATE facts SET person_id = ? WHERE fact_id = ? "
                "AND person_id = ?", (new_id, fid, pid))
        bc = nspec["birth_correction"]
        cur.execute(
            "UPDATE facts SET date_string = ?, place_string = ? "
            "WHERE fact_id = ? AND person_id = ?",
            (bc["date_string"], bc["place_string"], bc["fact_id"],
             new_id))
        print(f"Facts moved to {new_id}: {move_ids}; birth fact "
              f"{bc['fact_id']} corrected to {bc['date_string']!r}.")

        # ---- supersede citations ------------------------------------------
        for cspec in SPEC["supersede_citations"]:
            crow = row_dict(cur, "citations", "citation_id",
                            cspec["citation_id"])
            if not crow or crow["fact_id"] != cspec["fact_id"]:
                fail(f"citation {cspec['citation_id']} does not "
                     f"belong to fact {cspec['fact_id']}")
            text = crow["evidence_text"] or ""
            if MARKER.strip() not in text:
                cur.execute(
                    "UPDATE citations SET evidence_text = ? WHERE "
                    "citation_id = ?",
                    (text + MARKER + cspec["reason"] + "]",
                     cspec["citation_id"]))
                print(f"Citation {cspec['citation_id']} marked "
                      f"SUPERSEDED.")

        # ---- extra + new-fact citations -----------------------------------
        def add_citation(fact_id, source_id, text):
            found = cur.execute(
                "SELECT COUNT(*) FROM citations WHERE fact_id = ? "
                "AND source_id = ?", (fact_id, source_id)).fetchone()[0]
            if not found:
                cur.execute(
                    "INSERT INTO citations (fact_id, source_id, "
                    "evidence_text) VALUES (?, ?, ?)",
                    (fact_id, source_id, text))

        for espec in nspec["extra_citations"]:
            for key in espec["source_keys"]:
                add_citation(espec["fact_id"], source_ids[key],
                             CITATION_TEXTS[(espec["fact_id"], key)])
        new_fact_ids = {}
        for fspec in nspec["new_facts"]:
            found = cur.execute(
                "SELECT fact_id FROM facts WHERE person_id = ? AND "
                "fact_type = ? AND IFNULL(date_string, '') = "
                "IFNULL(?, '') AND IFNULL(value_string, '') = "
                "IFNULL(?, '')",
                (new_id, fspec["fact_type"], fspec["date_string"],
                 fspec["value_string"])).fetchone()
            if found:
                new_fact_ids[fspec["fact_type"]] = found[0]
                continue
            cur.execute(
                "INSERT INTO facts (person_id, fact_type, "
                "date_string, place_string, value_string) VALUES "
                "(?, ?, ?, ?, ?)",
                (new_id, fspec["fact_type"], fspec["date_string"],
                 fspec["place_string"], fspec["value_string"]))
            new_fact_ids[fspec["fact_type"]] = cur.lastrowid
            print(f"New fact on {new_id}: {fspec['fact_type']} "
                  f"{new_fact_ids[fspec['fact_type']]}")
        for fspec in nspec["new_facts"]:
            for key in fspec["cite_source_keys"]:
                add_citation(new_fact_ids[fspec["fact_type"]],
                             source_ids[key],
                             NEW_FACT_CITATION_TEXTS[fspec["fact_type"]])

        # ---- relationships --------------------------------------------------
        orig_mother_row = rels_439.get(("child_of", 9964))
        for pspec in nspec["parents"]:
            target = row_dict(cur, "persons", "person_id",
                              pspec["person_b_id"])
            if not target or target["name"] != pspec["expected_name"]:
                fail(f"parent profile {pspec['person_b_id']} is not "
                     f"{pspec['expected_name']!r}")
            found = cur.execute(
                "SELECT COUNT(*) FROM relationships WHERE "
                "person_a_id = ? AND person_b_id = ? AND "
                "relationship_type = 'child_of'",
                (new_id, pspec["person_b_id"])).fetchone()[0]
            if not found:
                if pspec["person_b_id"] == 9964 and orig_mother_row:
                    ev = orig_mother_row["evidence_text"]
                    cert = orig_mother_row["certainty"]
                elif pspec["person_b_id"] == 10725:
                    ev = ("1940 US Federal Census household of Samuel "
                          "Jackson names son William E Jackson, age "
                          "9; split research register (2026-11-22) "
                          "identifies this man as the son of Samuel "
                          "Benton Jackson Sr.")
                    cert = "census_and_research"
                else:
                    ev = ("Split research register item 1 "
                          "(2026-11-22).")
                    cert = "researched"
                cur.execute(
                    "INSERT INTO relationships (person_a_id, "
                    "person_b_id, relationship_type, evidence_text, "
                    "certainty) VALUES (?, ?, 'child_of', ?, ?)",
                    (new_id, pspec["person_b_id"], ev, cert))
                print(f"New profile linked child_of "
                      f"{pspec['person_b_id']}.")

        register = {"package": SPEC["package"], "run_date":
                    SPEC["run_date"], "detached_from_person": pid,
                    "detached_facts": [], "detached_relationships": [],
                    "detached_photos": [], "moved_relationships": []}
        for rspec in SPEC["relationships_remove_from_439"]:
            key = (rspec["relationship_type"], rspec["person_b_id"])
            row = rels_439.get(key)
            if row:
                entry = {k: row[k] for k in
                         ("id", "person_a_id", "person_b_id",
                          "relationship_type", "evidence_text",
                          "certainty")}
                entry["disposition"] = rspec["disposition"]
                if rspec.get("reciprocal"):
                    recip = cur.execute(
                        "SELECT id, person_a_id, person_b_id, "
                        "relationship_type, evidence_text, certainty "
                        "FROM relationships WHERE person_a_id = ? "
                        "AND person_b_id = ? AND "
                        "relationship_type = ?",
                        (rspec["person_b_id"], pid,
                         rspec["relationship_type"])).fetchone()
                    if recip:
                        rcols = ["id", "person_a_id", "person_b_id",
                                 "relationship_type", "evidence_text",
                                 "certainty"]
                        entry["reciprocal_row"] = dict(
                            zip(rcols, recip))
                        cur.execute(
                            "DELETE FROM relationships WHERE id = ?",
                            (recip[0],))
                        print(f"439 reciprocal relationship removed: "
                              f"({rspec['person_b_id']} -> {pid}, "
                              f"{rspec['relationship_type']})")
                if rspec["disposition"] == "register":
                    register["detached_relationships"].append(entry)
                else:
                    register["moved_relationships"].append(entry)
                cur.execute("DELETE FROM relationships WHERE id = ?",
                            (row["id"],))
                print(f"439 relationship removed: {key} "
                      f"({rspec['disposition']})")

        # ---- photos ---------------------------------------------------------
        photo_rows = rows_where(cur, "person_photos", "person_id", pid)
        for prow_ in photo_rows:
            cat = row_dict(cur, "unified_photo_catalog", "photo_id",
                           prow_["photo_id"])
            register["detached_photos"].append({
                "person_photo_row": prow_,
                "catalog_title": (cat or {}).get("title_or_caption"),
                "catalog_filename": (cat or {}).get(
                    "normalized_filename")})
            cur.execute("DELETE FROM person_photos WHERE id = ?",
                        (prow_["id"],))
        if photo_rows:
            print(f"Detached {len(photo_rows)} photo row(s) from 439 "
                  f"(ruling packet: all are other subjects).")

        # ---- detach facts ---------------------------------------------------
        for fid in detach_ids:
            frow = row_dict(cur, "facts", "fact_id", fid)
            if frow and frow["person_id"] == pid:
                cits = rows_where(cur, "citations", "fact_id", fid)
                entry = dict(frow)
                entry["citations"] = cits
                register["detached_facts"].append(entry)
                cur.execute("DELETE FROM citations WHERE fact_id = ?",
                            (fid,))
                cur.execute("DELETE FROM facts WHERE fact_id = ?",
                            (fid,))
        if register["detached_facts"]:
            print(f"Detached {len(register['detached_facts'])} "
                  f"pre-1931 facts to the register.")

        # ---- notes append on 439 ---------------------------------------------
        prow = row_dict(cur, "persons", "person_id", pid)
        notes = prow["notes"] or ""
        if p439["notes_marker"] not in notes:
            cur.execute(
                "UPDATE persons SET notes = ? WHERE person_id = ?",
                ((notes + "\n" if notes else "")
                 + p439["notes_append"], pid))
            print("Split note appended to 439.")

        # ---- final gates -------------------------------------------------------
        gate("persons total = 3802",
             cur.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
             == post["persons"])
        gate("sources total = 2693",
             cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
             == post["sources"])
        gate("439 facts = the 6 kept facts",
             sorted(r["fact_id"] for r in rows_where(
                 cur, "facts", "person_id", pid)) == sorted(keep_ids))
        gate("new profile facts = 6 (3 moved + 3 new)",
             cur.execute(
                 "SELECT COUNT(*) FROM facts WHERE person_id = ?",
                 (new_id,)).fetchone()[0] == 6)
        gate("moved facts sit on the new profile",
             cur.execute(
                 "SELECT COUNT(*) FROM facts WHERE person_id = ? "
                 "AND fact_id IN (10129, 10130, 10131)",
                 (new_id,)).fetchone()[0] == 3)
        gate("birth fact 10130 corrected",
             (lambda r: r and r["date_string"] == bc["date_string"]
              and r["place_string"] == bc["place_string"])(
                 row_dict(cur, "facts", "fact_id", 10130)))
        gate("439 relationships = child_of 10725 + child_of 11663 "
             "+ cross_dataset_match 368 (retained)",
             {(r["relationship_type"], r["person_b_id"])
              for r in rows_where(cur, "relationships",
                                  "person_a_id", pid)}
             == {(e["relationship_type"], e["person_b_id"])
                 for e in p439["relationships_final"]})
        gate("no spouse rows touch 439 in either direction",
             cur.execute(
                 "SELECT COUNT(*) FROM relationships WHERE "
                 "(person_a_id = ? OR person_b_id = ?) AND "
                 "relationship_type = 'spouse'",
                 (pid, pid)).fetchone()[0] == 0)
        gate("new profile relationships = child_of 10725 + 9964",
             {(r["relationship_type"], r["person_b_id"])
              for r in rows_where(cur, "relationships",
                                  "person_a_id", new_id)}
             == {("child_of", 10725), ("child_of", 9964)})
        gate("439 has no photo rows",
             cur.execute(
                 "SELECT COUNT(*) FROM person_photos WHERE "
                 "person_id = ?", (pid,)).fetchone()[0] == 0)
        for cspec in SPEC["supersede_citations"]:
            gate(f"citation {cspec['citation_id']} SUPERSEDED",
                 MARKER.strip() in (row_dict(
                     cur, "citations", "citation_id",
                     cspec["citation_id"]) or {}).get(
                         "evidence_text", ""))
        gate("439 notes carry the split marker",
             p439["notes_marker"] in (row_dict(
                 cur, "persons", "person_id", pid)["notes"] or ""))
        gate("PRAGMA integrity_check",
             cur.execute("PRAGMA integrity_check").fetchone()[0]
             == "ok")

        con.commit()
        print(f"Final gates passed ({len(gates)} checks).")
        print("COMMITTED.")

        if register["detached_facts"] or register["detached_photos"] \
                or register["detached_relationships"]:
            REGISTER_PATH.write_text(
                json.dumps(register, indent=2, sort_keys=True),
                encoding="utf-8")
            print(f"Register written: {REGISTER_PATH} "
                  f"({len(register['detached_facts'])} facts, "
                  f"{len(register['detached_relationships'])} "
                  f"relationships, {len(register['detached_photos'])} "
                  f"photos)")
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
