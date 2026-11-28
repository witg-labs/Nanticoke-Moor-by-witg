# Episode 8 Davis Corrections Package

Branch `fix/ep8-davis-corrections`, folder
`fixes/ep8-davis-corrections/`. Record-backed corrections for
Ethel Gwendolyn Clark (8192) and Harry Edward Davis (8159) from
the Episode 8 (Tidewater Lives) research of 28 Nov 2026.

## Files

| File | Purpose |
| --- | --- |
| `SPEC.md` | This document. |
| `ep8_davis_corrections_package.json` | Spec data loaded by the apply script: sources, fact edits, new facts, notes appends, the detach, the photo fix, expected counts. |
| `audit_ep8.py` | Read-only preflight audit. Run it against the live database before the apply run (step 1 below). |
| `apply_ep8_davis_corrections_package.py` | The apply script. Backup-first, single transaction, idempotent, stop-on-surprise. |
| `unassigned_evidence_register.json` | Shipped empty of detachments; the apply run rewrites it after commit with the real detached row ids. |
| `test_ep8_harness.py` | Simulation harness (11 tests) against a full-scale mock. Must be green before any live run. |
| `BUILD_REPORT.md` | Added after the live run, per the batch-package pattern. |

## What the package does

**New sources (8, ids assigned at runtime as max+1 in spec
order).** Ethel's funeral program; both spouses' Social Security
NUMIDENT records; Harry's VA gravesite record; the 1920 and 1950
census households; the New Jersey Bride Index entry; Harry's
WWII draft card. Dataset values are copied at runtime from live
reference sources (667 `mitsawokett_obits` for the program, 1281
`social_security_administration` for the NUMIDENT records, 1274
`cemetery_survey` for the VA record, 860 `Delaware Federal
Census` for the censuses); the two FamilySearch index/card
sources carry the literal `familysearch` (verified in use by
sources 2698/2699). Inserting a source with an empty url is
proven safe (sources 2710-2713).

**Profile 8192 (Ethel Gwendolyn Clark), facts 6 -> 8.**

- Marriage fact 24387 edited: date set to `8 Apr 1938` (funeral
  program), place `Delaware` cleared to empty (no Delaware
  marriage record was found in the Delaware Marriage Records,
  1913-1954, in the searches of 28 Nov 2026; a New Jersey Bride
  Index entry for 1938 exists and the place of marriage is
  unproven), value rewritten to say exactly that. Citations added
  from the funeral program and the bride index.
- New Burial fact: Harmony United Methodist Church Cemetery,
  Millsboro, 1997, cited to the funeral program.
- New Census fact: the 1950 household (ED 3-59, household 304),
  cited to the 1950 census source.
- Research note appended (marker `[Episode 8 research
  2026-11-28]`): the program's record of her work at
  Stuart-Kingston's in Rehoboth, her Harmony United Methodist
  Church service, her Nanticoke Indian Association membership,
  the four girls she and Harry reared besides Sheila, her
  parents as named in her Social Security file and Delaware
  birth record, and the reason for the 3591 detach.
- The `child_of` link to John Clark (3591) is detached to the
  register (below).

**Detach (8192 -> 3591).** The apply script discovers every
relationship row between 8192 and 3591 in both directions and
all types, and gates on exactly those rows (the 9928 lesson:
relationship storage is not uniform). It requires exactly one
`child_of` row (8192 -> 3591) whose evidence_text is
`Confirmed in 1930 US Federal Census as Daughter of household
head (Milton, Sussex, Delaware, USA)` and whose certainty is
`census_confirmed`; it deletes that row and, if present, a
stored reciprocal `parent_of` row (3591 -> 8192). Any other row
type between the pair, multiple primaries, or an orphan
reciprocal aborts the run. Nothing else on profile 3591 or on
any sibling profile is touched. The deletion is recorded in
`unassigned_evidence_register.json` with the reason: no record
names 3591 as her father, and a man who died in 1918 cannot be
the father of her siblings born in the 1920s; whether 3591 is a
different man or a duplicate of John Wesley Clark Jr (8193)
remains open.

**Profile 8159 (Harry Edward Davis), facts 7 -> 9.**

- Birth fact 7595: date `unknown` -> `22 Aug 1916 Millsboro,
  Sussex, Delaware, USA` (guarded on the date only; the fact's
  export value_string is None). Citations added from his
  NUMIDENT record, the VA gravesite record, and his draft card.
- Death fact 7596: date `1 Feb 1932` -> `31 Jan 1999` (guard:
  the current value must be one of those two). The 1932 date is
  GEDCOM-layer error, disproven by his 1938 marriage, his
  daughter Sheila's 1939 birth, his 1940 draft registration and
  WWII Army service, and both his VA and Social Security
  records. Citations added from the NUMIDENT and VA records.
- Burial fact 24332: date `1999 (aged 82–83)` -> `1999`, place
  `Delmarva` -> `Harmony Cemetery, Millsboro, Sussex, Delaware,
  USA`, value rewritten. Date and place are guarded strictly;
  the value guard accepts either observed pre-state variant
  (`Burial record documented for Harry Edward Davis` or the
  export's `Interred in historical Delmarva cemetery`) or the
  post-state value, and aborts on anything else. VA citation
  added.
- New Census fact 1920: the ED 198 household 353 of his brother
  Stephen, with their widowed mother Hester. **Folding guard:**
  fact 24333 already exists on 8159 as a Census fact dated
  `1920` (boilerplate enrichment), so all new facts are keyed on
  the 4-field key (person_id, fact_type, date_string,
  value_string) and the new fact stays distinct from 24333;
  8159 correctly reaches 9 facts.
- New Census fact 1950: the same ED 3-59 household as on 8192.
- Person row: birth_info `1916` -> `22 Aug 1916`, death_info
  `1999 (aged 82–83)` -> `31 Jan 1999 (aged 82)`.
- Correction note appended (same marker; existing notes text is
  never altered): the disproven 1932 date, his record-confirmed
  parentage (Morris Davis and Hester Morris, per his Social
  Security file and the 1920 household), and the note that the
  FindAGrave memorial number in the earlier notes (36969032)
  could not be verified in Nov 2026, the VA record being the
  burial source of record.

**Photo 611.** Schema-discovering fix: for each of
`unified_photo_catalog` and `photo_catalog`, if the table has
`approximate_year` / `dates_mentioned` columns and a row for
photo 611, the row's values must be the audited pre-state
(`1916` / `["1916"]`) or the post-state (`unknown` / `[]`); the
pre-state is rewritten to `unknown` / `[]`. If neither table
carries a year for 611 the run aborts rather than guessing
another location. Photo 617 (Harry's portrait, where 1916 is
his real birth year) is snapshotted before the run and gated
unchanged after it. No other photo is touched.

## Expected counts (gated in-transaction)

| Measure | Pre | Post |
| --- | --- | --- |
| persons | 3807 | 3807 |
| sources | 2693 | 2701 (+8) |
| facts on 8192 | 6 | 8 (1 edited, 2 new) |
| facts on 8159 | 7 | 9 (3 edited, 2 new) |
| relationships | — | exactly the detached row(s) removed; every other row id touching 8192/8159 unchanged |

Read-backs by full key: fact 24387 (date `8 Apr 1938`, place
empty), fact 7596 (`31 Jan 1999`), fact 7595, fact 24332, and
each new fact by its 4-field key. `PRAGMA integrity_check` must
return `ok`. Backup written first; single transaction; any gate
failure rolls back.

## Idempotency

Sources keyed on title; new facts keyed on the 4-field key;
edits keyed on fact_id with per-field guards accepting the
pre-state or the post-state value only; notes appends keyed on
the marker; the detach keyed on the discovered row (absent on
re-run). A second run detects the applied state, verifies only,
changes nothing, and leaves the register file as it stands.

## Run procedure (on the PC, against the live database)

1. **Audit.** `python3 audit_ep8.py <path-to-db>` and read the
   output: schema, totals (3807 persons / 2693 sources), both
   profiles' full rows, both catalog rows for photos 611/617,
   the reference datasets, and the `DETACH child_of row id`
   line.
2. **Arm the id gate.** Put the printed id into
   `"expected_relationship_id"` in
   `ep8_davis_corrections_package.json` (shipped `null` =
   unarmed; an unarmed run still gates on the row's type,
   direction, evidence_text and certainty, and prints a
   warning). The harness proves the abort on a wrong armed id.
3. **Apply.** `python3 apply_ep8_davis_corrections_package.py
   <path-to-db>`. Expect the timestamped backup line, every
   gate PASS, `COMMITTED.`, and the register-written line.
4. **Verify.** Re-run the audit; confirm the post-state counts
   and read-backs, then run the project export and integrity
   check as usual. Add `BUILD_REPORT.md` with the run record.
