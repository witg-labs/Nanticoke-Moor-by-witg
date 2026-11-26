# DB / Export Reconciliation Plan (2026-11-22)

## Why this exists

The archive's source of truth is the database,
`preservation_output/genealogy_preservation.db` on Jequan's Desktop PC.
The website runs on the export layer, `frontend/public/api/**` in
`witg-labs/Nanticoke-Moor-by-witg`, generated from that database.

The two layers have drifted apart. A series of reviewed fixes in
October and early November 2026 were made in the export layer and
merged to main, but the corresponding writes were never made in the PC
database. Any full re-export from the database therefore reverts those
fixes. This was measured during the 2026-11-19 source-repair run: a
full regeneration differed from origin/main in 1,638 files (797 GEDCOM
profiles title-only, since resolved by PR #18; 137 GEDCOM profiles
with unrelated regressions; 699 non-GEDCOM profiles changed).

Until the layers are reconciled, every queued apply package whose run
sheet ends in a full re-export is gated: packages 2-5 (citation
attachments, burial artifact marks, Whittington Clark split, Eli
Norwood probate card) and the seven conflation packages behind them.

This reconciliation is a layer-sync operation only. It merges no
profiles, splits no profiles, and deletes nothing. Every record keeps
its citations. Anything genuinely ambiguous is held for Jequan's
ruling, never silently overwritten in either direction.

## How the divergence happened (verified from origin, 2026-11-22)

Export-data commits on main, with how each was applied:

| Commit | Date | Change | Applied to |
|---|---|---|---|
| 2d37846 | 2026-10-16 | Five safe data hygiene fixes | export layer |
| b67bd99 | 2026-10-16 | Mini-tree person-photo linkages exported | export layer |
| d3edbeb | 2026-10-17 | 210 misassigned photo-person linkages removed per owner review | export layer |
| f945608 | 2026-10-25 | Aggregate files regenerated from fixed person sources | export layer |
| ac062e3 | 2026-11-05 | Wrights of Ontario portrait date corrected | export layer |
| e0f2102 | 2026-11-05 | Wright brothers photo date completed; Dorothy Wright Wallace identification (photo 2581) | export layer |
| 7c990d6 | 2026-11-11 | Phase 4 photo metadata, scoped regen (photos.json and downstream only) | database + scoped export |
| 6d2ec91 | 2026-11-18 | Photo 2581 enriched metadata restored | database + export |
| 04c872c | 2026-11-19 | Source 622/625 retitles (PR #18) | database + surgical export |
| 016dffc (PR #20, merged a8139ff) | 2026-11-22 | Hanzer lead-photo fix: photo 1129 off James Walter Hanzer (9722), photo 1130 set as his primary_photo | export layer only; backfill owed |

Post-plan addition, recorded so Stage 1 does not flag it as a
conflict: the 2026-11-22 Hanzer fix (PR #20) was made in the export
layer at the owner's direct instruction because the wrong photo was
live on a public profile. It is Category B by construction: the
database backfill writes (detach photo 1129 from person 9722; set
his primary photo to 1130) are owed and are listed here as part of
the seeded inventory.

Second post-plan addition (2026-11-23, PR #21, merge 803403d):
owner-contributed portrait of Howdy Thompson added in the export
layer as photo 3677, attached to person 8184 with primary_photo
set. Category B by construction: the database backfill (create
photo record 3677, attach to 8184, set primary) is owed. Image
file: frontend/public/assets/archive_media/people/Thompson_Howdy_1994.jpg.

Third post-plan addition (2026-11-23, PR #22, merge f469d11):
three owner-contributed portraits of Maryland Phoebe Davis added
in the export layer as photos 3679-3681, attached to person 11253
with the red crab shirt portrait (3679) set as primary_photo.
Category B by construction: the database backfill (create photo
records 3679-3681, attach to 11253, set primary) is owed. (Photo
3678 was assigned on branch fix/stanley-davis-photo for the
Stanley Oliver Davis Sr kitchen portrait; per the settled
2026-11-23 ruling that portrait is his and the branch is the
vehicle of the queued Stanley correction package, so the number
is used only when that package runs and the gap on main is
expected until then.)

Fourth post-plan addition (2026-11-23, PR #23, merge 7d386a4):
owner-contributed memorial card of Freeman Nelson Jackson added
in the export layer as photo 3682 (funeral_program,
embedded_photo), attached to person 10024 and set as his
primary_photo. Category B by construction: the database backfill
(create photo record 3682, attach to 10024, set primary) is owed.
Image file: frontend/public/assets/archive_media/people/Jackson_Freeman_memorial_card.jpg.
Source credit: contributed by Jequan Davis.

Fifth post-plan addition (2026-11-23, PR #25, merge 97fd1f0):
owner-contributed portrait of Phoebe Thompson Davis added in the
export layer as photo 3683, attached to person 8146 and set as
her primary_photo. Category B by construction: the database
backfill (create photo record 3683, attach to 8146, set primary)
is owed. Image file: frontend/public/assets/archive_media/people/Davis_Phoebe_Thompson_red_chair.jpg.
Source credit: contributed by Jequan Davis. (The first Phoebe
branch, fix/phoebe-davis-photo, conflicted with main after the
Freeman merge and was superseded by fix/phoebe-davis-photo-2,
branched from post-Freeman main.)

Sixth post-plan addition (2026-11-23, PR #26, merge e14bdd5):
owner-contributed funeral program cover of Dallas Robert
Johnson, Sr. added in the export layer as photo 3684 (a
funeral_program record, portrait embedded in the cover) and
attached to profile 9696, whose recorded dates (b. December 14,
1921; d. 14 Jan 2016) the program matches to the day. Profile
9696 had no photo. Category B by construction: the database
backfill (create photo record 3684, attach to 9696, set primary)
is owed. Image file: frontend/public/assets/archive_media/people/Johnson_Dallas_funeral_program.jpg.
Source credit: contributed by Jequan Davis.

Seventh post-plan addition (2026-11-23, PR #27, merge b36d4e6):
the obituary page of the same Dallas Robert Johnson, Sr. funeral
program, added in the export layer as photo 3685 (a
funeral_program document page, no face) and attached to profile
9696 alongside photo 3684. The page names his parents, wives,
and children; profile 9696 records no relationships, so those
links are package work, not part of this addition. Category B
by construction: the database backfill (create photo record
3685, attach to 9696) is owed. Image file:
frontend/public/assets/archive_media/people/Johnson_Dallas_funeral_program_obituary.jpg.
Source credit: contributed by Jequan Davis.

Eighth post-plan addition (2026-11-23, PR #28, merge 461c847):
owner-contributed funeral program cover and obituary page of
George Isaac Harmon added in the export layer as photos 3686
(cover) and 3687 (obituary page), attached to profile 9001,
whose recorded dates (b. 23 May 1948; d. 18 November 2014) the
program matches to the day. Profile 9001 had no photo. Category
B by construction: the database backfill (create photo records
3686-3687, attach to 9001, set 3686 primary) is owed. Image
files: frontend/public/assets/archive_media/people/Harmon_George_I_funeral_program.jpg
and Harmon_George_I_funeral_program_obituary.jpg. Source credit:
contributed by Jequan Davis. (Two defects on 9001 ride along
unedited for the package queue: a Burial fact dated 1851, and a
GEDCOM parent link conflicting with the program's parentage.)

Ninth post-plan addition (2026-11-23, PR #29, merge 411dbfb):
owner-contributed full funeral program cover and obituary page
of Freeman Nelson Jackson added in the export layer as photos
3688 (cover, set primary) and 3689 (obituary page), attached to
profile 10024 alongside his memorial card (3682, added the same
day as the fourth addition). Category B by construction: the
database backfill (create photo records 3688-3689, attach to
10024, set 3688 primary) is owed. Image files:
frontend/public/assets/archive_media/people/Jackson_Freeman_program_full.jpg
and Jackson_Freeman_program_obituary.jpg. Source credit:
contributed by Jequan Davis.

Tenth post-plan addition (2026-11-23, PR #30, merge 65bec07):
owner-contributed funeral program cover and obituary page of
Sylvester Elwood Thompson added in the export layer as photos
3690 (cover, set primary) and 3691 (obituary page), attached to
profile 8181. Category B by construction: the database backfill
(create photo records 3690-3691, attach to 8181, set 3690
primary) is owed. Image files:
frontend/public/assets/archive_media/people/Thompson_Sylvester_funeral_program.jpg
and Thompson_Sylvester_funeral_program_obituary.jpg. Source
credit: contributed by Jequan Davis.

Eleventh post-plan addition (2026-11-23, PR #31, merge
c604c97): owner-contributed funeral program cover, obituary
page and order of service of Samuel Thompson Jr. added in the
export layer as photos 3692 (cover, set primary), 3693
(obituary page) and 3694 (service page), attached to profile
8169. Category B by construction: the database backfill
(create photo records 3692-3694, attach to 8169, set 3692
primary) is owed. Image files:
frontend/public/assets/archive_media/people/Thompson_Samuel_Jr_funeral_program.jpg,
Thompson_Samuel_Jr_funeral_program_obituary.jpg and
Thompson_Samuel_Jr_funeral_program_service.jpg. Source credit:
contributed by Jequan Davis.

Twelfth post-plan addition (2026-11-23, PR #32, merge
bbfb3c9): owner-contributed funeral program service page of
George William Thompson, Jr. added in the export layer as
photo 3695, attached to profile 8189 and set primary (the
profile had no photo). Category B by construction: the
database backfill (create photo record 3695, attach to 8189,
set primary) is owed. Image file:
frontend/public/assets/archive_media/people/Thompson_George_William_Jr_program.jpg.
Source credit: contributed by Jequan Davis.

Thirteenth post-plan addition (2026-11-23, PR #33, merge
03c42d0): owner-contributed funeral program pages of Nelson
Freeman Jackson added in the export layer as photos 3697
(cover) and 3696 (obituary page), attached to profile 10025,
cover set primary (the profile had no photo). Category B by
construction: the database backfill (create photo records
3696-3697, attach to 10025, set primary) is owed. Image files:
frontend/public/assets/archive_media/people/Jackson_Nelson_program_full.jpg
and Jackson_Nelson_program_obituary.jpg. Source credit:
contributed by Jequan Davis.

The October and early-November fixes are the drift. Known examples the
2026-11-19 regeneration reverted: person 1003 re-adds misassigned
photo 1444 (removed in d3edbeb); person 10292 re-adds removed photos;
person 10020 drops the suffix "Sr" and 10201 drops "Jr"; person 1018
reverts document_type group_photo to portrait; persons 1033 and 1039
revert the flag_type schema; surnames.json Counselor count falls
39 to 15.

## Classification rules

Stage 1 classifies every field-level difference between a fresh
regeneration and origin/main's export into exactly one category:

- **A. Stale-checkout artifact.** Differences that exist only because a
  checkout is behind main (the 797 title-only files were this).
  Resolved by pulling current main before regenerating. Not
  divergence; not reported as findings.
- **B. Export-ahead, explained.** The regeneration loses a change that
  a seeded export-layer fix commit (table above) made on purpose.
  Main is authoritative. Stage 2 writes the change INTO the database.
  This is the bulk of the work.
- **C. Database-ahead.** The regeneration carries content main's
  export does not have, not explained by any export-layer commit
  (work done in the database and never exported). The database is
  authoritative. No database write is needed; Stage 2's full
  re-export publishes it, and Stage 1 lists every such item so the
  publication is a reviewed act, not a surprise.
- **D. True conflict.** Both sides changed the same field to different
  values, or a difference matches neither a seeded commit nor a
  plausible database-side edit. HELD for Jequan's ruling. Nothing in
  this category is overwritten in either direction by either stage.
- **E. Exporter schema drift.** Whole classes of format difference
  (the flag_type schema class is the known one) that come from the
  regeneration running different pipeline code than the one that
  produced main's files. Resolved by version parity: the regeneration
  must run the exporter from current main. If a format class persists
  after parity, its fields are reclassified under B, C, or D.
- **F. Derived aggregates.** surnames.json, graph.json,
  persons_summary.json, records_catalog.json, photos.json are
  computed from person and photo data. They are never reconciled
  file-by-file; they follow once the base data agrees, and Stage 2
  verifies them by counts.

Expected non-divergence, recorded so no run "fixes" it: the database
holds living persons the export redacts. Source 622 counts are the
reference example: 2,885 citations across 951 persons in the database
against 2,842 across 930 profiles in the export. Count gaps of this
shape are redaction, not drift.

## Staging

- **Stage 1 (this run): read-only.** Pull current main, back up the
  database, regenerate into a scratch directory outside the repo
  tree, produce a field-level classified diff per the rules above,
  and push a report only (no export files, no database writes).
  Run sheet: `~/workspace/handoff/2026-11-22-archive-reconciliation-stage1-pc-run.md`.
- **Orbit review.** Orbit verifies the Stage 1 report from origin,
  checks the classification against the seeded commit inventory, and
  brings Jequan the Category D held list for ruling.
- **Stage 2 (separate prompt, written after Stage 1 is verified):**
  apply Category B writes to the database (timestamped backup,
  dry-run first, single transaction, stop-on-surprise, the standing
  apply-package discipline), then a full re-export, then verification
  that a second regeneration diffed against the pushed export shows
  zero unexplained differences.
- Category C publishes as part of Stage 2's re-export, from the
  Stage 1 list Jequan has seen. Category D moves only on his ruling.

## What this unblocks

When Stage 2 verifies clean, the re-export gate lifts and the machine
queue runs in its established order:

1. Citation attachments, 43 corroborated facts, 69 pairs
   (branch fix/corroborated-citation-attachments @ f0156f29)
2. Burial artifact marks, 56 facts
   (branch fix/burial-artifact-marking @ 1727994d)
3. Whittington Clark split, profile 2412
   (branch fix/whittington-clark-split @ 3d54003f)
4. Eli Norwood probate card, profile 10457
   (branch fix/eli-norwood-probate-card @ 857e7147)
5. The seven conflation packages ruled 2026-11-22: splits for 439,
   8857, 8890 (three ways), 9928, 9968; corrections for 8345 and
   9561; with the orphan-handling rules and the split research
   register (SPLIT_RESEARCH_REGISTER.md) feeding them.

## Acceptance test

The reconciliation is done when a fresh full regeneration from the
database, diffed against the export on origin/main, shows zero
unexplained differences: every remaining difference is either the
living-person redaction gap in counts or an item on the Category D
held list awaiting ruling.
