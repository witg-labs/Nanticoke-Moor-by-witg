# William Jackson (439) split package: build report

Built by Orbit, 2026-11-27. Authority: Jequan Davis's conflation
ruling of 2026-11-22 (CONFLATION_RULINGS.md: "Profile keeps
b. 1931, d. 10 Dec 1971, son of Samuel and Agnes Jackson. The
GEDCOM-only death (15 Jul 2003, Millsboro) comes off the
profile. All pre-1931 same-name material (1746-1989) is
detached.") plus the split research register item 1
(2026-11-22, status PROFILE HOLDS), which established the 2003
cluster as a real, coherent man: William Edward Jackson Sr,
"Billy", b. Oct 1930 near Millsboro (7 Oct 1930 per SSDI-derived
listings, 9 Oct 1930 per the Mitsawokett pages; discrepancy
unresolved, carried at month precision), d. 15 Jul 2003
Millsboro, buried 19 Jul 2003 Harmony Cemetery, son of Samuel
Benton Jackson Sr and Agnes Beatrice Wright, husband of Allece
Dorene Clark, father of William E. Jackson Jr., Kevin W.
Jackson, and Horace K. Jackson Sr. The register's parked
parentage flag is not touched by this package: 439 keeps its
ruling parentage, and the new profile takes the parentage the
research supports, exactly as the register directs.

## Audit basis (live export, 2026-11-27)

Profile 439 held 36 facts: 6 belonging to the 1931-1971 man
(Name 718, Birth 719, Death 720, 1940 Census 16088, Burial
16712, SS-5 16713); 3 forming the 2003 cluster (10129, 10130,
10131, all GEDCOM-sourced); and 27 pre-1931 same-name items
(2 duplicate 1893 marriage facts, 19 Document Mentions spanning
the 1746 baptism, 1765 and 1768 records, 1830 census, tax
lists, the Caroline Coker and Levin Jackson mentions of a
1915-1989 man, and 6 Racial Classification facts implying men
born about 1848 and about 1821). Relationships: child_of Samuel
Jackson 10725, child_of Agnes Beatrice Wright 9964 (GEDCOM
linkage), child_of Agnes Jackson 11663 (census linkage),
spouse_of Ruth Both 11882 (the 1893 marriage). The 1940 census
fact's own text names the household: Samuel (30), Agnes (26),
William E Jackson (9), Bettis (7), Robert (5), Benson (4),
Bendel (2), matching the sibling profiles on 10725 and 9964.
Samuel 10725 and Agnes 9964 check out as the research's
parents. No profiles exist for Allece Dorene Clark or the three
sons, so they are named in the new profile's Marriage fact and
notes without links (Joan package precedent). The ruling packet
found every photo on 439 is another subject (Morgan portraits);
the export shows one attached photo (1865), the packet's DB
audit saw three, so the script detaches whatever person_photos
rows exist at runtime and registers each with its catalog data.

## Contents (one transaction)

- New profile "William Edward Jackson Sr" (evidence_level
  copied from split-created profile 12007 at runtime), with
  the 3 moved facts, the Birth fact corrected to Oct 1930 /
  Millsboro, Sussex County, Delaware, new Burial, Marriage,
  and Nickname facts, 8 new citations, and child_of links to
  10725 and 9964 (the 9964 link carries the original row's
  GEDCOM evidence text, moved from 439).
- Four new sources: SSDI listing (dataset copied from source
  1281), the Watson obituary of Betty Bernice (Jackson) Hall
  (dataset funeral_home_obituary), the Mitsawokett
  family-history pages (dataset copied from source 682), and
  the statement of Jequan Davis (dataset copied from 2702).
- 439: 27 facts, the Ruth Both spouse row, and all photo rows
  detached to unassigned_evidence_register.json (written only
  after the commit succeeds); 6 citations marked SUPERSEDED in
  place; split note appended. Final state: 6 facts, parents
  Samuel + Agnes Jackson, no photos.
- Counts: persons 3,801 -> 3,802; sources 2,689 -> 2,693.

## Simulation proof (2026-11-27, local harness, not shipped)

Mock built from the live export itself (all 36 facts with their
real citations and evidence texts, the 4 relationship rows, 3
photo rows), 3,801 persons, 2,689 sources, NOT NULL catalog
constraints in place. Harness 22/22 PASS, 17 in-script gates:
fresh run commits with the exact audited end state (register:
27 facts, 1 detached relationship, 1 moved relationship, 3
photos); second run is a true no-op leaving the register
byte-identical; a renamed-439 mock aborts with exit 3 and
creates nothing.

## Spotted follow-up (not in this package)

Profile 11663 "Agnes Jackson" is itself a conflation: born
18 Feb 1772, linked as spouse to both Edward Harmon (2098) and
Samuel Jackson (10725), and as mother to children of both
centuries. 439's census-evidenced mother link points at it and
stays as ruled; 11663's own untangling is a separate candidate
for the conflation queue, next to profile 3588.
