# John E Miller (8857) split package: build report

Built 2026-11-27 by Orbit. Authority:
`gedcom-citation/CONFLATION_RULINGS.md`, Jequan Davis ruling
2026-11-22: profile 8857 SPLIT. The profile keeps the 1856-1927
man (vital records, Find a Grave #107225416, 1875 marriage). The
GEDCOM-only Lewes life (b. Mar 1873 Delaware, d. 24 Feb 1950
Lewes) becomes its own profile, flagged unproven.

## Audit (live export, 2026-11-27, after the 8345 merge)

Profile 8857 held 13 facts in three groups:

- Kept life (1856-1927): 8348 Name, 8349 Birth 1856, 8350 Death
  4 Jun 1927, 12375 Marriage 11 Mar 1875, 24963 Burial (Find a
  Grave #107225416), 24964 Census 1860. The vital-record citations
  on the kept facts quote the kept life's own dates, so nothing on
  them moves.
- Split-off life (GEDCOM only, source 622): 9082 Name "John E.
  Miller", 9083 Birth "Mar 1873 Delaware", 9084 Death "24 Feb 1950
  Lewes". No corroborating fact of any kind (case file,
  CONFLATION_CASES.md). Research register item 2 is still QUEUED:
  no census, vital record, draft card, or burial found yet.
- Fits neither: 14635 and 14673 Document Mentions (probate estate
  sales naming a John Miller, undated), 15175 Document Mention
  (1770 tax list), 15675 Racial Classification (1850, Kent County,
  age 4, implying b. abt 1846; predates both men).

Census fact 24964 also carries citation 31469 (1920 census text).
A 1920 enumeration fits either man and no 1920 census fact exists
on either profile, so the citation is marked SUPERSEDED in place,
the 439/8345 precedent.

Relationships: the only links are the two GEDCOM-linked children,
William Alonzo Miller Sr (8858) and Hattie Miller (8860). The case
file is explicit that they do not discriminate between the men,
and the ruling does not assign them. They stay on 8857; the new
profile starts with no relationships. Both profiles' notes say so.

## Package content

- New profile "John E. Miller" (the name form his own Name fact
  9082 records; persons.name is UNIQUE and "John E Miller" is
  taken by 8857), birth_info "Mar 1873 Delaware", death_info
  "24 Feb 1950 Lewes", evidence_level copied at runtime from
  split-created profile 12007 (the unproven value, 1), notes
  stating the GEDCOM-only basis and the queued research.
- Facts 9082, 9083, 9084 move to the new profile unchanged.
- Facts 14635, 14673, 15175, 15675 detach to
  `fixes/john-e-miller-split/unassigned_evidence_register.json`
  with citations intact (script writes it only after commit).
- Citation 31469 marked SUPERSEDED.
- Split note appended to 8857.
- Persons 3,802 -> 3,803; sources unchanged at 2,693; no
  relationship changes; no photos on either profile.

## Simulation

`test_harness.py` (local only, not shipped) builds a mock from the
profile's real facts and citations as read from the live export.
Fresh run commits with all 8 gates green and writes the register
(4 facts, citations intact); second run is a true no-op; a
renamed-profile mock aborts untouched. Harness: 14/14 PASS.
