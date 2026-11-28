#!/usr/bin/env python3
"""John Clark 3591 untangle package (2026-11-28).

Profile 3591 ("John Clark") merged two men separated by more
than a century:

* the John Clark of the Revolutionary-era Sussex County Clark
  family (son of Levin Clark in the family tree; the tree also
  places the same sibling set under Thomas Clark and Elizabeth
  Morris), born in the 1780s (tree variants 1783 and 1789) and
  died 1834; and
* John Wesley Clark Jr (8193, 1894-1964), husband of Lulu Rae
  Carey and father of her children, whose 1930 census household,
  spouse link, and child links the archive's enrichment attached
  to 3591 as well.

The "d. 1918" on 3591 belongs to neither man (1834 vs 1964) and
rests on enrichment boilerplate quoting no record.

This package keeps the 18th-century man on 3591 and removes
everything that belongs to Jr:

* deletes the spouse rows between 3591 and 8194 (Lulu Rae
  Clark), discovered in both directions (spouse storage is not
  uniform: single forward row or reciprocal pair);
* deletes the child_of / parent_of rows between 3591 and each
  of 8195, 8210, 8196, 8207 (a stored parent_of reciprocal may
  or may not exist per child, per the 9928 lesson);
* moves fact 16058 (the 1930 census household) from 3591 to
  8193, marking its two boilerplate citations SUPERSEDED in
  place (the real 1930 citation 14868 stays live);
* detaches fact 19493 (boilerplate Marriage) and facts 15220 /
  15255 (name-match Document Mentions that cannot be this man)
  to the unassigned-evidence register;
* corrects fact 11986 (Death) 1918 -> 1834 and marks its two
  citations SUPERSEDED in place;
* rewrites the person row: death_info 1834, source_page and
  dataset_source aligned to the GEDCOM source (mirroring
  profile 9622), and the ingest note replaced by the untangle
  note.

Kept untouched: fact 2967 (Name), fact 15454 (the 1834 sibling
document mention, which matches his own family), both GEDCOM
child_of parent links (9350 Levin Clark, 8514 Elizabeth
Morris), everything on 8193 except the moved fact, everything
on 8194 except the shared spouse rows, everything on the
children except their rows to 3591, and any cross_dataset_match
rows touching 3591 (ignored by design, per the 439 lesson).

DEPENDENCY (hard gate): the ep8-davis-corrections package
deletes the child_of row (8192 -> 3591). If any relationship
row between 8192 and 3591 still exists, this package aborts:
Ep8 runs first.

Safety: backup written first; single transaction; hard gates
abort (rollback) on any surprise; idempotent (a second run
verifies only and changes nothing); the register file is
written only after the commit succeeds, and only when this run
detached or moved something.

Preflight step (see SPEC.md): run audit_3591.py against the
live database first; it prints every relationship row this
package will delete, with ids. Fill those ids into each
removal's "expected_ids" in the spec JSON to arm the id gate
before running this script on the live database. Shipped as
null (unarmed) so the simulation harness can prove both paths;
an unarmed run prints a warning.

Usage: python3 apply_john_clark_3591_untangle_package.py <db>
"""
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = json.loads(
    (HERE / "john_clark_3591_untangle_package.json").read_text(
        encoding="utf-8"))
REGISTER_PATH = HERE / "unassigned_evidence_register.json"
TARGET = SPEC["target_person"]["person_id"]
MARKER = "[Untangled 2026-11-28"
SUPERSEDED_TAG = "Marked SUPERSEDED by john-clark-3591-untangle package"


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


def rows_where(cur, table, col, val):
    cols = table_columns(cur, table)
    out = []
    for row in cur.execute(
            f"SELECT {', '.join(cols)} FROM {table} WHERE {col} = ?",
            (val,)):
        out.append(dict(zip(cols, row)))
    return out


def rel_rows_between(cur, a, b):
    cols = table_columns(cur, "relationships")
    out = []
    for row in cur.execute(
            f"SELECT {', '.join(cols)} FROM relationships WHERE "
            "(person_a_id = ? AND person_b_id = ?) OR "
            "(person_a_id = ? AND person_b_id = ?) ORDER BY id",
            (a, b, b, a)):
        out.append(dict(zip(cols, row)))
    return out


def rel_ids(cur, pid):
    return {r[0] for r in cur.execute(
        "SELECT id FROM relationships WHERE person_a_id = ? "
        "OR person_b_id = ?", (pid, pid))}


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_john_clark_3591_untangle_package.py "
             "<db path>")
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

        tp = SPEC["target_person"]
        p8193 = SPEC["person_8193"]
        ref9622 = SPEC["reference_9622"]
        dep = SPEC["dependency"]
        ignored_types = set(SPEC["ignored_relationship_types"])
        move = SPEC["fact_move"]

        # ---------- dependency gate (Ep8 runs first) ----------------
        dep_rows = rel_rows_between(cur, dep["pair"][0],
                                    dep["pair"][1])
        if dep_rows:
            fail(f"EP8 DEPENDENCY: {dep['message']}; rows present: "
                 f"{[(r['id'], r['relationship_type']) for r in dep_rows]}")

        # ---------- person verification ------------------------------
        prow = row_dict(cur, "persons", "person_id", TARGET)
        if not prow or prow["name"] != tp["name"]:
            fail(f"person {TARGET} is not {tp['name']!r}")
        for field in ("death_info", "source_page", "dataset_source",
                      "notes"):
            if prow[field] not in (tp["pre"][field], tp["post"][field]):
                fail(f"{TARGET} {field} {prow[field]!r} is neither "
                     f"the audited pre-state nor the post-state")
        if prow["birth_info"] is not None:
            fail(f"{TARGET} birth_info {prow['birth_info']!r} != "
                 f"audited null")
        prow8193 = row_dict(cur, "persons", "person_id", 8193)
        if not prow8193 or prow8193["name"] != p8193["name"]:
            fail(f"person 8193 is not {p8193['name']!r}")
        ref = row_dict(cur, "persons", "person_id",
                       ref9622["person_id"])
        if not ref:
            fail(f"reference person {ref9622['person_id']} missing")
        if ref["source_page"] != ref9622["source_page"] \
                or ref["dataset_source"] != ref9622["dataset_source"]:
            fail(f"reference 9622 source_page/dataset_source "
                 f"{ref['source_page']!r}/{ref['dataset_source']!r} "
                 f"!= audited {ref9622['source_page']!r}/"
                 f"{ref9622['dataset_source']!r}; stop-on-surprise")
        if tp["post"]["dataset_source"] != ref["dataset_source"] \
                or tp["post"]["source_page"] != ref["source_page"]:
            fail("spec post-state does not mirror reference 9622; "
                 "stop-on-surprise")
        print(f"Persons verified: {TARGET} John Clark, 8193 John "
              f"Wesley Clark Jr, reference 9622 John Wesley Clark Sr")

        # ---------- relationship discovery ---------------------------
        def discover(rem):
            rows = rel_rows_between(cur, TARGET, rem["other_id"])
            ignored = [r for r in rows
                       if r["relationship_type"] in ignored_types]
            deletable = [r for r in rows
                         if r["relationship_type"]
                         in rem["allowed_types"]]
            unexpected = [r for r in rows
                          if r not in ignored and r not in deletable]
            return rows, ignored, deletable, unexpected

        discoveries = {}
        for rem in SPEC["relationship_removals"]:
            rows, ignored, deletable, unexpected = discover(rem)
            if unexpected:
                fail(f"unexpected relationship rows between "
                     f"{TARGET} and {rem['other_id']}: "
                     f"{[(r['id'], r['relationship_type']) for r in unexpected]}")
            if rem["kind"] == "child":
                for r in deletable:
                    if r["relationship_type"] == "child_of" and not (
                            r["person_a_id"] == rem["other_id"]
                            and r["person_b_id"] == TARGET):
                        fail(f"child_of row {r['id']} has an "
                             f"unexpected direction for pair "
                             f"{TARGET}/{rem['other_id']}")
                    if r["relationship_type"] == "parent_of" and not (
                            r["person_a_id"] == TARGET
                            and r["person_b_id"] == rem["other_id"]):
                        fail(f"parent_of row {r['id']} has an "
                             f"unexpected direction for pair "
                             f"{TARGET}/{rem['other_id']}")
                primaries = [r for r in deletable
                             if r["relationship_type"] == "child_of"]
                reciprocals = [r for r in deletable
                               if r["relationship_type"] == "parent_of"]
            else:  # spouse: either direction is a primary storage row
                primaries = deletable
                reciprocals = []
                if len(deletable) > 2:
                    fail(f"more than two spouse rows between "
                         f"{TARGET} and {rem['other_id']}: "
                         f"{[r['id'] for r in deletable]}")
                if len(deletable) == 2 and \
                        deletable[0]["person_a_id"] == \
                        deletable[1]["person_a_id"]:
                    fail(f"two spouse rows between {TARGET} and "
                         f"{rem['other_id']} stored in the same "
                         f"direction; stop-on-surprise")
            if rem["kind"] == "child":
                if len(primaries) > 1:
                    fail(f"multiple child_of rows {rem['other_id']} "
                         f"-> {TARGET}: {[r['id'] for r in primaries]}")
                if len(reciprocals) > 1:
                    fail(f"multiple parent_of rows {TARGET} -> "
                         f"{rem['other_id']}: "
                         f"{[r['id'] for r in reciprocals]}")
                if reciprocals and not primaries:
                    fail(f"orphan reciprocal parent_of row "
                         f"{TARGET} -> {rem['other_id']} with no "
                         f"primary child_of row; stop-on-surprise")
            discoveries[rem["key"]] = {
                "rem": rem, "rows": rows, "ignored": ignored,
                "deletable": deletable, "primaries": primaries,
                "reciprocals": reciprocals}

        # ---------- relationship pre-state capture ---------------------
        watched = [TARGET, 8193, 8194] + [
            rem["other_id"] for rem in SPEC["relationship_removals"]
            if rem["kind"] == "child"]
        rel_pre = {pid: rel_ids(cur, pid) for pid in watched}
        sources_pre = cur.execute(
            "SELECT COUNT(*) FROM sources").fetchone()[0]
        persons_pre = cur.execute(
            "SELECT COUNT(*) FROM persons").fetchone()[0]

        # ---------- applied detection ----------------------------------
        def citation_has_tag(cid):
            c = row_dict(cur, "citations", "citation_id", cid)
            return bool(c) and SUPERSEDED_TAG in (c["evidence_text"]
                                                  or "")

        f11986 = row_dict(cur, "facts", "fact_id", 11986)
        fmove = row_dict(cur, "facts", "fact_id", move["fact_id"])
        applied = (
            prow["death_info"] == tp["post"]["death_info"]
            and prow["source_page"] == tp["post"]["source_page"]
            and prow["dataset_source"] == tp["post"]["dataset_source"]
            and MARKER in (prow["notes"] or "")
            and f11986 is not None
            and f11986["date_string"] == "1834"
            and f11986["value_string"]
            == SPEC["fact_edits"][0]["set"]["value_string"]
            and all(citation_has_tag(cs["citation_id"])
                    for cs in SPEC["fact_edits"][0]
                    ["supersede_citations"])
            and fmove is not None
            and fmove["person_id"] == move["to_person_id"]
            and all(citation_has_tag(cs["citation_id"])
                    for cs in move["supersede_citations"])
            and all(row_dict(cur, "facts", "fact_id",
                             d["fact_id"]) is None
                    for d in SPEC["fact_detaches"])
            and all(not discoveries[rem["key"]]["deletable"]
                    for rem in SPEC["relationship_removals"]))

        if applied:
            if persons_pre != SPEC["expected_post_state"]["persons"]:
                fail(f"applied state but persons {persons_pre} != "
                     f"{SPEC['expected_post_state']['persons']}")
            print("Package already applied; verifying only.")
        else:
            if persons_pre != SPEC["expected_pre_state"]["persons"]:
                fail(f"persons {persons_pre} != expected "
                     f"{SPEC['expected_pre_state']['persons']}")
            for field in ("death_info", "source_page",
                          "dataset_source", "notes"):
                if prow[field] != tp["pre"][field]:
                    fail(f"{TARGET} {field} {prow[field]!r} != "
                         f"audited pre-state {tp['pre'][field]!r} "
                         f"and the package is not fully applied; "
                         f"stop-on-surprise")
            got = sorted(r["fact_id"] for r in rows_where(
                cur, "facts", "person_id", TARGET))
            if got != sorted(tp["facts_pre"]):
                fail(f"facts on {TARGET} {got} != audited "
                     f"{sorted(tp['facts_pre'])}")
            got8193 = sorted(r["fact_id"] for r in rows_where(
                cur, "facts", "person_id", 8193))
            if got8193 != sorted(p8193["facts_pre"]):
                fail(f"facts on 8193 {got8193} != audited "
                     f"{sorted(p8193['facts_pre'])}")
            for rem in SPEC["relationship_removals"]:
                disc = discoveries[rem["key"]]
                if not disc["primaries"]:
                    fail(f"no primary relationship row found for "
                         f"removal {rem['key']} and the package is "
                         f"not fully applied; stop-on-surprise")
                prim = rem["primary"]
                if not any(
                        prim["evidence_contains"]
                        in (r["evidence_text"] or "")
                        and r["certainty"] == prim["certainty"]
                        for r in disc["primaries"]):
                    fail(f"no primary row for removal {rem['key']} "
                         f"carries the audited evidence "
                         f"({prim['evidence_contains']!r}, certainty "
                         f"{prim['certainty']!r}); stop-on-surprise")
                if rem.get("expected_ids") is not None:
                    found = {r["id"] for r in disc["deletable"]}
                    if found != set(rem["expected_ids"]):
                        fail(f"removal {rem['key']}: discovered row "
                             f"ids {sorted(found)} != armed "
                             f"expected_ids "
                             f"{sorted(rem['expected_ids'])}")
                else:
                    print(f"WARNING: removal {rem['key']} "
                          f"expected_ids is null (unarmed); deleting "
                          f"the discovered rows "
                          f"{[r['id'] for r in disc['deletable']]} "
                          f"on type/parties/evidence match.")
            print(f"Pre-state: persons {persons_pre}, sources "
                  f"{sources_pre}, facts {TARGET} "
                  f"{len(tp['facts_pre'])}, facts 8193 "
                  f"{len(p8193['facts_pre'])}.")

        # ---------- fact guards (both modes) ----------------------------
        edit = SPEC["fact_edits"][0]
        if f11986 is None or f11986["person_id"] != TARGET:
            fail(f"fact 11986 does not belong to person {TARGET}")
        if f11986["fact_type"] != edit["fact_type"]:
            fail(f"fact 11986 type {f11986['fact_type']!r} != "
                 f"{edit['fact_type']!r}")
        for field, allowed in edit["guard"].items():
            if f11986[field] not in allowed:
                fail(f"fact 11986 {field} {f11986[field]!r} is "
                     f"none of the allowed values; stop-on-surprise")
        for cs in edit["supersede_citations"]:
            c = row_dict(cur, "citations", "citation_id",
                         cs["citation_id"])
            if not c or c["fact_id"] != 11986:
                fail(f"citation {cs['citation_id']} does not "
                     f"belong to fact 11986")
        if fmove is None:
            fail(f"fact {move['fact_id']} missing")
        if fmove["fact_type"] != "Census":
            fail(f"fact {move['fact_id']} type "
                 f"{fmove['fact_type']!r} != 'Census'")
        if fmove["person_id"] not in (move["from_person_id"],
                                      move["to_person_id"]):
            fail(f"fact {move['fact_id']} is on person "
                 f"{fmove['person_id']}, neither the audited "
                 f"source nor the destination; stop-on-surprise")
        for cid in move["keep_citation_ids"] + [
                cs["citation_id"] for cs in
                move["supersede_citations"]]:
            c = row_dict(cur, "citations", "citation_id", cid)
            if not c or c["fact_id"] != move["fact_id"]:
                fail(f"citation {cid} does not belong to fact "
                     f"{move['fact_id']}")
        keep = row_dict(cur, "citations", "citation_id",
                        move["keep_citation_ids"][0])
        if SUPERSEDED_TAG in (keep["evidence_text"] or ""):
            fail(f"citation {move['keep_citation_ids'][0]} (the "
                 f"live 1930 citation) already carries a SUPERSEDED "
                 f"tag; stop-on-surprise")
        for d in SPEC["fact_detaches"]:
            f = row_dict(cur, "facts", "fact_id", d["fact_id"])
            if f is None:
                continue  # already detached (applied mode)
            if f["person_id"] != TARGET:
                fail(f"fact {d['fact_id']} does not belong to "
                     f"person {TARGET}")
            if f["fact_type"] != d["fact_type"]:
                fail(f"fact {d['fact_id']} type "
                     f"{f['fact_type']!r} != {d['fact_type']!r}")
            cids = sorted(r["citation_id"] for r in rows_where(
                cur, "citations", "fact_id", d["fact_id"]))
            if cids != sorted(d["citation_ids"]):
                fail(f"fact {d['fact_id']} citations {cids} != "
                     f"audited {sorted(d['citation_ids'])}")

        # ---------- register skeleton -----------------------------------
        register = {"package": SPEC["package"],
                    "run_date": SPEC["run_date"],
                    "detached_from_person": TARGET,
                    "detached_facts": [],
                    "detached_relationships": [],
                    "detached_photos": [],
                    "moved_facts": [],
                    "moved_relationships": []}
        deleted_rel_ids = []

        # ---------- relationship deletions -------------------------------
        for rem in SPEC["relationship_removals"]:
            disc = discoveries[rem["key"]]
            if not disc["deletable"]:
                continue
            entry_rows = disc["primaries"] + disc["reciprocals"]
            primary_row = disc["primaries"][0]
            entry = {k: primary_row[k] for k in
                     ("id", "person_a_id", "person_b_id",
                      "relationship_type", "evidence_text",
                      "certainty")}
            entry["disposition"] = "register"
            entry["reason"] = rem["reason"]
            extra = [r for r in entry_rows if r["id"] != primary_row["id"]]
            if extra:
                entry["reciprocal_row"] = {
                    k: extra[0][k] for k in
                    ("id", "person_a_id", "person_b_id",
                     "relationship_type", "evidence_text",
                     "certainty")}
            for r in disc["reciprocals"] + disc["primaries"]:
                cur.execute("DELETE FROM relationships "
                            "WHERE id = ?", (r["id"],))
                deleted_rel_ids.append(r["id"])
                print(f"Relationship row removed: {r['id']} "
                      f"({r['person_a_id']} -> {r['person_b_id']}, "
                      f"{r['relationship_type']}) [{rem['key']}]")
            register["detached_relationships"].append(entry)

        # ---------- fact move ---------------------------------------------
        if fmove["person_id"] == move["from_person_id"]:
            cur.execute(
                "UPDATE facts SET person_id = ? WHERE fact_id = ?",
                (move["to_person_id"], move["fact_id"]))
            entry = {"fact": fmove,
                     "from_person_id": move["from_person_id"],
                     "to_person_id": move["to_person_id"],
                     "superseded_citation_ids": [
                         cs["citation_id"] for cs in
                         move["supersede_citations"]],
                     "disposition": "moved",
                     "reason": move["reason"]}
            register["moved_facts"].append(entry)
            print(f"Fact {move['fact_id']} moved: "
                  f"{move['from_person_id']} -> "
                  f"{move['to_person_id']}")
        for cs in move["supersede_citations"]:
            c = row_dict(cur, "citations", "citation_id",
                         cs["citation_id"])
            if SUPERSEDED_TAG not in (c["evidence_text"] or ""):
                cur.execute(
                    "UPDATE citations SET evidence_text = ? "
                    "WHERE citation_id = ?",
                    ((c["evidence_text"] or "") + cs["marker"],
                     cs["citation_id"]))
                print(f"Citation {cs['citation_id']} marked "
                      f"SUPERSEDED.")

        # ---------- fact detaches -------------------------------------------
        for d in SPEC["fact_detaches"]:
            f = row_dict(cur, "facts", "fact_id", d["fact_id"])
            if f is None:
                continue
            cits = rows_where(cur, "citations", "fact_id",
                              d["fact_id"])
            for c in cits:
                cur.execute("DELETE FROM citations "
                            "WHERE citation_id = ?",
                            (c["citation_id"],))
            cur.execute("DELETE FROM facts WHERE fact_id = ?",
                        (d["fact_id"],))
            register["detached_facts"].append(
                {"fact": f, "citations": cits,
                 "disposition": "register", "reason": d["reason"]})
            print(f"Fact {d['fact_id']} detached to the register "
                  f"with {len(cits)} citation(s).")

        # ---------- fact edit 11986 ------------------------------------------
        f11986 = row_dict(cur, "facts", "fact_id", 11986)
        changes = {k: v for k, v in edit["set"].items()
                   if f11986[k] != v}
        if changes:
            assignments = ", ".join(f"{k} = ?" for k in changes)
            cur.execute(
                f"UPDATE facts SET {assignments} WHERE fact_id = ?",
                (*changes.values(), 11986))
            print(f"Fact 11986 edited: {sorted(changes)}")
        for cs in edit["supersede_citations"]:
            c = row_dict(cur, "citations", "citation_id",
                         cs["citation_id"])
            if SUPERSEDED_TAG not in (c["evidence_text"] or ""):
                cur.execute(
                    "UPDATE citations SET evidence_text = ? "
                    "WHERE citation_id = ?",
                    ((c["evidence_text"] or "") + cs["marker"],
                     cs["citation_id"]))
                print(f"Citation {cs['citation_id']} marked "
                      f"SUPERSEDED.")

        # ---------- person row 3591 --------------------------------------------
        prow = row_dict(cur, "persons", "person_id", TARGET)
        pchanges = {}
        for field in ("death_info", "source_page", "dataset_source",
                      "notes"):
            if prow[field] != tp["post"][field]:
                pchanges[field] = tp["post"][field]
        if pchanges:
            assignments = ", ".join(f"{k} = ?" for k in pchanges)
            cur.execute(
                f"UPDATE persons SET {assignments} "
                f"WHERE person_id = ?",
                (*pchanges.values(), TARGET))
            print(f"Person {TARGET} row corrected: "
                  f"{sorted(pchanges)}")

        # ---------- final gates --------------------------------------------------
        gate("persons total = 3807",
             cur.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
             == SPEC["expected_post_state"]["persons"])
        gate("sources total unchanged",
             cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
             == sources_pre)
        gate(f"facts on {TARGET} = 3 (2967, 11986 edited, 15454)",
             sorted(r["fact_id"] for r in rows_where(
                 cur, "facts", "person_id", TARGET))
             == sorted(tp["facts_post"]))
        gate("facts on 8193 = 10 (9 audited + moved 16058)",
             sorted(r["fact_id"] for r in rows_where(
                 cur, "facts", "person_id", 8193))
             == sorted(p8193["facts_pre"] + [move["fact_id"]]))
        gate("fact 11986 read-back: date '1834', corrected value",
             (lambda r: r and r["date_string"] == "1834"
              and r["value_string"] == edit["set"]["value_string"])(
                 row_dict(cur, "facts", "fact_id", 11986)))
        gate("fact 16058 read-back: on person 8193",
             (lambda r: r and r["person_id"]
              == move["to_person_id"])(
                 row_dict(cur, "facts", "fact_id", move["fact_id"])))
        for cs in move["supersede_citations"]:
            gate(f"citation {cs['citation_id']} marked SUPERSEDED",
                 citation_has_tag(cs["citation_id"]))
        for cs in edit["supersede_citations"]:
            gate(f"citation {cs['citation_id']} marked SUPERSEDED",
                 citation_has_tag(cs["citation_id"]))
        gate("citation 14868 stays live (no SUPERSEDED tag)",
             not citation_has_tag(move["keep_citation_ids"][0]))
        for d in SPEC["fact_detaches"]:
            gate(f"fact {d['fact_id']} detached (absent)",
                 row_dict(cur, "facts", "fact_id",
                          d["fact_id"]) is None)
            for cid in d["citation_ids"]:
                gate(f"citation {cid} detached (absent)",
                     row_dict(cur, "citations", "citation_id",
                              cid) is None)
        gate(f"person {TARGET} row in post-state",
             (lambda r: r["death_info"] == tp["post"]["death_info"]
              and r["source_page"] == tp["post"]["source_page"]
              and r["dataset_source"] == tp["post"]["dataset_source"]
              and r["notes"] == tp["post"]["notes"]
              and r["birth_info"] is None)(
                 row_dict(cur, "persons", "person_id", TARGET)))
        gate("no relationship rows between 8192 and 3591 (Ep8 "
             "dependency still satisfied)",
             cur.execute(
                 "SELECT COUNT(*) FROM relationships WHERE "
                 "(person_a_id = 8192 AND person_b_id = 3591) OR "
                 "(person_a_id = 3591 AND person_b_id = 8192)"
                 ).fetchone()[0] == 0)
        for pid in watched:
            gate(f"relationship id set on {pid} = pre-state minus "
                 f"deleted",
                 rel_ids(cur, pid)
                 == rel_pre[pid] - set(deleted_rel_ids))
        gate("PRAGMA integrity_check",
             cur.execute("PRAGMA integrity_check").fetchone()[0]
             == "ok")

        con.commit()
        print(f"Final gates passed ({len(gates)} checks).")
        print("COMMITTED.")

        if register["detached_relationships"] \
                or register["detached_facts"] \
                or register["moved_facts"]:
            REGISTER_PATH.write_text(
                json.dumps(register, indent=2, sort_keys=True),
                encoding="utf-8")
            print(f"Register written: {REGISTER_PATH} "
                  f"({len(register['detached_relationships'])} "
                  f"relationship pair(s), "
                  f"{len(register['detached_facts'])} fact(s), "
                  f"{len(register['moved_facts'])} moved fact(s))")
        else:
            print("No detachments or moves this run (already "
                  "applied); register file left as it stands.")
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - rollback on any surprise
        con.rollback()
        fail(f"unexpected error, rolled back: {exc!r}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
