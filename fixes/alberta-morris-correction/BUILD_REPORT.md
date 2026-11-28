# Alberta Morris (8345) correction package: build report

Built 2026-11-27 by Orbit. Authority:
`gedcom-citation/CONFLATION_RULINGS.md`, Jequan Davis ruling
2026-11-22: profile 8345 is ONE woman, NO SPLIT. Adopt b. 27 Sep
1939, d. 26 Apr 1983 (aged 43); the GEDCOM "1971 Residence" is a
residence note mis-typed as a death; the GEDCOM b. 5 Mar 1937 is
flagged superseded and stays visible (orphan rule: superseded
dates stay visible as superseded, not erased).

## Audit (live export, 2026-11-27, after the 439 merge)

Profile 8345 held 9 facts. The adopted dates already existed as
facts from the vital-records dataset (6876 Birth 27 Sep 1939, 6877
Death 26 Apr 1983), but the person row still carried the GEDCOM
values (birth_info "5 Mar 1937 Delaware, USA", death_info "1971
Residence"), and two vital-record citations quoted the GEDCOM
dates while sitting on the adopted facts: 30505 ("born 5 Mar
1937") on fact 6876 and 30506 ("deceased 1971 Residence") on fact
6877. Citation 30508 (1950 census text) sits on the 1940 census
fact 24506 with no 1950 census fact on the profile, the same
pattern as citation 17371 in the 439 package. Relationships
(child_of Edgar Coil Morris Sr 8274, child_of Sarah Jane Morris
8339) are untouched by this package and are not gated on, per the
439 lesson; neither are any cross_dataset_match rows, if present.

## Package content

- Person 8345: birth_info -> "27 Sep 1939", death_info ->
  "26 Apr 1983 (aged 43)".
- Fact 7798 (GEDCOM Birth, 5 Mar 1937): flagged 'superseded' in
  fact_quality_flags with the ruling cited; the fact and its
  citations stay in place.
- Fact 7799 (GEDCOM "Death", "1971 Residence"): retyped to
  Residence, date "1971".
- Citations 30505 and 30506 move onto facts 7798 and 7799, the
  facts their text describes (prevention rule).
- Citation 30508 marked SUPERSEDED in place (439 precedent).
- Correction note appended to the profile (notes were empty).
- No new profiles, no new sources, no relationship changes:
  persons stay 3,802, sources stay 2,693.

## Simulation

`test_harness.py` (local only, not shipped) builds a mock from the
profile's real facts and citations as read from the live export,
under the live constraints. Fresh run commits with all 13 gates
green; second run is a true no-op; a tampered person row aborts
untouched. Harness: 14/14 PASS.

## Spotted, not in this package

Fact 24507 dates an SS-5 application to 1937, which fits neither
birth year on the profile (an infant does not file an SS-5). It is
the same NUMIDENT boilerplate pattern as the held SS-5 fact in the
Geraldine Jackson ruling; left untouched here for a ruling.
