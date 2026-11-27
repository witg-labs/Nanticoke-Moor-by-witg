# Maryland Phoebe Davis package: build report, 2026-11-27

Package: apply_maryland_davis_package.py + maryland_davis_package.json
Spec: ~/workspace/family-archive/MARYLAND_DAVIS_PACKAGE_2026-11-23.md
Preflight: PREFLIGHT_2026-11-27.md (audited against origin/main @
1c4f1edb, the Mosley-Davis merge; every claim matched, with two
scope notes: the wrong Samuel Thompson parent row was already
removed by the Samuel package, and Joan Ellen Davis has no archive
profile, so no link is created for her).

## What it does (one transaction, backup first)

1. Burial fact 27650 corrected in place from the import boilerplate
   ("Interred in historical Delmarva cemetery") to the funeral
   program's interment: 1 Feb 2020, Harmony U.M. Cemetery,
   Millsboro, with the street address in the value. The single
   cemetery-survey citation (source 1274) is detached to the
   unassigned-evidence register; the program is cited instead.
2. The child_of auto-link to grandmother Martha E Thompson (8147)
   is removed (row captured in full into the register); the
   child_of link to father William Wesley Davis Sr (8609) is
   added with the program's parentage line as evidence. The
   mother link to Phoebe Thompson (8146) is kept.
3. Five new facts on 11253, each cited: Companion (Charles Henry,
   37 years), Education (Millsboro #204 School; William C. Jason
   High School), Employment (Townsend Poultry Plant, over 30
   years) to the funeral program source; Nickname "Aunt Meryl" to
   the program; Nickname "Marilyn (Merle)" to a Jequan Davis
   statement source (his 2026-11-23 identity ruling).
4. Notes append (marker-guarded): no biological children; helped
   raise Joan's children Sandra Davis, Jane Davis, Toney Floyd;
   survivors William Davis Jr., Stanley Davis, Preston Davis,
   Joan Davis. No links are created by the note.
5. The generic import Marriage fact 27653 is left in place and
   marked in fact_quality_flags (flag "generic_unverified"): it
   is not evidence of a marriage (ruling 2026-11-23).
6. The three funeral program page photographs are registered as
   photo rows (category "people", document_type "funeral_program",
   contains_face 1, face_context "embedded_photo", following the
   Samuel Thompson program rows) with photo_catalog title rows,
   linked to 11253, none primary. All four NOT NULL catalog
   columns are populated in the specs. sha256: cover
   b9d6fbf9f04114233524fc77b12eb7481527e6fa3102bed8330bedf15234587b,
   obituary page
   11737014756aa01851c780e0a676956cfb917c27bd27ac8e5cefbdbed34fa3f0,
   back page
   23a477e9fec892e343380ec7e7b38c300056d50ffb7a11533e2ecdaf0af074f9.

## Simulation proof (mock DB with live constraints)

Harness: test_harness.py (local, not shipped). The mock carries
persons.name UNIQUE and the unified_photo_catalog NOT NULL
columns, and seeds the audited current state (8 facts on 11253,
the boilerplate burial with its 1274 citation, the 8147 and 8146
child_of rows, 3,800 persons).

- Fresh run: COMMITTED, all 25 in-script gates PASS.
- Second run: COMMITTED as a true no-op (sources created 0, facts
  created 0, photo rows created 0, register entries 0).
- Tampered copy (burial place altered beforehand): aborts with
  SCHEMA SURPRISE, exit 3, database byte-identical afterwards.
- Harness assertions on the committed mock: 25/25 PASS, including
  the register holding exactly the detached 1274 citation and the
  removed 8147 relationship row.

## Expected counts on the live run

Persons 3,800 before and after; sources 2,679 -> 2,681; facts on
11253 8 -> 13; relationships touching 11253 stay 2 (one removed,
one added); citations on fact 27650 stay 1 (1274 out, program in);
photos 2,882 -> 2,885; register gains 2 entries.
