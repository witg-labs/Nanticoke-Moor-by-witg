# John S Thompson (9561) cleanup package: build report

Built 2026-11-27 by Orbit. Authority:
`gedcom-citation/CONFLATION_RULINGS.md`, Jequan Davis ruling
2026-11-22: profile 9561 NO SPLIT. One infant, b. 9 Feb 1928
Stockley, d. 12 Jul 1930 Georgetown; "abt 1927" is a precision
variant of the same birth. Cleanup: remove the undated marriage
fact and detach the two group photos to the unidentified-photo
pool. Orphan rule: nothing detached is deleted outright; the
marriage fact goes to the unassigned-evidence register with its
citation.

## Audit (live export, 2026-11-27)

The case file (`gedcom-citation/CONFLATION_CASES.md`, "Person
9561 — John S Thompson") reads this profile as one person with a
precision difference, not two people merged, and the live export
confirms it in full:

- Kept life (7 facts): 7712 Name "Jack Thompson" (a standard
  nickname for John, no dates attached), 7713 Birth "abt 1927
  Delaware" whose vital-record citation 32395 quotes the exact
  9 Feb 1928 Stockley birth, so the apparent conflict is an
  attachment artifact, 7714 Death "12 Jul 1930 Georgetown",
  8882 Name, 8883 Birth "9 February 1928 Stockley, Sussex
  County, Delaware", 8884 Death "12 July 1930 Georgetown",
  25364 Census 1930 (a 2-year-old enumerated shortly before a
  July 1930 death). The parents on the profile, Samuel L.
  Thompson (9097) and Martha E Thompson (8147), married
  20 Sep 1917 per their own profiles, fit a 1928 child.
- Marriage fact 25365: undated, place "Delaware", value
  "Marriage record documented for John S Thompson", one
  citation (32398, source 1270) whose evidence text is generic
  ("Marriage record on file for John S Thompson") and whose
  source title is a birth register. A child who died 12 Jul 1930
  aged 2 cannot have married.
- Photos 2366 ("Thompson_John_And_Sarah.jpg", subject "Thompson
  John & Sarah") and 2368 ("Thompson_John_Family.jpg", subject
  "Thompson John Family"), both Mitsawokett group portraits with
  no approximate year. The titles imply an adult John Thompson
  with a Sarah and a family; nothing ties them to this child.

The export matches the package spec exactly: 9561's fact set is
the 8 expected facts, and the 2 attached photos are 2366 and
2368. Relationships are untouched by this package and are not
gated on, per the 439 lesson; neither are any cross_dataset_match
rows, if present.

## Package content

- Fact 25365 detaches to
  `fixes/john-s-thompson-cleanup/unassigned_evidence_register.json`
  with citation 32398 intact (the script writes the register
  only after the commit succeeds; the run agent commits it with
  the export).
- Photos 2366 and 2368 detach to the unidentified pool: 9561's
  person_photos rows for them are deleted, and
  unified_photo_catalog.primary_person_id is set to NULL where
  it equals 9561. Both the person_photos rows and the catalog
  rows are recorded in the register under `detached_photos`
  before anything changes.
- Correction note appended to 9561 (notes were empty).
- No new profiles, no new sources, no relationship changes, no
  edits to the 7 kept facts: persons stay 3,805, sources stay
  2,693.

## Simulation

`test_harness.py` (local only, not shipped) builds a mock from
the profile's real facts and citations as read from the live
export, with the live NOT NULL constraints of
unified_photo_catalog (normalized_filename, original_filename,
local_image_path, sha256_hash) in place. Fresh run commits with
all 8 gates green and writes the register (1 fact with its
citation, 2 photos with their rows recorded); second run is a
true no-op (applied state detected from the absent marriage fact
and the absent photo rows, end state verified only); a mock
carrying an extra unexpected fact on 9561 aborts with exit 3 and
changes nothing. Harness: 16/16 PASS.
