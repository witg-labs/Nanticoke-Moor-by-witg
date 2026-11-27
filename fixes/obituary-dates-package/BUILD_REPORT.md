# Obituary-override date-correction batch: build report

Built by Orbit, 2026-11-27. Authority: Jequan Davis's
obituary-override rule (2026-11-23: a funeral program or obituary he
supplies beats the archive's dates for the same person; superseded
values stay visible as superseded), with the first applications
logged the same day (Annabelle Thompson, Pearl Mae Thompson,
Delphine Mae Davis, Sheila K. Davis dates), the George A. Davis
service-card cross-reference ("fact cleanup rides the correction
package"), the Hersel Davis death-half item (birth half settled by
the Mosley-Davis package, PR #46), and the Lydia Clark/Norwood
forensics verdict filed 2026-11-23 (1850 census, dwelling 32, age
60: birth abt 1790; 1768 and the gravestone's implied abt 1781 kept
visible as conflicting accounts).

## Identity checks before any date moved

- Delphine Mae Davis (8182): the archive's own links make her the
  daughter of George A. Davis (8157) and Pearl Mae Thompson (8863)
  and the mother of Dwayne Davis (8250), exactly the family her
  funeral program names. She is the program's woman carrying
  another woman's dates (1918-1968, Find a Grave 131722949,
  Valhalla Gardens); the memorial citation is detached, not the
  profile split.
- Sheila Kathleen Davis (8248): the archive's links make her the
  daughter of Harry Edward Davis (8159) and Ethel Gwendolyn Clark
  (8192); her program names her parents as Harry and Ethel Davis.
  Same pattern: her dates correct to 1939-2010; the Sheila Hill
  Davis memorial (261625394) citation is detached.
- George A. Davis (8157): his Birth 1912 and Death Dec 1923
  (aged 10-11) facts pair into a child George Davis; the adult's
  censuses run 1910-1950 and his Watson service card (funeral
  11 Sep 1986, interment Harmony Cemetery 12 Sep 1986, age 77)
  settles his death. The pair detaches whole to the register; a
  new Death fact (Sep 1986) is created from the card.
- Lydia E Norwood (9334): her export is fully redacted (the
  exporter marks her living and withholds her facts), so her
  Birth fact cannot be audited from the export. The script prints
  her complete database state in the run output, discovers the
  Birth fact carrying "1768" dynamically (aborting if there is
  not exactly one, or none and no corrected one), and corrects
  it to abt 1790 with an 1850-census citation. If her redaction
  persists after the run, the printed notes will show why and a
  one-item follow-up will fix the wording.

## Contents (one transaction)

Per profile: vital facts corrected in place and cited to a new
funeral_program source for the supplied document; the citations
that supported the old values marked SUPERSEDED in place (14
citations; original text preserved); person birth_info/death_info
set to match; a marker-guarded correction note appended (the
original Find a Grave import lines stay, answered by the append).

Detached to fixes/obituary-dates-package/
unassigned_evidence_register.json (5 entries): George's 1912
Birth fact and Dec 1923 Death fact (with their citations);
Delphine's Find a Grave burial citation 30196 and her impossible
1920 Census fact (with its 2 citations); Sheila's Find a Grave
burial citation 30379.

Flagged generic_unverified in fact_quality_flags (9 facts): the
Social Security application and generic Marriage facts whose
years belong to the superseded date sets (Annabelle 24422/24423,
Pearl 24979/24980, Delphine 24362/24363, Sheila 24439/24440) and
George's generic Marriage fact 24327. Facts left in place.

New facts (2): George A. Davis Death, Sep 1986, Millsboro;
Hersel R. Davis Death, 9 Aug 2005, Green Valley Terrace,
Millsboro (the death half of his item; his duplicated infant
facts are a separate conflation item and are not touched).

Expected counts: persons 3,801 unchanged; sources 2,683 -> 2,690
(six document sources + the 1850 census source); photos
unchanged at 2,886.

## Simulation proof (2026-11-27, local harness, not shipped)

Mock carried persons.name UNIQUE, 3,801 seeded persons, 2,683
sources, and all seven profiles in their exact live fact/citation
shapes (Lydia's Birth fact seeded as "abt 1768 Sussex" per the
export's derived birth_date). Harness 35/35 PASS: fresh run
commits with all 67 in-script gates green; second run is a true
no-op (zero deltas, register byte-identical); a tampered
Annabelle death_info aborts with exit 3, rollback, and no
register written. One defect was caught and fixed during
simulation: the per-person final fact-count gate now keys off
the audited expected count when a profile is already applied,
so reruns gate correctly.
