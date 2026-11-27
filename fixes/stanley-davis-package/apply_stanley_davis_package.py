#!/usr/bin/env python3
"""Stanley Oliver Davis Sr correction package.

Corrects profile 8155: Birth fact to 5 Feb 1941 and Death fact to
22 Jun 2021 (both Millsboro, Delaware), resting on Jequan Davis's
2026-11-23 confirmation of his Ancestry tree profile (death and burial
citing the U.S. Find A Grave Index; birth and death also citing the
U.S. Public Records Index). The import citations that supported the old
values are marked SUPERSEDED in place, never silently overwritten.

The Burial fact is corrected to Millsboro with its Find a Grave
memorial 66421404 citation detached to the unassigned-evidence
register: that memorial is a different Stanley Davis (Alvinston
Cemetery, Ontario, Canada, per the import note on this profile). The
impossible 1920 Census fact (he was born in 1941) is detached whole to
the same register. The generic Marriage fact is flagged
generic_unverified and left in place. His kitchen portrait (supplied by
Jequan Davis 2026-11-23; byte-identical to the file carried on branch
fix/stanley-davis-photo) is registered as a new photo row and set
primary.

Safety: schema discovered at runtime; hard gates abort (rollback) on
any surprise; idempotent (a second run is a no-op); backup written
first; the register file is written only after a successful commit.

Usage: python3 apply_stanley_davis_package.py <path-to-genealogy_preservation.db>
"""
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "stanley_davis_package.json").read_text(encoding="utf-8"))
REGISTER_PATH = HERE / "unassigned_evidence_register.json"
SUPERSEDED_PREFIX = "SUPERSEDED (stanley-davis package, 2026-11-27): "


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
        fail("usage: apply_stanley_davis_package.py <db path>")
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

    def gate(name, ok):
        gates.append((name, bool(ok)))
        print(("PASS " if ok else "FAIL ") + name)
        if not ok:
            con.rollback()
            fail(f"gate failed: {name}")

    try:
        for table in ("persons", "sources", "facts", "citations",
                      "unified_photo_catalog", "photo_catalog",
                      "person_photos"):
            if not table_columns(cur, table):
                fail(f"table missing: {table}")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS fact_quality_flags ("
            "fact_id INTEGER PRIMARY KEY, flag TEXT, note TEXT, "
            "applied_at TEXT)")

        pre = SPEC["expected_pre_state"]
        pspec = SPEC["person"]
        pid = pspec["person_id"]

        # ---- pre-state verification -------------------------------------
        prow = row_dict(cur, "persons", "person_id", pid)
        if not prow or prow["name"] != pspec["name"]:
            fail(f"person {pid} is not {pspec['name']!r}")
        photo_spec = SPEC["photo"]
        existing_photo = cur.execute(
            "SELECT photo_id FROM unified_photo_catalog "
            "WHERE local_image_path = ?",
            (photo_spec["local_image_path"],),
        ).fetchone()
        fresh_photo = existing_photo is None
        persons_now = cur.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
        sources_now = cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        max_photo_now = cur.execute(
            "SELECT MAX(photo_id) FROM unified_photo_catalog").fetchone()[0]
        facts_now = cur.execute(
            "SELECT COUNT(*) FROM facts WHERE person_id = ?",
            (pid,)).fetchone()[0]
        if fresh_photo:
            if persons_now != pre["persons"]:
                fail(f"persons {persons_now} != expected {pre['persons']}")
            if sources_now != pre["sources"]:
                fail(f"sources {sources_now} != expected {pre['sources']}")
            if max_photo_now != pre["max_photo_id"]:
                fail(f"max photo_id {max_photo_now} != expected "
                     f"{pre['max_photo_id']}")
            if prow["birth_info"] != pspec["expected_birth_info"]:
                fail(f"birth_info {prow['birth_info']!r} != expected "
                     f"{pspec['expected_birth_info']!r}")
            if prow["death_info"] != pspec["expected_death_info"]:
                fail(f"death_info {prow['death_info']!r} != expected "
                     f"{pspec['expected_death_info']!r}")
            if facts_now != pre["facts_on_person"]:
                fail(f"facts on {pid} {facts_now} != expected "
                     f"{pre['facts_on_person']}")
            shapes = {
                7586: ("Birth", "unknown"),
                7587: ("Death", "1990"),
                24322: ("Burial", "1990"),
                24323: ("Census", "1920"),
                24324: ("Marriage", None),
            }
            for fid, (ftype, fdate) in shapes.items():
                frow = row_dict(cur, "facts", "fact_id", fid)
                if (not frow or frow["person_id"] != pid
                        or frow["fact_type"] != ftype
                        or frow["date_string"] != fdate):
                    fail(f"fact {fid} shape mismatch: {frow!r}")
            burial = row_dict(cur, "facts", "fact_id", 24322)
            if (burial["place_string"] != "Delmarva"
                    or "66421404" not in (burial["value_string"] or "")):
                fail(f"burial fact 24322 shape mismatch: {burial!r}")
            bcites = [r[0] for r in cur.execute(
                "SELECT citation_id FROM citations WHERE fact_id = 24322")]
            if bcites != [30117]:
                fail(f"burial citations {bcites} != [30117]")
            ccites = sorted(r[0] for r in cur.execute(
                "SELECT citation_id FROM citations WHERE fact_id = 24323"))
            if ccites != SPEC["census_detach"]["citation_ids"]:
                fail(f"census citations {ccites} != expected "
                     f"{SPEC['census_detach']['citation_ids']}")
        print(f"Person verified: {pid} {pspec['name']}")
        print(f"Pre-state: persons {persons_now}, sources {sources_now}, "
              f"facts on {pid} {facts_now}, max photo_id {max_photo_now}, "
              f"photo exists: {not fresh_photo}.")

        # ---- statement source -------------------------------------------
        sspec = SPEC["statement_source"]
        statement_id, s_created = find_or_create_source(
            cur, sspec["dataset"], sspec["title"], sspec.get("url", ""))
        print(f"Source {'created' if s_created else 'found'}: "
              f"{statement_id} - {sspec['title'][:60]}")

        # ---- Birth / Death corrections -----------------------------------
        for vspec in SPEC["vital_corrections"]:
            cur.execute(
                "UPDATE facts SET date_string = ?, place_string = ? "
                "WHERE fact_id = ?",
                (vspec["date_string"], vspec["place_string"],
                 vspec["fact_id"]),
            )
            _, c_created = ensure_citation(
                cur, vspec["fact_id"], statement_id,
                vspec["citation_evidence"])
            print(f"{vspec['fact_type']} fact corrected: "
                  f"{vspec['date_string']}, {vspec['place_string']}."
                  + (" Citation added from statement source."
                     if c_created else ""))
        cur.execute(
            "UPDATE persons SET birth_info = ?, death_info = ? "
            "WHERE person_id = ?",
            (pspec["birth_info"], pspec["death_info"], pid),
        )
        print(f"Person fields set: birth_info {pspec['birth_info']!r}, "
              f"death_info {pspec['death_info']!r}.")

        # ---- mark the old citations SUPERSEDED ----------------------------
        for sspec2 in SPEC["supersede_citations"]:
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
                print(f"Citation {sspec2['citation_id']} marked SUPERSEDED.")

        # ---- Burial correction + memorial citation detach -----------------
        bspec = SPEC["burial_correction"]
        crow = row_dict(cur, "citations", "citation_id", 30117)
        if crow is not None:
            register_additions.append({
                "kind": "citation",
                "person_id": pid,
                "detached_from_fact_id": bspec["fact_id"],
                "citation": crow,
                "reason": "Find a Grave memorial 66421404 is a different "
                          "Stanley Davis (Alvinston Cemetery, Ontario, "
                          "Canada); it is not Stanley Oliver Davis Sr of "
                          "Millsboro (1941-2021). Detached under the "
                          "prevention rule by the stanley-davis package, "
                          "2026-11-27.",
            })
            cur.execute("DELETE FROM citations WHERE citation_id = 30117")
            print("Citation 30117 detached to the register.")
        cur.execute(
            "UPDATE facts SET date_string = ?, place_string = ?, "
            "value_string = ? WHERE fact_id = ?",
            (bspec["date_string"], bspec["place_string"],
             bspec["value_string"], bspec["fact_id"]),
        )
        _, bc_created = ensure_citation(
            cur, bspec["fact_id"], statement_id, bspec["citation_evidence"])
        print(f"Burial fact corrected: {bspec['place_string']}."
              + (" Citation added from statement source." if bc_created
                 else ""))

        # ---- Census fact detach -------------------------------------------
        cspec = SPEC["census_detach"]
        frow = row_dict(cur, "facts", "fact_id", cspec["fact_id"])
        if frow is not None:
            cites = [row_dict(cur, "citations", "citation_id", cid)
                     for cid in cspec["citation_ids"]]
            register_additions.append({
                "kind": "fact",
                "person_id": pid,
                "fact": frow,
                "citations": cites,
                "reason": "A man born 5 Feb 1941 cannot appear in the 1920 "
                          "census; the fact's generic import citations quote "
                          "no household matching his life. Detached whole "
                          "under the prevention rule by the stanley-davis "
                          "package, 2026-11-27.",
            })
            cur.execute(
                "DELETE FROM citations WHERE fact_id = ?",
                (cspec["fact_id"],))
            cur.execute(
                "DELETE FROM facts WHERE fact_id = ?",
                (cspec["fact_id"],))
            print(f"Census fact {cspec['fact_id']} detached to the register "
                  f"with its {len(cites)} citations.")

        # ---- Marriage flag ---------------------------------------------------
        mspec = SPEC["marriage_flag"]
        cur.execute(
            "INSERT OR IGNORE INTO fact_quality_flags "
            "(fact_id, flag, note, applied_at) VALUES (?, ?, ?, ?)",
            (mspec["fact_id"], mspec["flag"], mspec["note"],
             mspec["applied_at"]),
        )
        print("Marriage fact flagged generic_unverified.")

        # ---- notes append -----------------------------------------------------
        prow = row_dict(cur, "persons", "person_id", pid)
        notes = prow["notes"] or ""
        if SPEC["notes_marker"] not in notes:
            new_notes = (notes.rstrip() + "\n" + SPEC["notes_append"]
                         if notes.strip() else SPEC["notes_append"])
            cur.execute(
                "UPDATE persons SET notes = ? WHERE person_id = ?",
                (new_notes, pid),
            )
            print(f"Correction notes appended to {pid}.")

        # ---- photo row ---------------------------------------------------------
        if fresh_photo:
            cols = table_columns(cur, "unified_photo_catalog")
            values = {
                "normalized_filename": photo_spec["normalized_filename"],
                "original_filename": photo_spec["original_filename"],
                "local_image_path": photo_spec["local_image_path"],
                "sha256_hash": photo_spec["sha256_hash"],
                "title": photo_spec["title"],
                "category": photo_spec["category"],
                "document_type": photo_spec["document_type"],
                "asset_type": photo_spec["asset_type"],
                "subtype": photo_spec["subtype"],
                "subject_names": photo_spec["subject_names"],
                "married_surname": photo_spec["married_surname"],
                "dataset_source": photo_spec["dataset_source"],
                "contains_face": photo_spec["contains_face"],
                "face_context": photo_spec["face_context"],
                "routing_target": photo_spec["routing_target"],
                "primary_person_id": pid,
            }
            use = {k: v for k, v in values.items() if k in cols}
            col_sql = ", ".join(use.keys())
            ph = ", ".join("?" for _ in use)
            cur.execute(
                f"INSERT INTO unified_photo_catalog ({col_sql}) "
                f"VALUES ({ph})",
                tuple(use.values()),
            )
            photo_id = cur.lastrowid
            print(f"Photo row created: {photo_id}")
        else:
            photo_id = existing_photo[0]
            print(f"Photo row found: {photo_id}")
        trow = cur.execute(
            "SELECT photo_id FROM photo_catalog WHERE photo_id = ?",
            (photo_id,),
        ).fetchone()
        if not trow:
            tcols = table_columns(cur, "photo_catalog")
            tvals = {"photo_id": photo_id,
                     "title_or_caption": photo_spec["title"]}
            tuse = {k: v for k, v in tvals.items() if k in tcols}
            cur.execute(
                f"INSERT INTO photo_catalog ({', '.join(tuse.keys())}) "
                f"VALUES ({', '.join('?' for _ in tuse)})",
                tuple(tuse.values()),
            )
            print(f"Photo title row created in photo_catalog: {photo_id}")
        lrow = cur.execute(
            "SELECT id FROM person_photos WHERE person_id = ? "
            "AND photo_id = ?",
            (pid, photo_id),
        ).fetchone()
        if not lrow:
            cur.execute(
                "INSERT INTO person_photos (person_id, photo_id, "
                "confidence_score, is_primary) VALUES (?, ?, ?, ?)",
                (pid, photo_id, photo_spec["confidence_score"],
                 photo_spec["is_primary"]),
            )
            print(f"Photo {photo_id} linked to person {pid} "
                  f"(primary={photo_spec['is_primary']}).")

        # ---- final gates ---------------------------------------------------
        gate("persons total unchanged",
             cur.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
             == pre["persons"])
        gate("sources delta equals sources created this run",
             cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
             - sources_now == (1 if s_created else 0))
        prow = row_dict(cur, "persons", "person_id", pid)
        gate("person birth_info and death_info carry the corrected values",
             prow["birth_info"] == pspec["birth_info"]
             and prow["death_info"] == pspec["death_info"])
        gate("facts on 8155 = 5",
             cur.execute(
                 "SELECT COUNT(*) FROM facts WHERE person_id = ?",
                 (pid,)).fetchone()[0] == 5)
        for vspec in SPEC["vital_corrections"]:
            frow = row_dict(cur, "facts", "fact_id", vspec["fact_id"])
            gate(f"{vspec['fact_type']} fact carries the corrected values",
                 frow["date_string"] == vspec["date_string"]
                 and frow["place_string"] == vspec["place_string"])
            gate(f"{vspec['fact_type']} fact cited to the statement source",
                 cur.execute(
                     "SELECT COUNT(*) FROM citations WHERE fact_id = ? "
                     "AND source_id = ?",
                     (vspec["fact_id"], statement_id),
                 ).fetchone()[0] == 1)
        brow = row_dict(cur, "facts", "fact_id", bspec["fact_id"])
        gate("burial fact carries the corrected values",
             brow["date_string"] == bspec["date_string"]
             and brow["place_string"] == bspec["place_string"]
             and brow["value_string"] == bspec["value_string"])
        gate("memorial citation detached from burial fact",
             cur.execute(
                 "SELECT COUNT(*) FROM citations WHERE citation_id = 30117"
             ).fetchone()[0] == 0)
        gate("burial fact cited to the statement source",
             cur.execute(
                 "SELECT COUNT(*) FROM citations WHERE fact_id = ? "
                 "AND source_id = ?",
                 (bspec["fact_id"], statement_id),
             ).fetchone()[0] == 1)
        gate("census fact gone from the profile",
             cur.execute(
                 "SELECT COUNT(*) FROM facts WHERE fact_id = ?",
                 (cspec["fact_id"],)).fetchone()[0] == 0)
        for sspec2 in SPEC["supersede_citations"]:
            crow = row_dict(cur, "citations", "citation_id",
                            sspec2["citation_id"])
            gate(f"citation {sspec2['citation_id']} marked SUPERSEDED",
                 crow is not None
                 and (crow["evidence_text"] or "").startswith(
                     SUPERSEDED_PREFIX))
        gate("marriage fact carries a quality flag",
             cur.execute(
                 "SELECT COUNT(*) FROM fact_quality_flags "
                 "WHERE fact_id = ? AND flag = ?",
                 (mspec["fact_id"], mspec["flag"]),
             ).fetchone()[0] == 1)
        gate("correction notes append present",
             SPEC["notes_marker"] in (prow["notes"] or ""))
        gate("photo row + title + primary link present",
             cur.execute(
                 "SELECT COUNT(*) FROM unified_photo_catalog "
                 "WHERE photo_id = ?", (photo_id,)).fetchone()[0] == 1
             and cur.execute(
                 "SELECT COUNT(*) FROM photo_catalog WHERE photo_id = ?",
                 (photo_id,)).fetchone()[0] == 1
             and cur.execute(
                 "SELECT COUNT(*) FROM person_photos WHERE person_id = ? "
                 "AND photo_id = ? AND is_primary = 1",
                 (pid, photo_id)).fetchone()[0] == 1)
        gate("register entries this run are the full set or zero",
             len(register_additions) in (0, 2))
        gate("PRAGMA integrity_check",
             cur.execute("PRAGMA integrity_check").fetchone()[0] == "ok")

        con.commit()
        print(f"Final gates passed ({len(gates)} checks).")
        print(f"Field changes this run: sources created "
              f"{1 if s_created else 0}, photo rows created "
              f"{1 if fresh_photo else 0}, register entries "
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
