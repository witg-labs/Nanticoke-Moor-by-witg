# Enrichment proposal, Batch A: Job Harmon circle and 1855 trial defendants

**Status:** PROPOSAL ONLY for the data change, prepared 2026-10-27 after PR #6 (Lydia Clark proposal) was merged. No ingestion and no live archive change has been made. This document itself is submitted for review via a pull request; merging that PR merges the proposal document, not the database change.
**Source:** `CLAIM_AUDIT.md` (2026-10-27 verdicts), `archive_enrichment_ingestion.json` (entries for these ids), `ARCHIVE_ENRICHMENT_MAP.md`.
**Rule:** Do not hand-edit `frontend/public/api/person/*.json` or `persons_summary.json`. Those are generated exports from `preservation_output/genealogy_preservation.db`. Ingest into the database, then re-export and verify.

## Batch A, ready

### Job Harmon, id 10540 (b. 1725, Sussex County)
Archive links already match Heinegg: parents Edward Harmon (2098) and Patience Harmon (10554); children Jemima (10374), Sheppard (10544), Eunice (10545), Edward I (10546), Adonijah (998), Keisiah (10548, spelling variant of Kesiah).
Facts to add, all cited to Heinegg, Harman family, entry 9:
- Sept 1746 muster, age 21, Capt. John Shannon's Company, King George's War.
- Merchant account £12.18, including a "checked shirt" (Kent Co. dockets RG 3505.003).
- General Sessions Court RG 4815.017, 1753-60 and 1761-1771; indictment Feb 1759, continued through Aug 1762; Lockwood suit Nov 1765. Note: "1735-1771" is a composite span; 1735 is the start year of the RG 3505.003 docket volume, not a dated appearance.
- St. George's Protestant Episcopal Church, Indian River: Jemima baptized 16 April 1750; Shepherd, "Mulattoes: Shepherd son of Job and Comfort ___ b. 15 Apr 177(2)" [Wright, Vital Records of Kent and Sussex Counties, 95, 101]. Wider family "mulatto" labels come from Lewes and Coolsprings Presbyterian marriage records, not St. George's.

### Edward Harmon, id 2098 (b. abt 1700) and Patience Harmon, id 10554 (b. 1680, Delaware)
Fact to add to both, cited to Heinegg, Harman family, entry 4, as a hedge note only:
- "Edward and Patience may have been the ancestors of some of the family members who were in Maryland and Delaware." Job appears only under that "may have been" preamble (child list: "vii. Job, born say 1726"). Flat "mother Patience Harmon" is not supported by Heinegg.
This note does not by itself downgrade the archive's existing "confirmed" parent links. Downgrading certainty is a separate call.

### Jemima Harmon, id 10374 (b. 16 Apr 1750, Broadkill Hundred)
Fact to add, cited to Heinegg, Harman family, entry 9:
- Baptized at St. George's Protestant Episcopal Church, Indian River, 16 April 1750. The date already matches the archive birth date; this adds the baptism source, not a new date.

### John Puckham, id 1696 (b. abt 1660, d. aft 1683) and Joan Johnson, id 1697
Fact to add to both, cited to Heinegg, Record #82 (Stepney Parish, Somerset Co., MD):
- Married 1682/3. The archive already notes John Puckham married Joan Johnson 25 Feb 1682/3 in Somerset Co., MD, minister John Huett; the Heinegg citation is the addition, and it does not change the archive's date or minister note.
Flag, do not fix in this batch: Joan Johnson's profile also carries an 1880 birth and a Social Security application fact, which cannot belong to a 1682/3 bride. That is a pre-existing conflation, separate from the marriage fact.

### Levin Sockum, id 1924 (Levin Eunice Sockum, b. 1807, d. 25 Dec 1864)
Fact to add, cited to Fisher 1895, State v. Levin Sockum, and audit corrections register 1:
- Defendant in the 1855 Millsboro trial, charged with violating Delaware law against Black gun ownership; the all-white jury ruled the men "Negro"/"Mulatto." Lydia Clark (9334, per the merged PR #6 proposal) testified for the prosecution.
Not added in this batch: co-defendant Isaiah Harmon has no archive profile found, so his trial fact has no clean home. Do not attach it to a different Isaiah.

## Excluded from Batch A, with reasons

- Shepherd Harmon, id 10547 (b. 1906), and Keisiah Harmon, id 10548 (with 1900/1950 census facts): not Job's 18th-century children on the evidence in their profiles, despite relationship links pointing at them. Conflation review needed before any Heinegg child fact is attached to them.
- Comfort Allen, Job's wife in Heinegg: Heinegg says "probably" his wife, and "Allen" is attributed, not established. No Comfort Harmon profile was found, and no new spouse profile is created in this batch. If a spouse profile is created later, it must carry "probably" and "Allen attributed" with it.
- Eunice, Edward, Adonijah, and Kesiah as Heinegg children: Heinegg marks each with "?". The archive already links them as children of Job. This batch does not change those links; it adds the "?" hedge as a note on Job's profile, not as a link deletion.
- Any Driggers, Dawes, 1881 group, Bowen/Boen, or James Clark fact. Those are separate batches or decisions.

## Verification checklist (after ingestion and re-export, before any data PR is merged)

- `person/10540.json` shows the muster, account, court, and St. George's facts with Heinegg citations, and the "1735-1771" composite-span note.
- `person/2098.json` and `person/10554.json` show the "may have been" hedge note, with existing parent links unchanged unless a separate certainty decision is recorded.
- `person/10374.json` shows the St. George's baptism citation for 16 April 1750.
- `person/1696.json` and `person/1697.json` show the Heinegg Record #82 marriage citation, with the archive's 25 Feb 1682/3 date unchanged.
- `person/1924.json` shows the 1855 trial fact with Fisher 1895 citation.
- No generated export file is edited by hand; all changes come through the database and a fresh export.
- No fact from this batch is attached to 10547, 10548, a later namesake, or a different Isaiah.

## Out of scope

- Lydia 9334 database ingestion itself (PR #6 proposal, merged as a document; ingestion still pending and needs the database holder).
- Bowen/Boen Clark, James Clark, Ann Johnson/Clark, Driggers new profiles, Dawes persons, and the 1881 group fact.
