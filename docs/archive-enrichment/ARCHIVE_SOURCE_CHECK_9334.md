# Source check: archive id 9334, Lydia E Norwood

**Run:** 2026-10-27, at the user's "Run the 9334 source check first."
**Question:** What source actually sits behind 9334, what sits behind 11251, and what blocks attaching the 1855 trial fact?
**Answer in one line:** The same-person reading holds, but 9334 as currently exported is the worse canonical profile to merge into: it is redacted as living, it has no exported facts, and its spouse link is chronologically impossible. 11251's chain is coherent. Merge direction and redaction need fixing before ingestion, not after.

## 9334, Lydia E Norwood

- Dataset: `davis_family_gedcom`. Source page: `Davis Family Tree.ged`.
- Relationships in the detail file: child of Nathaniel Nathan Norwood (10542, 1745-1786) and Jemima Harmon (10374, 1750-1849); spouse of James Clark (9336) via GEDCOM Family @F47@, marriage in Sussex Co., DE; parent of Bowen Clark (9335).
- Parentage fits a birth about 1768: mother Jemima would be about 18, father Nathaniel alive until 1786.
- Detail file state: `is_living: True`, `birth_info: Private`, `death_info: ""`, `facts: []`, evidence L0 in the repo clone (L3 in the repo-git clone; the clones disagree on evidence level, which is itself a sync flag).
- The same detail file still carries parsed fields: `birth_date: "abt 1768 Sussex"`, `death_date: "26 Dec 1856 Delaware, USA"`. So the summary dates are not invented. They are in the detail file, hidden by the redaction.
- Blocker: a person with a parsed death date of 1856 is exported as living, so her facts are stripped from the detail view. If a trial fact is ingested into the database while that living flag persists, it may still not appear in the detail view. The living flag must be checked and cleared in the database before ingestion, not assumed fixed by the export.
- Spouse chain is broken: James Clark (9336) is listed with birth 22 Jan 1831 and death 1834. He cannot be the husband of a woman born about 1768, nor the father of Bowen Clark (abt 1850, sixteen years after his death). The same profile is also listed as both spouse of 9334 and child of 9334 (a GEDCOM parent-child record loop).
- James Clark (9336) is conflated with James H. Clark (10421): both carry birth 22 Jan 1831, WikiTree Clark-93419, and a 23 September 1900 marriage to Cassius Mosley. The archive already flags 10421 vs 9336 as a Duplicate Candidate (matching name and birth year). The intended husband of Lydia is presumably an older James Clark, father of Boen (b. 1805), not the 1831 James.

## 11251, Lydia Nau-Gwa-Ok-Wa Norwood Clark

- Dataset: `findagrave`. Source page: `FindAGrave Memorial 55667866`. Evidence L3.
- Birth 1780, death 1860. Notes: "Grandmother of James H. Clark; Nanticoke Lineage Ancestress."
- Its only person-specific source is that FindAGrave memorial. The other facts on the profile are generic document mentions (Moors, Obits, Warren Wright, MainMenu) and generic census templates, not evidence for the trial, for the 1840/1850 census labels, or for the coercion account.
- Chain is chronologically coherent: Lydia (1780) -> Boen Clark (11249, 1805-1880, notes: "Son of James Clark & Lydia Nau-Gwa-Ok-Wa Norwood Clark") -> James H. Clark (10421, 1831-1907). James H. Clark's own notes say: "Grandson of James Clark (#9336) & Lydia Nau-Gwa-Ok-Wa Norwood Clark (#11251)." So the archive's own James H. note ties 11251 as grandmother, not mother, of James H.
- That matches the 9334 chain in structure: Lydia -> Bowen/Boen Clark -> James H. Clark. Both Lydia profiles are grandmothers of James H. Clark through a Bowen/Boen son. That is the duplicate evidence, not a contradiction.

## Bowen / Boen Clark, the linked duplicate

- Bowen Clark (9335, GEDCOM, b. abt 1850 Sussex, census 1850) and Boen Clark (11249, FindAGrave 55667866, b. 1805, d. 1880) are both listed as parent of James H. Clark (10421) and child of James Clark (9336) and a Lydia Norwood Clark (9334 vs 11251).
- Both point to the same 1850 census record: Ancestry view 19697629:8054 (Bowen's census citation; Boen's photo "1850 Federal Census - Boen Clark Household," same Ancestry record).
- Birth years conflict by 45 years. Boen's 1805 fits the 1850 census (age 45) and James H.'s 1831 birth (father age 26). Bowen's abt 1850 does not fit either: a man born about 1850 cannot head an 1850 household or father a child born 1831. Bowen's year looks like a census-year misread.
- Mother side repeats the pattern: Ann W. Johnson (10420, 1804-1885, GEDCOM, spouse of Bowen) and Ann Clark (11250, 1810-1885, FindAGrave 55667866, mother of James H.) are likely the same mother, maiden Johnson, married Clark. Not confirmed by the user; noted only.

## Date conflicts that survive the source check

- Birth: 9334 abt 1768 vs 11251 1780 (12 years apart). Both allow an elderly witness in 1855 (about 87 vs about 75).
- Death: 9334 26 Dec 1856 vs 11251 1860 (4 years apart). The audit follows the tribal 1856 date; Speck puts Lydia Clark's death probably between 1840 and 1850. Neither archive date is a primary source for the trial. Keep both as alternate dates with sources, do not overwrite one with the other.
- No archive source for either profile mentions the 1855 trial, the 1840 "free colored" / 1850 "Mulatto" census labels, or the coercion oral tradition. Those facts come from the audit (Fisher 1895, census, Nanticoke Indian Association), not from the archive's existing sources. The trial fact is new to the archive, not a correction of an existing archive fact.

## What must happen before ingestion, in order

1. Clear the living redaction on 9334 in the database and verify her facts export. Otherwise the ingested trial fact will be invisible in the detail view.
2. Do not carry 9334's spouse link to James Clark (9336, b. 1831) into the merged profile. That link is impossible as written and belongs to the James Clark duplicate problem, not to Lydia.
3. Merge 11251 into 9334 only with alternate dates preserved (1768/1856 from GEDCOM summary vs 1780/1860 from FindAGrave 55667866), plus 11251's "Nanticoke Lineage Ancestress" note and its Boen/James H. grandmother chain.
4. Keep Bowen/Boen Clark as a separate duplicate decision. It is strongly indicated by the shared census record, but the user has not confirmed it.
5. 7577, Lydia Clark (spouse Bowen Harmon, Harmon children, birth fact 1834), remains separate, per the user's confirmation.

## Status

No repo change, no PR, no ingestion. This check is a report only, filed alongside the enrichment map.
