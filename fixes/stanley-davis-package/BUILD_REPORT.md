# Stanley Oliver Davis Sr correction package: build report

Built by Orbit, 2026-11-27. Spec:
`~/workspace/family-archive/STANLEY_DAVIS_CORRECTION_2026-11-23.md`
(Jequan's settled ruling of 2026-11-23: profile 8155 IS Stanley Oliver
Davis Sr, 5 Feb 1941 to 22 Jun 2021, Millsboro; the archive's 1990 death
is the error).

## Audit (against origin/main @ bf0013e, post-Joan export)

- 8155 today: birth_info "unknown", death_info "1990"; parents 8609 and
  8146 already correct; no photos. Facts: Name 7585 (GEDCOM source 622);
  Birth 7586 "unknown" (citations 7580 GEDCOM, 30115 source 1270
  boilerplate "born unknown"); Death 7587 "1990" (7581 GEDCOM, 30116
  source 1270); Burial 24322 (1990, "Delmarva", "Interred in Delmarva
  cemetery (Find a Grave #66421404)", citation 30117, source 2333);
  Census 24323 dated 1920 (citations 30118 source 859, 30119 source 862,
  both generic import text); Marriage 24324 generic (source 1270).
- Profile notes carry the import line "Verified via FindAGrave:
  .../memorial/66421404/stanley-davis (Buried at Alvinston Cemetery)".
  Alvinston Cemetery is in Lambton County, Ontario, Canada, and
  memorial numbers in the 66M range date from about 2011, a decade
  before this man's 2021 death. Verdict under the spec's apply-time
  test: memorial 66421404 is a DIFFERENT Stanley Davis. (Find a Grave
  itself bot-walled a direct read on 2026-11-27; the verdict rests on
  the archive's own import note plus the memorial-number era, and on
  the two independent contradictions of the 1990/Ontario life: his
  sister Maryland's Feb 2020 program naming him a surviving brother,
  and his tree profile's Find A Grave Index-sourced 2021 death.)
- Portrait: the kitchen portrait Jequan supplied 2026-11-23 (filed at
  ~/workspace/genealogy-records/stanley-davis/) is byte-identical to
  frontend/public/assets/archive_media/people/Davis_Stanley_Oliver_Sr.jpg
  on branch fix/stanley-davis-photo (sha256 4ba8372f..., 369,371 bytes,
  verified 2026-11-27). No photo row exists in the live catalog for it
  (the branch's old hand-built export row 3678 never entered the DB),
  so the package creates the catalog row fresh; expected id 3708.
  The branch's photos.json conflict was resolved to main's version on
  2026-11-27 at Jequan's direction; the image file is untouched there
  and the run checks it out from that branch.

## Contents (one transaction)

- Birth fact 7586 set to 5 Feb 1941, Millsboro, Sussex County,
  Delaware; Death fact 7587 set to 22 Jun 2021, Millsboro; persons
  birth_info/death_info set to match. Both cited to a new
  family_statement source recording Jequan's 2026-11-23 confirmation
  of the tree profile, with the tree's own source basis quoted
  (U.S. Find A Grave Index; U.S. Public Records Index; sources
  screenshot filed 2026-11-23).
- Citations 7581, 30115, 30116 marked SUPERSEDED in their evidence
  text (original text preserved after the marker), not deleted.
- Burial fact 24322 corrected in place (date cleared, place Millsboro,
  Sussex County, Delaware, value states the cemetery is not named in
  the sources read); citation 30117 detached to the register.
- Census fact 24323 detached whole to the register with citations
  30118 and 30119 (a man born in 1941 cannot be enumerated in 1920;
  prevention rule).
- Marriage fact 24324 left in place, flagged generic_unverified in
  fact_quality_flags.
- Notes: marker-guarded correction append recording the memorial
  verdict and the corrected life dates; the original import line is
  NOT removed.
- Photo: unified_photo_catalog row + photo_catalog title row +
  person_photos link (is_primary 1, his only photo) using the
  branch-verified field set (title Davis_Stanley_Oliver_Sr.jpg,
  category people, portrait, contains_face 1, primary_subject).

Expected counts: persons 3,801 unchanged; sources 2,682 -> 2,683;
facts on 8155 6 -> 5; photos 2,885 -> 2,886; register +2 entries.

## Simulation proof (2026-11-27, local harness, not shipped)

Mock carried persons.name UNIQUE, the live NOT NULL photo-catalog
constraints, 3,801 seeded persons, 2,682 sources, and 8155's exact live
fact/citation set. Harness 24/24 PASS: fresh run commits with all 20
in-script gates green; second run is a true no-op (zero deltas, register
file byte-identical); a tampered burial place aborts with exit 3,
rollback, and no register written.
