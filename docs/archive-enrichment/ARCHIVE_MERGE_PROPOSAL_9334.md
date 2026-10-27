# Cleaned merge proposal: Lydia Clark, archive id 9334

**Status:** PROPOSAL ONLY, prepared 2026-10-27 at the user's go-ahead to prepare it. No repo change, no PR, no ingestion, no live archive change.
**Canonical profile:** 9334, Lydia E Norwood.
**Duplicate to retire:** 11251, Lydia Nau-Gwa-Ok-Wa Norwood Clark.
**Separate, do not touch:** 7577, Lydia Clark (spouse Bowen Harmon).
**Sources for this proposal:** `ARCHIVE_SOURCE_CHECK_9334.md`, `ARCHIVE_ENRICHMENT_MAP.md`, `CLAIM_AUDIT.md` (D10), `archive_enrichment_ingestion.json` (12 entries).

## Why this merge is "cleaned," not a straight merge

A straight merge of 11251 into 9334 would carry two archive errors into the canonical profile:

1. 9334 is exported as living (`is_living: True`, birth Private, death blank, facts empty), even though the same detail file carries parsed dates of abt 1768 Sussex and 26 Dec 1856 Delaware. Ingesting facts into a living-redacted profile would hide them in the detail view.
2. 9334 is linked as spouse, and also as parent, of James Clark (9336, b. 22 Jan 1831, d. 1834). That link is chronologically impossible and belongs to the James Clark duplicate problem (9336 vs James H. Clark, 10421, both b. 22 Jan 1831, both WikiTree Clark-93419, both with a 1900 Cassius Mosley marriage). It must not survive the merge.

## Merged profile, as proposed (id 9334)

- **Names:** Lydia E Norwood (canonical name, from GEDCOM). Alternate name, preserved verbatim: Lydia Nau-Gwa-Ok-Wa Norwood Clark (from FindAGrave Memorial 55667866, via 11251).
- **Birth:** abt 1768, Sussex. Alternate birth, preserved with source, not used as primary: 1780 (FindAGrave Memorial 55667866).
- **Death:** 26 Dec 1856, Delaware, USA. Alternate death, preserved with source, not used as primary: 1860 (FindAGrave Memorial 55667866).
- **Living flag:** cleared. `is_living` must be absent or False on re-export, and the detail file must show birth and death, not Private/blank.
- **Parents (kept from 9334, GEDCOM):** Nathaniel Nathan Norwood (10542, 1745-1786) and Jemima Harmon (10374, 1750-1849). This parentage fits both birth years (mother about 18 in 1768, about 30 in 1780).
- **Spouse:** James Clark, name only, NO id link in this proposal. Do not link to James Clark (9336, b. 1831). The intended husband is the older James Clark, father of Boen Clark (b. 1805). Resolving which James Clark profile that is belongs to the James Clark duplicate decision, which is out of scope here. Do not create a new James Clark profile in this step.
- **Children (as currently linked, not merged in this step):** Bowen Clark (9335, GEDCOM, b. abt 1850) and Boen Clark (11249, FindAGrave 55667866, b. 1805). Both are listed as parent of James H. Clark (10421) and both point to the same 1850 census record (Ancestry 19697629:8054). They are a likely duplicate pair, but the user has NOT confirmed that merge. This proposal keeps both links, flagged as a duplicate pair pending a separate decision, and does not pick one birth year over the other.
- **Grandchild (through either son link):** James H. Clark (10421, 1831-1907). James H.'s own notes already call 11251 his grandmother; after the merge that note should read 9334.
- **Notes to carry over from 11251:** "Nanticoke Lineage Ancestress" and "Grandmother of James H. Clark."
- **Evidence level:** do not copy either clone's level blindly. The repo clone marks 9334 L0 and the repo-git clone marks her L3, a sync discrepancy to resolve at ingestion time. After the facts below are ingested with their citations, recalibrate from the citation count in the database, and record the resulting level in the merge report.

## Facts to add to 9334 (from the ingestion set)

1. **1855 trial (Event):** Testified for the prosecution in the 1855 Millsboro trial of Levin Sockum and Isaiah Harmon; the all-white jury ruled the men "Negro"/"Mulatto"; her Nanticoke heritage was never legally acknowledged by that trial. Citation: Fisher 1895, State v. Levin Sockum; audit corrections register 1.
2. **Oral tradition note (attached to the trial fact, labeled as such, never as documented fact):** The Nanticoke Indian Association's oral tradition holds she was coerced (elderly, infirm, dependent on the white family she lived with). "Last full-blooded Nanticoke" is prosecution-era/1935-newspaper framing; "last fluent speaker" is the Association's account only, not settled linguistic fact.
3. **Census labels:** "free colored" (1840), "Mulatto" (1850). Citation: 1840 and 1850 census, per audit corrections register 1.
4. **Death:** 26 Dec 1856, Delaware, USA (already in the summary and in the detail file's parsed fields; this step makes it visible in the detail file by clearing the living redaction, rather than adding a new date).

## Facts and links NOT to carry over

- 11251's generic document mentions (Moors, Obits, Warren Wright, MainMenu) and its generic 1790 census template fact. They are not person-specific evidence for this Lydia and must not be copied as if they were.
- 11251's 1780/1860 dates as primary dates. They stay only as alternates, with FindAGrave as source.
- 9334's spouse link and parent link to James Clark (9336). Both are deleted in this proposal, with the reason recorded (see above). The GEDCOM Family @F47@ marriage record itself is preserved as a note ("GEDCOM Family @F47@, marriage in Sussex Co., DE, spouse recorded as James Clark") without an id link, so the underlying record is not lost while the impossible link is removed.
- Any fact from 7577, Lydia Clark (Bowen Harmon family, birth fact 1834). Separate person, confirmed by the user.

## Retiring 11251

- Mark 11251 as a duplicate of 9334, not as a deleted person with no trace. Keep its id, its FindAGrave source (Memorial 55667866), and its alternate dates in the merge record.
- Re-point 11251's only relationship, parent of Boen Clark (11249), to 9334, so Boen's mother link does not dangle. Do not re-point it to Bowen Clark (9335); that is the separate Bowen/Boen decision.
- Update James H. Clark's (10421) grandmother note from "#11251" to "#9334" at the same time, or the note will point at a retired id.

## Steps, in order (for the implementer, not yet authorized)

1. In the database (not in the generated export files): clear the living flag on 9334 and confirm her birth and death fields read abt 1768 Sussex and 26 Dec 1856 Delaware, USA.
2. Apply the merged name, alternate name, alternate dates, notes, and parent links above to 9334.
3. Delete the 9334-to-9336 spouse and parent links, recording the GEDCOM @F47@ marriage as a name-only note.
4. Add the four facts above to 9334 with their citations (Fisher 1895; 1840/1850 census; audit corrections register 1).
5. Mark 11251 as a duplicate of 9334, re-point Boen Clark's mother link to 9334, and update James H. Clark's grandmother note.
6. Re-export and verify, before any PR is merged:
   - `person/9334.json` shows `is_living` absent or False, birth abt 1768, death 26 Dec 1856, and all four facts with citations.
   - `person/9334.json` shows parents 10542 and 10374, no spouse link to 9336, and no parent link to 9336.
   - `person/11249.json` shows mother 9334 (not 11251).
   - `person/10421.json` shows grandmother 9334 (not 11251) in its notes or links.
   - No other profile still references 11251 except in the merge record itself.
7. Open a PR for review with that verified diff. Merge only on his per-merge go-ahead, under his standing merge rule.

## Out of scope, explicitly not in this proposal

- Merging Bowen Clark (9335) with Boen Clark (11249).
- Resolving James Clark (9336) vs James H. Clark (10421).
- Merging Ann W. Johnson (10420) with Ann Clark (11250).
- Any Driggers, Dawes, or 1881 group fact from the enrichment map.
- Any change to 7577, Lydia Clark.
