# RainTech GRC — V1 Operator Runbook (draft)

Status: **draft, October 6, 2026.** It covers what is built on `main`. CMMC
close and package issuance (#107/#108) and the CMMC Windows acceptance (#109)
are not built yet. Their sections say so. This runbook does not replace
`docs/specification.md`; where the two disagree, the specification wins.

## 1. Before you start

- V1 is for **sanitized** assessment material. Never put CUI, PHI, ePHI,
  credentials, or regulated samples into the app. See
  `docs/local-evidence-operating-boundary.md`.
- Everything runs locally and offline. The app listens on loopback only.
- One operator account (Johnathan) is recorded on every governed change.

## 2. Install, launch, and data location

- Build and verify the Windows package as described in
  `packaging/windows/README.md`. Use the ARM64 package on the Surface Pro 11.
- Launch from the shortcut. The browser UI opens on loopback.
- Data lives in `%LOCALAPPDATA%\RainTech\GRC Platform`:
  - `workspace.db`: all structured data
  - `files\`: evidence, generated and issued artifacts
  - `files\backups\`: pre-issuance sets, `workspace\` sets, `pre-migration\`
    copies
- `RAINTECH_DATA_DIR` points the app elsewhere. Use it only for isolated
  testing.

## 3. Start an engagement

1. **+ Client / project.** Choose the client, the project name, and the
   **framework**: HIPAA 45 CFR Part 164 or CMMC Level 2. The framework version
   is pinned for the life of the project.
2. **Profile.** Acknowledge the local evidence boundary, complete intake, and
   move readiness to *Intake complete*. An assessment cannot start before that.
   *Profile complete* needs a named reviewer and approval evidence.
3. Create the assessment from the Assessments view.

## 4. HIPAA workflow

1. Work each record in the work list:
   - answer the guidance questions
   - record notes
   - map evidence, with a rationale per mapping
   - set the determination
   - *Met* needs mapped evidence or a documented interview/observation.
   - *N/A* needs a rationale.
   - Addressable specifications need a disposition.
2. **Security Risk Analysis.** Complete the scope and the risks. High and
   Critical risks need approval.
3. **Not Met.** Reconcile each Not Met to a finding and a corrective action.
   Validate corrective work before changing to Met.
4. **Close readiness.** Clear every blocker shown in the close panel.
5. **Generate** the report (DOCX) and the POA&M (XLSX).
6. **Review and sign off:** In Review → Reviewed → Ready to issue.
7. **Back up.** The pre-issuance backup is required, and a failure blocks
   issuance.
8. **Issue.** The issued package is immutable.
9. **Corrections:**
   - Presentation-only: correct and reissue from the same stored snapshot.
   - Substantive: reopen with the affected records named, revalidate them, then
     regenerate, review, back up, and issue again.
   - The prior issue stays current until the new one is issued.

## 5. CMMC Level 2 workflow

1. The work list shows the 110 requirements. Opening a requirement shows all of
   its assessment objectives with their status.
2. Record a determination **per objective**: Blank, Met, Not Met, or Pending.
   - The requirement status is derived and cannot be edited.
   - Met needs evidence or an interview/observation.
   - CMMC has no N/A in this version.
3. RainTech practitioner guidance appears in the dashed amber panel. It is not
   DoD or NIST text: never cite it as authority. It never sets a status.
4. **Official score.** The score panel follows 32 CFR 170.24.
   - It stays *provisional* while requirements are unscored.
   - For IA.L2-3.5.3 and SC.L2-3.13.11, record partial or no implementation,
     with a rationale.
   - If CA.L2-3.12.4 (SSP) is Not Met, the score cannot be completed.
   - Conditional-status eligibility follows 32 CFR 170.21.
5. **Findings.** A Not Met requirement automatically gets exactly one finding,
   listing its failed objectives. Add POA&M items on the requirement page.
   Pending creates follow-up work only.
6. **Not built yet:** the CMMC close gate, SSP, and package issuance
   (#107/#108). Do not represent a CMMC engagement as issued.

## 6. Evidence

- **Upload:** "Add evidence file". Every file and replacement gets an immutable
  SHA-256 version.
- **Replace:** "Replace file" adds a new version. Existing mappings stay on the
  version they were made with. Use **Use latest version** on a mapping only
  after you have checked the new file still supports it.
- **Detach:** unmapping is refused if it would leave a Met determination without
  support.
- **Recycle bin** (under *Evidence library and recycle bin*):
  - Only unmapped evidence can be binned, and it can be restored.
  - *Delete permanently* removes the file bytes only. It is refused while any
    generated or issued package cites the file.
- **Review dates** mark evidence *overdue*. They never change a determination.

## 7. Backups and recovery

- **Automatic backups:**
  - A daily backup of the database, taken after changes.
  - A weekly full backup, taken after changes.
  - The app keeps 14 daily and 2 weekly backups. Manual and pre-issuance
    backups are never pruned.
- **Back up now** (top bar) makes a full set at any time.
- **"Backup failed"** in the top bar means the last automatic backup failed.
  Check free disk space, then press *Back up now*. The warning clears on the
  next success.
- **Upgrades:** a new version copies the database to
  `files\backups\pre-migration\` before migrating. If that copy fails, the app
  does not migrate.
- **Restore** (offline, into a new empty folder only; never over live data):

  ```powershell
  .\RainTechGRCRecovery.exe .\files\backups\workspace\manual-....zip C:\RainTech-Recovery-Test
  ```

  Restore checks every hash before writing anything, and writes all or nothing.
  To test a restored copy, point `RAINTECH_DATA_DIR` at it.
- Run a restore test monthly on the Surface (AC-021). This is not yet recorded
  as done.

## 8. Troubleshooting

| Symptom | Check |
|---|---|
| Assessment cannot start | Profile readiness must be *Intake complete* or *Profile complete*. |
| "Met requires mapped evidence…" | Map evidence or document an interview/observation. |
| Close or issue blocked | Read the blocker list; it names the record or gate. |
| Pre-issuance backup failed | Free disk space; files must not change during the backup. |
| CMMC score "provisional" | See the blockers under the score: unscored requirements, a missing partial-credit level, or the SSP. |
| App will not start after an update | The pre-migration copy is in `files\backups\pre-migration\`. Restore from a workspace set if needed. |

## 9. Open items before broader V1 release

- #107/#108: CMMC SSP, close gate, and package issuance.
- #109: CMMC Windows/offline acceptance on the Surface.
- #32: native x64, adapter-disabled, and downloaded-file SmartScreen checks.
- Monthly restore testing on the target device.
- One synthetic HIPAA and one synthetic CMMC engagement, end to end, once #108
  lands.
