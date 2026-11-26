#!/usr/bin/env python3
"""
Split profile 2412 (Whittington Clark) per Jequan's approval 2026-11-17 of
SPLIT_PLAN_2412_whittington_clark.md, on the evidence of the Sussex County
probate file (Delaware Public Archives 4545-000-009).

Data: split_2412.json beside this script. Operations:
1. Create (or reuse) a source row for the probate file.
2. Create the younger Whittington Clark profile; move his three facts
   (11924, 1958, 18452) and the two GEDCOM parent links to it; clean the
   narrative out of his birth fact into his notes.
3. Correct the elder's person fields (death before 12 Jul 1836, birth
   unknown), append the split note, and add four probate-cited facts.
4. Create nine profiles (widow Lydia, heirs Nathaniel and Latin, three
   unnamed daughters, Eli Mosley, James Palmer, elder Bowen Harman) and the
   nine relationships the distribution account proves, reciprocally.
5. Append disambiguation notes to profiles 7577, 1022, 2492 (no other
   change to them).

The schema is discovered from the database, never assumed. Safety:
timestamped backup first; ONE transaction; idempotent (rerunning changes
nothing twice); every assert failure rolls back and prints what was found.

Usage: python3 apply_split_2412.py [path-to-genealogy_preservation.db]

Correction 2026-11-25 (Orbit), after the first run stopped on schema
discovery and rolled back clean: (1) the relationships columns are
person_a_id / person_b_id and are now the first candidates; (2) the
citation model is detected from the table's columns, not its name
(this database's citations table is a direct fact/source/evidence
table), and new citations carry the fact's value as evidence_text;
(3) table lookup prefers exact names (persons over person_photos);
(4) the created-person lookup for the nine new profiles matches
their full notes exactly, because the sibling profiles share a
60-character notes prefix and a prefix search conflates them;
(5) parent-link moves print their rowcounts. No data or plan changes.
Second correction the same day, after re-run 2 committed with a
silent conflation (caught by the runner, who restored the database
from the pre-script backup): the eli_mosley and james_palmer notes
in the plan were identical strings, so even exact notes matching
resolved James Palmer to Eli Mosley's profile. The plan now gives
each man a notes string naming himself; the created-person lookup
below matches on name AND notes; and a hard gate after creation
fails the run if any two new profiles resolve to the same id or
the created count differs from the plan count.
"""
import json, os, shutil, sqlite3, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "split_2412.json")))
ELDER = D["elder_person_id"]
MARK = "[Created by split package 2026-11-17"

def tables(cur):
    return [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

def cols(cur, t):
    return [r[1] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()]

def pick(cs, *subs, required=True):
    low = [c.lower() for c in cs]
    for s in subs:
        for c, l in zip(cs, low):
            if s in l:
                return c
    if required:
        raise RuntimeError(f"no column matching {subs} in {cs}")
    return None

def find_table(cur, *name_subs):
    ts = tables(cur)
    for s in name_subs:
        for t in ts:
            if t.lower() == s or t.lower() == s + "s":
                return t
    for t in ts:
        if any(s in t.lower() for s in name_subs):
            return t
    return None

def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
        "~/Desktop/Antigravity Projects/lynncjackson-genealogy-scraper/"
        "preservation_output/genealogy_preservation.db")
    if not os.path.exists(db_path):
        sys.exit(f"DB not found: {db_path}")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{db_path}.backup-{stamp}"
    shutil.copy2(db_path, backup)
    print(f"Backup: {backup}")

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    try:
        pt = find_table(cur, "person")           # persons
        ft = find_table(cur, "fact")             # facts
        rt = find_table(cur, "relation")         # relationships
        st = find_table(cur, "source")           # sources
        ct = find_table(cur, "citation")         # citations or link table
        if not all([pt, ft, rt, st]):
            raise RuntimeError(f"tables found: persons={pt} facts={ft} rel={rt} sources={st}")
        pc, fc, rc, sc = cols(cur, pt), cols(cur, ft), cols(cur, rt), cols(cur, st)
        p_id = pc[0]
        p_name = pick(pc, "name")
        p_notes = pick(pc, "notes", "note", required=False)
        f_id, f_person = fc[0], pick(fc, "person")
        f_type = pick(fc, "type")
        f_date = pick(fc, "date", required=False)
        f_val = pick(fc, "value", required=False)
        f_place = pick(fc, "place", required=False)
        r_person = pick(rc, "person_a", "person")
        r_related = pick(rc, "person_b", "related", "other", "target")
        r_type = pick(rc, "type", "relation")
        r_ev = pick(rc, "evidence", "note", required=False)
        s_id = sc[0]
        s_title = pick(sc, "title", "name")
        s_ds = pick(sc, "dataset", required=False)
        s_url = pick(sc, "url", required=False)

        def person_exists(pid):
            return cur.execute(f"SELECT 1 FROM {pt} WHERE {p_id}=?", (pid,)).fetchone()

        if not person_exists(ELDER):
            raise RuntimeError(f"elder profile {ELDER} not found")

        cur.execute("BEGIN")

        # 1. Source row for the probate file
        row = cur.execute(f"SELECT {s_id} FROM {st} WHERE {s_title}=?",
                          (D["source"]["title"],)).fetchone()
        if row:
            source_id = row[0]
        else:
            ins, vals = [s_title], [D["source"]["title"]]
            if s_ds: ins.append(s_ds); vals.append(D["source"]["dataset"])
            if s_url: ins.append(s_url); vals.append(D["source"]["url"])
            cur.execute(f"INSERT INTO {st} ({', '.join(ins)}) VALUES ({', '.join('?'*len(ins))})", vals)
            source_id = cur.lastrowid
        print(f"Source id: {source_id}")

        # Citation writer for new facts (model detected from the
        # citations table's columns: a direct table carries fact and
        # source columns; a link table carries fact and citation
        # columns and no source column)
        cc = cols(cur, ct) if ct else []
        has_fact = any("fact" in c.lower() for c in cc)
        has_source = any("source" in c.lower() for c in cc)
        has_citation = any("citation" in c.lower() for c in cc)
        link_table = ct if (ct and has_fact and has_citation and not has_source) else None
        def cite(fact_id, evidence=None):
            if ct and has_fact and has_source:
                cfc = pick(cc, "fact"); csc = pick(cc, "source")
                ins, vals = [cfc, csc], [fact_id, source_id]
                cev = pick(cc, "evidence", required=False)
                if cev and evidence:
                    ins.append(cev); vals.append(evidence)
                cur.execute(f"INSERT INTO {ct} ({', '.join(ins)}) VALUES ({', '.join('?'*len(ins))})", vals)
            elif link_table:
                lc = cols(cur, link_table)
                lfc = pick(lc, "fact"); lcc = pick(lc, "citation")
                cit_t = find_table(cur, "citation")
                citc = cols(cur, cit_t)
                cid_c = citc[0]; src_c = pick(citc, "source")
                cur.execute(f"INSERT INTO {cit_t} ({src_c}) VALUES (?)", (source_id,))
                new_cid = cur.lastrowid
                cur.execute(f"INSERT INTO {link_table} ({lfc}, {lcc}) VALUES (?, ?)", (fact_id, new_cid))
            else:
                raise RuntimeError("no recognizable citation model for new facts")

        def insert_person(spec, extra=None):
            ins, vals = [p_name], [spec["name"]]
            for cand, key in (("first_name", "first_name"), ("married", "married_last_name")):
                c = pick(pc, cand, required=False)
                if c and key in spec:
                    ins.append(c); vals.append(spec[key])
            if p_notes and spec.get("notes"):
                ins.append(p_notes); vals.append(spec["notes"])
            if extra:
                for colname, val in extra:
                    c = pick(pc, colname, required=False)
                    if c: ins.append(c); vals.append(val)
            cur.execute(f"INSERT INTO {pt} ({', '.join(ins)}) VALUES ({', '.join('?'*len(ins))})", vals)
            return cur.lastrowid

        def find_created(marker_text, exact=False):
            if not p_notes: return None
            if exact:
                r = cur.execute(f"SELECT {p_id} FROM {pt} WHERE {p_notes}=?",
                                (marker_text,)).fetchone()
            else:
                r = cur.execute(f"SELECT {p_id} FROM {pt} WHERE {p_notes} LIKE ?",
                                (f"%{marker_text}%",)).fetchone()
            return r[0] if r else None

        def find_created_person(spec):
            # A created profile is identified by its name AND its full
            # notes together; either alone can collide (names repeat
            # across the archive's history, and two plan entries once
            # shipped with identical notes).
            if not p_notes: return None
            r = cur.execute(f"SELECT {p_id} FROM {pt} WHERE {p_name}=? AND {p_notes}=?",
                            (spec["name"], spec["notes"])).fetchone()
            return r[0] if r else None

        # 2. Younger profile
        younger_id = find_created("Created by split package 2026-11-17 from profile 2412")
        if younger_id is None:
            y = D["younger"]
            younger_id = insert_person(y, extra=[
                ("birth_date", y["birth_date"]), ("birth_info", y["birth_info"]),
                ("death_date", y["death_date"]), ("death_info", y["death_info"])])
        print(f"Younger profile id: {younger_id}")

        # Move his facts
        moved = 0
        for fid in D["facts_to_move_to_younger"]:
            cur.execute(f"UPDATE {ft} SET {f_person}=? WHERE {f_id}=? AND {f_person}=?",
                        (younger_id, fid, ELDER))
            moved += cur.rowcount
        print(f"Facts moved to younger: {moved} of {len(D['facts_to_move_to_younger'])}")

        # Clean his birth fact text
        bc = D["younger"]["birth_fact_cleanup"]
        sets, vals = [], []
        if f_date: sets.append(f"{f_date}=?"); vals.append(bc["new_date_string"])
        if f_val: sets.append(f"{f_val}=?"); vals.append(bc["new_value_string"])
        if sets:
            cur.execute(f"UPDATE {ft} SET {', '.join(sets)} WHERE {f_id}=?", vals + [bc["fact_id"]])

        # Move the GEDCOM parent links (resolve parents by exact name)
        for pname in D["parent_links_to_move"]:
            prow = cur.execute(f"SELECT {p_id} FROM {pt} WHERE {p_name}=?", (pname,)).fetchall()
            if len(prow) != 1:
                raise RuntimeError(f"parent {pname}: {len(prow)} name matches, need exactly 1")
            pid = prow[0][0]
            cur.execute(f"UPDATE {rt} SET {r_person}=? WHERE {r_person}=? AND {r_related}=? "
                        f"AND {r_type} LIKE 'child%'", (younger_id, ELDER, pid))
            n1 = cur.rowcount
            cur.execute(f"UPDATE {rt} SET {r_related}=? WHERE {r_person}=? AND {r_related}=? "
                        f"AND {r_type} LIKE 'parent%'", (younger_id, pid, ELDER))
            n2 = cur.rowcount
            print(f"Parent link {pname} (id {pid}): child-side rows {n1}, parent-side rows {n2}")
        print("Parent links moved.")

        # 3. Elder person fields and notes
        eu = D["elder_person_update"]
        sets, vals = [], []
        for colname in ("birth_date", "birth_info", "death_date", "death_info"):
            c = pick(pc, colname, required=False)
            if c: sets.append(f"{c}=?"); vals.append(eu[colname])
        if sets:
            cur.execute(f"UPDATE {pt} SET {', '.join(sets)} WHERE {p_id}=?", vals + [ELDER])
        if p_notes:
            cur_notes = cur.execute(f"SELECT {p_notes} FROM {pt} WHERE {p_id}=?",
                                    (ELDER,)).fetchone()[0] or ""
            # drop the stale Find A Grave verification claim, keep the rest
            kept = " ".join(seg for seg in cur_notes.split(" | ")
                            if "FindAGrave" not in seg and "Find A Grave" not in seg)
            if "Split 2026-11-17" not in kept:
                new_notes = (kept.rstrip() + " " + eu["notes_append"]).strip()
                cur.execute(f"UPDATE {pt} SET {p_notes}=? WHERE {p_id}=?", (new_notes, ELDER))
        print("Elder profile corrected.")

        # Elder's new probate facts, each cited to the probate source
        for nf in D["elder_new_facts"]:
            dup = cur.execute(
                f"SELECT 1 FROM {ft} WHERE {f_person}=? AND {f_type}=? "
                + (f"AND {f_date}=?" if f_date else ""),
                (ELDER, nf["fact_type"], nf["date_string"]) if f_date else (ELDER, nf["fact_type"])).fetchone()
            if dup: continue
            ins, vals = [f_person, f_type], [ELDER, nf["fact_type"]]
            if f_date: ins.append(f_date); vals.append(nf["date_string"])
            if f_val: ins.append(f_val); vals.append(nf["value_string"])
            if f_place: ins.append(f_place); vals.append(nf["place_string"])
            cur.execute(f"INSERT INTO {ft} ({', '.join(ins)}) VALUES ({', '.join('?'*len(ins))})", vals)
            cite(cur.lastrowid, nf.get("value_string"))
        print("Elder probate facts added and cited.")

        # 4. New persons
        ids = {"ELDER": ELDER, "YOUNGER": younger_id}
        for spec in D["new_persons"]:
            existing = find_created_person(spec) if p_notes else None
            ids[spec["key"]] = existing if existing else insert_person(spec)
        resolved = [ids[s["key"]] for s in D["new_persons"]]
        if len(resolved) != len(D["new_persons"]) or len(set(resolved)) != len(resolved) \
           or younger_id in resolved:
            raise RuntimeError(f"new_persons resolution failed, ids not distinct: {ids}")
        print("New person ids:", {k: v for k, v in ids.items() if k not in ("ELDER", "YOUNGER")})

        # 5. Relationships, reciprocal, skip if present
        def rel_exists(a, b, t):
            return cur.execute(f"SELECT 1 FROM {rt} WHERE {r_person}=? AND {r_related}=? AND {r_type}=?",
                               (a, b, t)).fetchone()
        def add_rel(a, b, t, ev):
            if rel_exists(a, b, t): return
            ins, vals = [r_person, r_related, r_type], [a, b, t]
            if r_ev: ins.append(r_ev); vals.append(ev)
            cur.execute(f"INSERT INTO {rt} ({', '.join(ins)}) VALUES ({', '.join('?'*len(ins))})", vals)
        for rel in D["relationships"]:
            a, b = ids[rel["a"]], ids[rel["b"]]
            if rel["type"] == "spouse":
                add_rel(a, b, "spouse_of", rel["evidence"]); add_rel(b, a, "spouse_of", rel["evidence"])
            else:
                add_rel(a, b, "parent_of", rel["evidence"]); add_rel(b, a, "child_of", rel["evidence"])
        print("Relationships created.")

        # 6. Disambiguation notes
        if p_notes:
            for dn in D["disambiguation_notes"]:
                if not person_exists(dn["person_id"]):
                    raise RuntimeError(f"disambiguation target {dn['person_id']} missing")
                cur_notes = cur.execute(f"SELECT {p_notes} FROM {pt} WHERE {p_id}=?",
                                        (dn["person_id"],)).fetchone()[0] or ""
                if "Note 2026-11-17" not in cur_notes:
                    cur.execute(f"UPDATE {pt} SET {p_notes}=? WHERE {p_id}=?",
                                ((cur_notes.rstrip() + " " + dn["append"]).strip(), dn["person_id"]))
        print("Disambiguation notes appended.")

        con.commit()
        print("COMMITTED. Re-export and push on this branch for verification.")
    except Exception as e:
        con.rollback()
        print("ROLLED BACK, nothing changed:", e)
        for t in tables(cur):
            if any(s in t.lower() for s in ("person", "fact", "relation", "source", "citation")):
                print(t, cols(cur, t))
        con.close()
        sys.exit(1)
    con.close()

if __name__ == "__main__":
    main()
