# Lydia J Harmon (9928) split package: build report

Built 2026-11-27 by Orbit. Authority:
`gedcom-citation/CONFLATION_RULINGS.md`, Jequan Davis ruling
2026-11-22: profile 9928 SPLIT. The 1776-1851 woman keeps the
profile. The 1848-1927 woman becomes a separate profile and takes
the Simon Harmon marriage. The Raymond Harmon / Hattie Miller
parentage fits neither and is detached from both, held as a
couple in the unassigned-evidence register.

## Audit (live export, 2026-11-27, after the 8857 merge)

Profile 9928 held 9 facts in two incompatible lifespans
(CONFLATION_CASES.md, Person 9928):

- Kept life (1776-1851): 9230 Name, 9231 Birth 16 Jan 1776, 9232
  Death 6 Mar 1851 (aged 75), 25645 Burial (Find a Grave
  #86408962), 25646 Census 1790. Supported beyond the GEDCOM by
  colonial vital-record citations quoting her own dates, the
  Find a Grave burial, and census citations.
- Split-off life (1848-1927): 9912 Name "Lydia J. Harmon", 9913
  Birth 30 Jul 1848, 9914 Death 28 Oct 1927 (aged 79), all
  GEDCOM-only, plus 25647, the undated generic Marriage fact
  ("Marriage record documented for Lydia J Harmon", Delaware).
  The ruling assigns the marriage to this woman; her husband
  Simon Harmon (b. abt 1835) fits a wife born 1848 and cannot
  fit the 1776-1851 woman.
- Fits neither: the child_of links to Raymond Harmon (9931,
  b. abt 1902) and Hattie Miller (8860, b. 1905). Parents born
  in 1902 and 1905 cannot have a daughter born in 1776 or 1848.

Relationships were read in the live DB's vocabulary, per the
439 lesson: the Simon Harmon link is stored as type 'spouse' in
reciprocal rows (9928 -> 10514 and 10514 -> 9928), which the
export renders as a single 'spouse_of'; the parentage links are
single child_of rows (9928 -> 9931, 9928 -> 8860). No photos on
the profile.

Pre-state counts are chained behind the packages ahead of this
one in the batch (8890 three-way split and 9561 cleanup land
first): persons 3,805, sources 2,693.

## Package content

- New profile "Lydia J. Harmon" (the name form her own Name fact
  9912 records; persons.name is UNIQUE and "Lydia J Harmon" is
  taken by 9928), birth_info "30 Jul 1848", death_info "28 Oct
  1927 (aged 79)", evidence_level copied at runtime from
  split-created profile 12007 (the unproven value, 1),
  source_page and dataset_source copied from 9928, notes stating
  the GEDCOM-only basis and the queued research (split research
  register item 3).
- Facts 9912, 9913, 9914, 25647 move to the new profile
  unchanged.
- The spouse link to Simon Harmon (10514) moves with her: both
  reciprocal 'spouse' rows are re-pointed to the new profile.
- The child_of rows to Raymond Harmon (9931) and Hattie Miller
  (8860) detach to
  `fixes/lydia-j-harmon-split/unassigned_evidence_register.json`
  as full relationship rows, held as a couple (the script writes
  the register only after the commit succeeds).
- Split note appended to 9928.
- Persons 3,805 -> 3,806; sources unchanged at 2,693; no new
  sources; no photos on either profile.

## Simulation

`test_harness.py` (local only, not shipped) builds a mock from
the profile's real facts and citations as read from the live
export, with relationships in the DB's vocabulary (reciprocal
'spouse' pair, single child_of rows). Fresh run commits with
all 9 gates green and writes the register (2 detached child_of
rows, the held couple); second run is a true no-op; a
renamed-profile mock aborts untouched. Harness: 15/15 PASS.

## Amendment (2026-11-27, after the first live run aborted)

The first live run aborted cleanly at the pre-state gate: "reciprocal spouse row (10514 -> 9928) count 0 != 1". The live DB stores the Simon Harmon marriage as a SINGLE forward 'spouse' row (9928 -> 10514, row id 855); no reciprocal row exists for this couple, unlike profile 439's pair. The run's diagnostic also showed a stored reciprocal 'parent_of' row (31492, 9931 -> 9928) for Raymond Harmon; Hattie Miller has none. The database was hash-verified unchanged after the abort.

Amended by Orbit: the spec records the audited rows (spouse rows_expected 1; reciprocal_parent_of_row_id_expected 31492 for 9931, null for 8860). The script now gates on spouse rows touching 9928 in either direction == 1 and on each parent_of reciprocal's presence, re-points the single spouse row, and detaches Raymond's parent_of reciprocal with its child_of row into the register (recorded as reciprocal_row). Final gates: exactly one spouse row touches the new profile; zero relationship rows touch 9928 except cross_dataset_match. Harness rebuilt to mirror the live rows (mock parent_of row carries the real id 31492): 16/16 PASS.
