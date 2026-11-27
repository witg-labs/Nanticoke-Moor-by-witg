# Build report: Samuel Thompson Jr correction package

Built 2026-11-27. Status: **simulation-proven, ready to push to a
branch. NOT run against the real database** (the DB is not on this
machine). Nothing was pushed.

## Files

- `apply_samuel_thompson_jr_correction.py` — schema-discovering,
  backup-first, single-transaction, idempotent apply script in
  the Mosley-Davis pattern (exact-name candidate lists, PRAGMA
  table_info read with NOT NULL flags, stop-on-surprise exit 3,
  rollback restores both the DB transaction and the register
  file).
- `samuel_thompson_jr_correction.json` — the plan: every target
  value, evidence text, detachment note, and the expected-count
  table the gates assert.
- `unassigned_evidence_register.json` — created by the script at
  run time in the same folder (see resolution 3 below); it does
  not exist yet because the package has not run.

## Scope folded in

Spec sections 1-9 as written; Addendum 2 (section 12) in full
(David 8351 is David Lee Thompson; Tinnie/Biggie renamed in
parenthesis form, dates removed, marked living); Jequan's
2026-11-27 ruling that Shirley Thompson (8265) is alive (her
death_info cleared and her Death fact carrying 30 May 1992
detached to the register as contradicted). Addendum 1 items 1-3
(new profiles for William Harvey "Jelly", Bradley, and the Deroy
restoration) are NOT in this package: no profiles are created,
persons total is gated unchanged at 3,799. Addendum 1 items 4-5
(Wydell 8352's "1902" death, Ruth Ann 8268's date reset) are
also NOT applied — see resolution 9. Ruth Ann's parent link
stands, per Addendum 1 item 5's premise, and the simulation
verifies it survives the run.

## Simulation

Mock: SQLite DB built with the live schema shape and the live
NOT NULL constraints in place (persons.name TEXT NOT NULL
UNIQUE, facts.fact_type TEXT NOT NULL), seeded with the
preflight-verified live values for every touched profile, fact,
citation, and relationship (PREFLIGHT_2026-11-27.md plus the
person JSONs on origin/main @ c498b28f), plus filler rows
bringing totals to the live 3,799 persons and 2,674 sources so
the absolute count gates run for real. Harness and mock builder
were kept in /tmp/samuel_sim/ (build_mock.py, simulate.py);
results below are from the final harness run: **53/53 checks
passed.**

### Run 1 (fresh mock): COMMITTED, all 30 in-script gates PASS

Gate by gate: persons total unchanged; name set on 8169, 8264,
8351, 10097, 10098; 8169 birth_info corrected; 8351 birth_info
corrected; 8351 death_info corrected; 10097, 10098, 8265
death_info cleared (living); 10097 birth_info cleared (living);
facts on 8169 = 6 (SS-5 out, Nickname in); citations on 8169's
facts = 8; relationships touching 8169 = 12; wrong link gone
8169<->8147 (spouse); wrong link gone 8169<->8168 (parent);
wrong link gone 8169<->11253 (parent); citation 30159 retained,
marked superseded; citations 30160, 30161, 30163 detached; SS-5
fact 24344 detached; exactly one source each for samuel_program,
david_program, jequan_statement; sources delta equals sources
created this run; field changes are the full expected set;
PRAGMA integrity_check ok.

Run-1 tallies the runner will see on a pristine DB: field
changes names 5, birth_info 3, death_info 4; sources created 3;
register entries 13 (3 relationships, 3 citations, 5 facts —
24344, 9483, 9484, 9487, 7758 — and 2 superseded-in-place
captures for David's Birth/Death facts). Post-run read-backs
verified by full key: the three Nickname facts by
(person_id, fact_type, value_string), all three sources by exact
title, profile rows by person_id for every changed field, and
the detached rows' full contents inside the register file.

### Run 2 (same DB again): idempotent no-op

Exit 0, COMMITTED, field changes 0 across the board, sources
created 0, register entries 0; the full DB dump after run 2 is
identical to the dump after run 1, and the register file is
byte-identical. One bug was found and fixed during simulation:
the first build's pre-state check demanded SS-5 fact 24344
exist, which is false after a completed run (the package itself
detaches it); the check now accepts present-and-correct or
absent, and surprises on anything else.

### Run 3 (deliberately wrong current state): abort + rollback

Mock copy with 8169's birth_info tampered to "1 Jan 1900
Elsewhere": the script exits 3 with "SCHEMA SURPRISE: person
8169 birth_info is neither the expected old nor the new value",
prints "ROLLED BACK, nothing changed", the post-abort DB dump
is identical to the pre-run tampered dump, and no register file
is written. A timestamped backup is written before the
transaction in every run, including aborted ones.

## Final expected-count table (what the runner should see)

| Measure | Before | After |
|---|---|---|
| Persons total | 3,799 | 3,799 (no creates, no deletes) |
| persons.name changed | — | 5 (8169, 8264, 8351, 10097, 10098) |
| persons.birth_info changed | — | 3 (8169 set, 8351 set, 10097 cleared) |
| persons.death_info changed | — | 4 (8351 set, 10097 / 10098 / 8265 cleared) |
| Facts on 8169 | 6 | 6 (SS-5 24344 detached, Nickname added) |
| Citations on 8169's facts | 9 | 8 (see resolution 1) |
| Relationships touching 8169 | 15 | 12 |
| Facts on 8351 | 7 | 7 (Birth/Death updated in place) |
| Facts on 10097 | 7 | 6 (2 detached, Nickname added) |
| Facts on 10098 | 6 | 6 (1 detached, Nickname added) |
| Facts on 8265 | 6 | 5 (Death fact detached) |
| Sources | 2,674 | 2,677 expected (+3 created; fewer if a title already exists — the gate asserts delta = created count, and exactly one row per title) |
| Register entries added | — | 13 on a pristine run |

Global relationship count falls by exactly the rows deleted
(3 in the mock's single-row storage). If the Maryland Davis
package has already removed the 8169<->11253 reciprocal from
her side, the delete here is a no-op for that pair and the run
report must reconcile the difference explicitly instead of
forcing the count, per spec section 9.

## Discrepancies and ambiguities resolved (read before running)

1. **Spec section 9's "citations on 8169's facts: 9 before; 9
   after" does not survive its own component list.** Detaching
   citations 30160, 30161, 30163 (-3) and adding three citations
   (+3) nets zero only if citation 30162 stays — but 30162 rides
   SS-5 fact 24344, which section 6d detaches whole, so 30162
   leaves 8169's fact set with it. The true figure is **9 -> 8**,
   and the plan gates on 8. The tasking's expected counts did
   not include this measure; flagged here rather than silently
   adjusted.
2. **Sources: +3 expected on the live DB, not +1/+2.** Spec
   sections 3c and 7b require the three Nickname facts to be
   cited to Jequan Davis's statement of 2026-11-27, and section
   3c expressly forbids citing the Bull nickname to the funeral
   program. No statement source exists in the live DB (verified
   against all 2,674 titles in sources.json: the only
   Jequan-titled sources are the two GEDCOM compilations, 622
   and 625, and citing a 2026-11-27 oral statement to the GEDCOM
   would misattribute it). Resolution: a third find-or-create
   source, "Statement of Jequan Davis, 2026-11-27 (family
   knowledge; Samuel Thompson Jr. correction audit)". The
   tasking's "+1 or +2" covered the two program sources only;
   with the statement source the pristine-run delta is +3. The
   gate asserts delta = number created this run and exactly one
   row per title, so a pre-existing title reduces the delta
   without failing the run.
3. **The unassigned-evidence register has no DB
   representation in any prior package** (the Mosley-Davis
   pattern detaches nothing; no register table exists in the
   schema). Resolution: the register is a JSON file,
   `unassigned_evidence_register.json`, in the package folder,
   following the project's register-as-file convention. Every
   detached row (relationship, citation, or fact with all its
   citations) and every superseded-in-place capture is written
   there in full, all columns verbatim, with its detachment
   note, before commit; on rollback the file is restored to its
   pre-run contents, and on an idempotent re-run it is not
   touched. The runner should commit this file with the export,
   as with prior packages' artifacts.
4. **Cleared date fields are set to the string "unknown"**, the
   archive's existing no-value representation (10098's
   birth_info and 8265's birth_info already carry it), not NULL
   or empty. This is also why 10098's birth_info is not counted
   as a change: it already reads "unknown".
5. **Rename collisions abort the whole run, not just the one
   rename.** Spec section 9 says a collision "aborts the
   affected rename only", but the same section's hard count
   gates cannot pass with a partial rename set, so the script
   checks all five target names up front and aborts before any
   change if one is taken by another profile. Preflight verified
   all five target names free, so this should never fire.
6. **Section 3e's family counts** ("25 grandchildren, 27
   great-grandchildren", "cited to the program source") are
   appended to persons.notes, which cannot carry a citation;
   the program source is cited on 8169's Death and Marriage
   facts in the same run, which is where the counts come from.
7. **Name facts are not rewritten.** The renames change
   persons.name only (all the spec orders); the existing Name
   fact value_strings on 8169 ("Samuel Thompson"), 8264, and
   8351 keep their old values in the fact list. On 10097/10098
   the Name facts do get the section 7b program citations.
   Flagged in case a follow-on tidy wants the Name facts synced.
8. **Wrong-life facts left untouched, by spec discipline.**
   Addendum 2 and the Shirley ruling name only the Birth/Death
   facts (and, for Shirley, the Death fact). The following stay
   on the corrected profiles carrying wrong-life values and need
   a ruling before anyone detaches them: on 8351, Burial fact
   24520 (FindAGrave #138577443, dated 9 Nov 2014), Census fact
   24521 (a 1950 census entry, impossible for a man born in
   1955), SS-5 fact 24522 (dated 1946), Marriage fact 24523; on
   8265, Burial fact 24465 (FindAGrave #103371235, dated 30 May
   1992 — the same contradicted date as the detached Death
   fact); on 10097, Burial 25822, Census 25823, SS-5 25824,
   Marriage 25825; on 10098, Burial 25826, Census 25827 (1800 /
   1860 censuses), Marriage 25828. The simulation verifies each
   of these survives the run byte-identical.
9. **Wydell 8352 and Ruth Ann 8268 corrections are excluded.**
   Addendum 1 items 4-5 assign them to "this package's follow-on
   set (or this package, at run time, if scope is extended on
   his word)", and the tasking's expected counts (birth_info 3,
   death_info 4) exclude them — folding Wydell in would make
   death_info changes 5, and Ruth Ann would make birth_info 4
   and death_info 5. If Jequan extends scope on the word at run
   time, that is a plan amendment (new plan entries + gates),
   not something the runner should improvise.
10. **David's source-1270 citations (30532, 30533)** are
    prefixed SUPERSEDED in place on his Birth/Death facts,
    following the section 3a pattern Addendum 2 points to, and
    the pre-correction fact + citation rows are also captured
    in the register as "fact_superseded_in_place" so the old
    values survive in two places.
11. **Honest-evidence note carried into the run output:** the
    script prints, and the run report should repeat, that the
    1929 Newark birth registration behind citation 30159 has
    never been read; it is an asserted citation, retained as
    superseded under the obituary-override rule. Pulling it at
    the Delaware Public Archives is the section 10 item 5
    research follow-up, not a blocker.

## For the runner

Copy the .py and .json into `fixes/samuel-thompson-jr-correction/`
on the package branch, run
`python3 apply_samuel_thompson_jr_correction.py <path-to-genealogy_preservation.db>`,
and expect: the backup line, the pre-state line (persons 3799,
facts 6, citations 9, relationships 15, sources 2674 on a
pristine DB), 30 PASS gate lines, the tallies (names 5,
birth_info 3, death_info 4, sources created 3, register entries
13), "Register updated", and "COMMITTED." Anything else — a
SCHEMA SURPRISE or exit 3/4 — means stop, restore from the named
backup, and report; do not retry uncorrected. Then full export,
push, and Orbit verifies from origin before merge, per standard
package rules.
