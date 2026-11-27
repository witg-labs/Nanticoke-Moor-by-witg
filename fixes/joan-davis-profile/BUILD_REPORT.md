# Joan Ellen Davis living-profile package: build report

Built by Orbit, 2026-11-27. The Maryland Davis package audit (2026-11-27)
identified the gap: Maryland's sister Joan, named throughout her program,
had no profile. Jequan commissioned the profile on 2026-11-27 with the
direction that she is living.

## Audit (against origin/main @ 4064fc40, post-Maryland export)

- No person named Joan Davis or Joan Ellen Davis exists anywhere in the
  3,800-person export (nearest names are other people: Joan Johnson 1697,
  Joan Dixon 4802, Joan Durham 4928, Joan Elaine Clark 8211). Max
  person_id is 12017 (Maggie Mosley), so the new profile is 12018.
- No profiles exist for Clifford Hammond, Jane Davis, Sandra Davis, or
  Toney Floyd, so no spouse or child links are created; her children are
  named in the notes only, from her sister's program.
- Living-profile shape follows the Samuel Thompson package precedent
  (profiles 10097 and 8265): birth_info and death_info are the string
  "unknown", and no Birth or Death fact is created. Her real birth date
  (19 Nov 1945, family knowledge) is deliberately NOT stored or displayed,
  per Jequan's living-people rule of 2026-11-27.
- Evidence: the 1950 census fact already on her sister Maryland's profile
  (fact 16134, source 862) enumerates "Joan Ellen Davis (Granddaughter,
  age 3)" in Samuel and Martha Thompson's household with her mother Phoebe
  Davis in the house; Maryland's funeral program (source 2700, created by
  the Maryland package run) names Maryland's parents as William Wesley
  Davis and Phoebe (Thompson) Davis and Joan Davis as Maryland's sister.
  Both parent links carry that evidence text; a new family_statement
  source records Jequan's 2026-11-27 direction.

## Contents (one transaction)

- Person created: 12018 Joan Ellen Davis (first Joan, middle Ellen,
  maiden Davis; dataset_source davis_family_gedcom; evidence_level 1;
  notes carry the living marker, her parentage, and her children as named
  in Maryland's program; her street address is NOT included).
- Source created: Statement of Jequan Davis, 2026-11-27 (family
  knowledge; Joan Ellen Davis, living profile), dataset family_statement.
- Facts: Name (cited to the statement source); Census 1950 (cited to
  source 862 with evidence text quoting her own enumeration line).
- Relationships: child_of Phoebe Thompson 8146 and child_of William
  Wesley Davis Sr 8609, both certainty "confirmed" with quoted evidence.

Expected counts: persons 3,800 -> 3,801; sources 2,681 -> 2,682; facts on
12018: 2; relationships touching 12018: 2; photos unchanged at 2,885;
obituaries 400; documents 334.

## Simulation proof (2026-11-27, local harness, not shipped)

Mock carried persons.name UNIQUE, the live column sets for all five
tables, 3,800 seeded persons (max id 12017), and source stubs 862/2700
among 2,681 sources. Harness 17/17 PASS: fresh run commits with all 14
in-script gates green (person 12018 created, living fields 'unknown', no
Birth/Death facts, both facts cited, both parent links present); second
run is a true no-op ("Person found: 12018", zero deltas on persons,
sources, facts, relationships); a tampered parent name aborts with exit
3, rollback, and no Joan created.
