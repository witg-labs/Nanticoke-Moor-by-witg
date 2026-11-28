# John Clark 3591 Untangle Package

Branch `fix/john-clark-3591-untangle`, folder
`fixes/john-clark-3591-untangle/`. Untangles profile 3591
("John Clark"), which merged two men separated by more than a
century (research of 28 Nov 2026; findings file
`~/workspace/genealogy-records/clark-john-3591/profile-3591-disentangled-2026-11-28.md`).

## Files

| File | Purpose |
| --- | --- |
| `SPEC.md` | This document. |
| `john_clark_3591_untangle_package.json` | Spec data loaded by the apply script: the dependency gate, person pre/post state, relationship removals, the fact move, fact detaches, the death-fact edit, expected counts. |
| `audit_3591.py` | Read-only preflight audit. Run it against the live database before the apply run (step 1 below). |
| `apply_john_clark_3591_untangle_package.py` | The apply script. Backup-first, single transaction, idempotent, stop-on-surprise. |
| `unassigned_evidence_register.json` | Shipped empty of detachments; the apply run rewrites it after commit with the real detached rows/facts and the moved fact. |
| `test_3591_harness.py` | Simulation harness (8 tests) against a full-scale mock. Must be green before any live run. |
| `BUILD_REPORT.md` | Added after the live run, per the batch-package pattern. |

## The two men

Profile 3591 merged:

1. **The John Clark of the Revolutionary-era Sussex County
   Clark family** — son of Levin Clark (9350) in the family
   tree, which also places the same sibling set (Whittington,
   John, Nathaniel, Comfort, Elizabeth, Lavenia) under Thomas
   Clark and Elizabeth Morris (8514). Born in the 1780s (tree
   variants: b. 14 Jul 1783, d. 20 Jul 1834, under Levin Clark
   + Esther Aydelott; b. 1789 under Thomas Clark + Elizabeth
   Morris), dead by/in 1834. Fact 15454's document mention
   (ClarkThomas.htm) lists that sibling set as children living
   in 1834 or dead by 1834. This is the man who stays on 3591.
2. **John Wesley Clark Jr (8193, 1894-1964)** — husband of
   Lulu Rae Carey (8194) and father of Ethel Gwendolyn Clark
   and her siblings. The Mitsawokett Carey photo page
   (3591's `source_page`) captions a photograph "John Clark is
   the husband of Lulu Rae Carey", and Mitsawokett's own
   genealogy pages name Lulu's husband as John Wesley Clark Jr
   throughout. The archive's enrichment attached Jr's 1930
   census household, spouse link, and child links to 3591 as
   well as to 8193.

The `d. 1918` on 3591 belongs to neither man (1834 vs 1964);
its citations are enrichment boilerplate quoting no record.

## Dependency (hard gate)

**This package runs AFTER `ep8-davis-corrections`.** The Ep8
package deletes the `child_of` row (8192 -> 3591) and any
stored reciprocal. The audit prints
`EP8 DEPENDENCY: rows between 8192 and 3591: <n>`; the apply
script aborts with the dependency message while any row
between 8192 and 3591 still exists. The harness models the
post-Ep8 state for its clean runs and proves the abort with
the 8192 rows present (test 3).

## What the package does

**Relationship removals** (discovered at runtime in both
directions and all types, gated on exactly the discovered
rows, per the 9928 lesson; `cross_dataset_match` rows are
ignored by design, per the 439 lesson, and any other
unexpected row type aborts):

- Spouse rows between 3591 and 8194 (single forward row or
  reciprocal pair; both storage variants are harness-proven).
- `child_of` / `parent_of` rows between 3591 and each of 8195
  (Carlisie), 8210 (Millie), 8196 (Wilfred), 8207 (Arlie
  Benjamin): a stored `parent_of` reciprocal may or may not
  exist per child; an orphan reciprocal aborts. Each primary
  row must carry the audited 1930-census evidence and
  `census_confirmed` certainty.
- Kept: both GEDCOM `child_of` parent links (9350, 8514).

**Fact move.** Fact 16058 (the 1930 census household) moves
from 3591 to 8193, who has no 1930 census fact. Citations
21977 (boilerplate naming the 1850 census) and 21978
(boilerplate naming the 1910 census) are marked SUPERSEDED in
place; citation 14868, the real 1930 citation, stays live.

**Fact detaches to the register** (fact row + its citations,
with reasons): fact 19493 (boilerplate Marriage assertion;
Jr's marriage to Lulu is recorded on his own profile, fact
24389); fact 15220 (1795 Broadkill Hundred tax list: an adult
householder when this man was a child); fact 15255 (1682
titheables list: a century before his birth). Neither mention
citation quotes text tying the mention to the son of Levin
Clark.

**Death correction.** Fact 11986: date `1918` -> `1834`, value
rewritten to state the tree's 20 Jul 1834 and the former
error. Citations 15696 and 21976 marked SUPERSEDED in place.

**Person row 3591.** `death_info` `1918` -> `1834`;
`source_page` `CareyCharlesE&DellaRidgeway.htm` -> `Davis
Family Tree.ged`; `dataset_source` `mitsawokett_delaware` ->
`davis_family_gedcom`; `birth_info` stays null; the ingest
note is replaced by the untangle note (marker `[Untangled
2026-11-28`).

**Dataset decision (audited).** 3591's `dataset_source`
(`mitsawokett_delaware`) differs from the GEDCOM-sourced
value on profile 9622 (John Wesley Clark Sr, `source_page`
`Davis Family Tree.ged`), so the package aligns 3591 to
9622's value, `davis_family_gedcom`. The apply script reads
9622's live row and aborts if it does not match the audited
values, and if the spec's post-state does not mirror it.

## Expected counts (gated in-transaction)

| Measure | Pre | Post |
| --- | --- | --- |
| persons | 3807 | 3807 |
| sources | unchanged (gated against the pre-run count; 2693 before the Ep8 package, 2701 after it) | same |
| facts on 3591 | 7 | 3 (2967 Name, 11986 Death edited, 15454 Document Mention) |
| facts on 8193 | 9 | 10 (+ moved 16058) |
| relationships touching 3591 | audited set | pre-state minus exactly the deleted spouse/child rows; the two parent links (and any ignored `cross_dataset_match` rows) remain |

Read-backs: fact 11986 shows date `1834` and the corrected
value; fact 16058 reads on person 8193 with citation 14868
live and 21977/21978 SUPERSEDED; citations 15696/21976
SUPERSEDED; facts 19493/15220/15255 and citations
21979/14022/14057 absent; the person row reads in post-state;
the relationship id sets of 3591, 8193, 8194 and each child
equal their pre-state minus exactly the deleted ids.
`PRAGMA integrity_check` must return `ok`. Backup written
first; single transaction; any gate failure rolls back.

## Idempotency

The death edit is keyed on fact_id with guards accepting the
pre-state or the post-state values only; SUPERSEDED markers
are appended only when absent; the move is keyed on
(fact 16058, current person in {3591, 8193}); detaches are
keyed on fact_id absence on re-run; relationship deletions
are keyed on the audited row ids, absent on re-run; the
person-row rewrite is keyed on the `[Untangled 2026-11-28`
marker and the post-state field values. A second run detects
the applied state, verifies only, changes nothing, and leaves
the register file as it stands.

## Run procedure (on the PC, against the live database)

Run only after the ep8-davis-corrections package has been
applied to the live database.

1. **Audit.** `python3 audit_3591.py <path-to-db>` and read
   the output: schema, totals, 3591's full rows, 8193's fact
   list, 9622's alignment values, the `EP8 DEPENDENCY` line
   (must read 0), and the `WILL DELETE` lines with row ids.
2. **Arm the id gates.** Put each pair's WILL DELETE ids into
   that removal's `"expected_ids"` list in
   `john_clark_3591_untangle_package.json` (shipped `null` =
   unarmed; an unarmed run still gates on each row's type,
   parties, direction, evidence and certainty, and prints a
   warning per removal). The harness proves the abort paths;
   the armed comparison runs in pre-state mode.
3. **Apply.** `python3 apply_john_clark_3591_untangle_package.py
   <path-to-db>`. Expect the timestamped backup line, every
   gate PASS, `COMMITTED.`, and the register-written line.
4. **Verify.** Re-run the audit; confirm the post-state counts
   and read-backs, then run the project export and integrity
   check as usual. Add `BUILD_REPORT.md` with the run record.
