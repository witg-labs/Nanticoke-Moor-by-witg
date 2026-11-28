# Lydia E Norwood un-redaction fix: build report

Built by Orbit, 2026-11-27, at Jequan Davis's direction (he picked
"Build the Lydia un-redaction fix" from the options offered with
the obituary-dates closeout).

## Diagnosis (from the obituary-dates run's diagnostic print)

Profile 9334's database state is now correct (birth_info
"abt 1790", Birth fact 8705 "abt 1790" cited to the 1850 census
source 853, death 26 Dec 1856), but the export still redacts her:
the exporter's is_probably_living() matches the word "living" in
a person's notes, and her long biographical notes say the
Nanticoke community "remains a living reality" (the run agent
identified that phrase as the trigger). Exported result:
is_living true, birth_info "Private", death_info "", notes "",
facts []. She has been hidden by this false positive since long
before the current package series.

## Contents (one transaction)

- Notes wording: every occurrence of "a living reality" becomes
  "a thriving reality" (her notes use "continues to thrive" for
  the same community elsewhere; meaning preserved). The script
  prints every "living" occurrence with context first, and
  aborts if any "living" substring would remain after the swap,
  rather than guessing at further wording. A final gate requires
  the new notes to be byte-identical to the old apart from the
  swapped phrase.
- Flags: Census fact 25218 (dated 1790, generic import
  boilerplate) and Marriage fact 25219 (generic import) flagged
  generic_unverified in fact_quality_flags, the same soft
  treatment as the obituary-dates batch, so her profile is clean
  when it appears.
- Nothing else: no facts, fields, sources, or relationships
  change. Persons 3,801 and sources 2,689 unchanged.

Expected export after the run: living-redacted count 39 -> 38;
person/9334.json shows birth_info "abt 1790", her five facts
(Name, Birth abt 1790 with the 1850 census citation, Death
26 Dec 1856, Census 1790, Marriage), and her full notes including
the obituary-dates conflict append.

## Simulation proof (2026-11-27, local harness, not shipped)

Mock carried 3,801 persons, 2,689 sources, and Lydia's exact
post-obituary-dates shape (five facts 8704/8705/8706/25218/25219;
notes seeded with the trigger phrase twice plus "lived"
instances and the conflict append). Harness 13/13 PASS: fresh run
commits with all 9 in-script gates green and the rest of the
notes byte-identical; second run is a true no-op; a mock with an
additional unrelated "living" instance ("living descendants")
aborts with exit 3 and leaves the notes untouched, as designed.

Correction (2026-11-27, after the first live run aborted cleanly on the pre-state gate): the expected sources count was written as 2,690, derived from the highest source IDs created that day; the audited figure is 2,689 (2,683 before the obituary-dates package plus its six new sources; the 1850 census source already existed). The script aborted before any change, exactly as designed; the database was verified unchanged by hash. Spec corrected and re-pushed.
