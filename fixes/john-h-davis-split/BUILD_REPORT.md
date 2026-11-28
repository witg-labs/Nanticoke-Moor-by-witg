# John H Davis (8890) three-way split package: build report

Built 2026-11-27 by Orbit. Authority:
`gedcom-citation/CONFLATION_RULINGS.md`, Jequan Davis ruling
2026-11-22: profile 8890 SPLIT THREE WAYS. The 1819-1886 man
keeps the profile; the 1738-1840 man (Holy Trinity burial, Find a
Grave #137944370) becomes a profile; the abt 1889 son of Maurice
Davis takes the 1900 census fact and both photo documents.
Cross-quoting citations reattached to the correct man.

## Audit (live export, 2026-11-27; case file: CONFLATION_CASES.md, Person 8890)

Profile 8890 held 11 facts for three men:

- Kept life (1819-1886): 8263 Name "John H. Davis", 8264 Birth
  3 Jan 1819, 8265 Death 19 Sep 1886 (aged 67), 14034 and 15348
  Document Mentions (a John Davis with wife Mary Elizabeth
  Jackson; compatible with this era, impossible for the 1840
  death). The person row, however, carried the 1738 man's dates
  (birth_info "1738", death_info "1840 (aged 101-102)") and his
  Find a Grave note.
- Second life (1738-1840): 8381 Name "John H Davis", 8382 Birth
  1738, 8383 Death 1840, 24990 Burial (Find a Grave #137944370,
  Holy Trinity Churchyard). His only non-GEDCOM support is the
  burial; research register item 5 is queued.
- Third life (abt 1889): 15997 Census 1900 (Son, age 11, in the
  Indian River Hundred household of Maurice Davis) and both
  photos on the profile (3462, the 1900 household document; 3482,
  a WWI-era household document). The household's other children
  are profiled as children of Morris Davis (12006) and Hester A.
  Morris Davis (11247); the census head "Maurice" is Morris.
- Cross-attached citations: 31525 ("born 1738") sits on the 1819
  man's birth fact 8264 and 31526 ("deceased 1840") on his death
  fact 8265; both belong on the 1738 man's facts. Citations 31528
  (1790 census boilerplate) and 31529 (1840 census boilerplate)
  sit on the 1900 census fact, naming no age or household.
- Fits none of the three with confidence: 24991, an undated
  generic marriage fact ("Marriage record documented for John H
  Davis", no spouse named).
- The only relationship, child_of Joseph Henry Davis (8613),
  carries no dates and stays on 8890, per the spec.

Name handling: persons.name is UNIQUE. Profile 8890 is renamed
to "John H. Davis", the punctuated form its own kept Name fact
8263 records, BEFORE the new profile is created as "John H
Davis", the form fact 8381 records. The script performs the
rename first inside the transaction for exactly this reason.

## Package content

- 8890 renamed "John H. Davis"; person row set to b. 3 Jan 1819,
  d. 19 Sep 1886 (aged 67); the "Verified via FindAGrave"
  memorial 137944370 note line removed (it moves to profile A);
  split note appended. Keeps facts 8263, 8264, 8265, 14034, 15348.
- New profile A "John H Davis" (1738-1840), facts 8381, 8382,
  8383, 24990, notes carrying the Find a Grave memorial text.
- New profile B "John H Davis (Son of Maurice)" (b. abt 1889),
  fact 15997, person_photos rows for photos 3462 and 3482 moved
  from 8890, unified_photo_catalog.primary_person_id updated to
  B where it pointed at 8890, and child_of links to Morris Davis
  (12006) and Hester A. Morris Davis (11247), certainty
  census_confirmed.
- Both new profiles: evidence_level copied at runtime from
  split-created profile 12007 (the unproven value, 1);
  source_page and dataset_source copied from 8890.
- Citations 31525 and 31526 moved to facts 8382 and 8383;
  citations 31528 and 31529 marked SUPERSEDED in place.
- Fact 24991 detached to
  `fixes/john-h-davis-split/unassigned_evidence_register.json`
  with its citation intact (script writes it only after commit).
- Persons 3,803 -> 3,805; sources unchanged at 2,693.

## Simulation

`test_harness.py` (local only, not shipped) builds a mock from
the profile's real facts and citations as read from the live
export, with person_photos rows for 3462/3482 and
unified_photo_catalog rows carrying the live NOT NULL columns
(normalized_filename, original_filename, local_image_path,
sha256_hash). Fresh run commits with all 17 gates green and
writes the register (1 fact, citation intact); second run is a
true no-op; a renamed-profile mock aborts untouched (exit 3) and
creates no profiles. Harness: 22/22 PASS.

One gate correction during the build: the first simulation run
failed the notes gate because the spec's own split note for 8890
mentions "Find a Grave #137944370" while narrating the split.
The gate now tests for the removed note line itself ("Verified
via FindAGrave"), which is what the spec orders removed; the
memorial number's appearance inside the split note is the spec's
own text and stays.

## Live run (2026-11-27)

Ran on the live database in the five-package batch: all 17 gates passed, committed, re-exported (3,805 persons, 38 redacted, integrity PASSED), export pushed as 4dfb301b57e7ea5e4f6cafbad2b418f87afb371e. New profiles 12021 (John H Davis) and 12022 (John H Davis (Son of Maurice)). This note was appended by Orbit to retrigger PR checks.
