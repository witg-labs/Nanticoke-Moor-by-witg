# Geraldine Jackson (9968) split package: build report

Built 2026-11-27 by Orbit. Authority:
`gedcom-citation/CONFLATION_RULINGS.md`, Jequan Davis ruling
2026-11-22: profile 9968 SPLIT. The infant (1937-1938) keeps the
profile, with her parents, burial #288073524, and the vital-record
citations that quote her dates. The adult (1925-1985) becomes a
separate profile with the marriage. The 1937 SS-5 fact is held
unassigned on the original profile. Cross-attached citations
sorted as part of the package.

## Audit (live export, 2026-11-27, after the 9928 merge)

Profile 9968 held 9 facts in three groups (case file:
CONFLATION_CASES.md, "Person 9968 — Geraldine Jackson"):

- Infant (keeps the profile): 9334 Name, 9335 Birth 30 Aug 1937,
  9336 Death 16 Apr 1938 (aged 7 months), 25716 Burial (Find a
  Grave #288073524). Her own birth and death facts are GEDCOM-only,
  but the burial and the person notes corroborate her, and the two
  Delaware vital-record citations that quote her exact dates were
  sitting on the adult's facts (below).
- Adult (splits off): 6881 Name, 6882 Birth 8 Aug 1925, 6883 Death
  22 Jul 1985 (aged 59), 25718 Marriage (undated, Delaware; only
  an adult could have married). Her dates rest on the Mitsawokett
  SterrettParisFamily.htm page (source 573), a secondary source.
- Fits neither: 25717 Social Security Application, dated 1937.
  The infant was born 30 Aug 1937 and died the following April;
  the adult would have been 11-12 in 1937. Held unassigned per
  the ruling.

The crossed citations: 33152, on the adult's birth fact 6882,
quotes a birth registration for "Geraldine Jackson, born 30 Aug
1937"; 33153, on the adult's death fact 6883, quotes a death
registration for "Geraldine Jackson, deceased 16 Apr 1938 (aged 7
months)". Both belong to the infant's facts.

Relationships: parents Blaine Jackson (6129) and Gladys Mae
Jackson (9967), both GEDCOM linkage. The ruling leaves them with
the infant; they are NOT assigned to the adult, though a 1925
birth is chronologically possible (her mother would have been
15). Untouched by this package. The pedigree-diagram photo 1340
carries no dates and distinguishes neither woman; it stays on
9968, and a final gate requires 9968 to still hold exactly that
one photo row.

## Package content

- Citations move FIRST (prevention rule): 33152 from fact 6882
  to the infant's birth fact 9335; 33153 from fact 6883 to the
  infant's death fact 9336.
- New profile "Geraldine Jackson (1925-1985)" (persons.name is
  UNIQUE and "Geraldine Jackson" is the infant's profile name;
  the years are the qualifier, per the spec), birth_info "8 Aug
  1925", death_info "22 Jul 1985 (aged 59)", evidence_level
  copied at runtime from split-created profile 12007 (the
  unproven value, 1), dataset fields copied from 9968, notes
  stating the secondary-source basis, the parents decision, and
  the queued research (split research register item 4).
- Facts 6881, 6882, 6883, 25718 move to the new profile.
- Fact 25717 flagged 'unassigned_held' in fact_quality_flags
  with the ruling cited; the fact stays on 9968 and is evidence
  for neither woman.
- Split note appended to 9968.
- Persons 3,806 -> 3,807; sources unchanged at 2,693; no
  relationship or photo changes.

## Simulation

`test_harness.py` (local only, not shipped) builds a mock from
the profile's real facts and citations as read from the live
export, with the live person_photos and fact_quality_flags
tables in place. Fresh run commits with all 12 gates green;
second run is a true no-op (still exactly one flag row); a
renamed-profile mock aborts untouched. Harness: 17/17 PASS.
