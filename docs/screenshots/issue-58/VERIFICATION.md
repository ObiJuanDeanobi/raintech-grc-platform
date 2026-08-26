# Issue 58 Browser Verification

Date: 2026-08-26  
Branch: `feature/58-system-owned-hipaa-walkthrough`  
Data: synthetic only

## QA inventory

- The work list and previous/next traversal expose every record in the pinned
  framework catalog.
- Walkthrough position is separate from determination progress.
- Derived parent records appear as steps, show their exact catalog-owned
  no-prompt explanation, and do not expose editable determination controls.
- Determination-bearing no-prompt records show their exact catalog-owned
  explanation and retain editable determination controls.
- Prompt answers and determinations save through the existing recoverable
  autosave behavior.
- Assessment-time prompt move and move-rejection controls are absent.
- A second client/project starts with independent answers and progress; switching
  back restores the first project's data.
- First, interior, and final traversal boundaries behave correctly.
- The supported minimum desktop viewport has no horizontal overflow.

Exploratory checks also covered a rejected incomplete `Met` determination,
recovery by adding the required synthetic interview note, and switching projects
after saved work.

## Results

- The live work list displayed 194 records in catalog order.
- The first record displayed `1 of 194`; record 164.310(d)(1) displayed
  `38 of 194`; record 164.404(b) displayed `65 of 194`; and the final record
  displayed `194 of 194`.
- The final step disabled Next and retained an enabled Previous control.
- Progress updated in place from `2 of 149 resolved` to `3 of 149 resolved`
  after a successful synthetic determination save; no project reopen was
  required.
- Record 164.310(d)(1) displayed the exact persisted explanation that its
  guidance routes to children and its status is derived. It exposed no
  determination status buttons.
- Record 164.404(b) displayed the exact persisted explanation that the record
  text itself is the prompt and retained determination controls.
- A prompt answer saved in Synthetic Health Group was absent from Synthetic
  Clinic Two and returned after switching back.
- No move, reassignment, proposed-placement, or rejection action was visible.
- The final remediation pass produced no browser-console errors or uncaught
  page errors, including during project switches that cancel assessment reads.
- At 1280 by 720, document width equaled viewport width and no horizontal
  scrolling was present.

## Automated verification

- Focused Issue 58 API tests: 8 passed.
- Full API suite: 17 passed.
- `python -m unittest discover -s tests -p 'test_*.py'`: 74 run, 15 skipped.
- React suite: 18 passed.
- `pnpm typecheck`, `pnpm lint`, and `pnpm build`: passed.
- `ruff check .`, `mypy catalog api`, and `git diff --check`: passed.
- Clean and populated migration upgrade, downgrade, re-upgrade, restart,
  historical-row preservation, and project-isolation cases are covered by the
  Issue 58 API suite.

## Compatibility review

The change adds no native dependency, platform-specific path, shell behavior,
or architecture-specific code. It uses the existing Python, SQLite, FastAPI,
React, and browser seams, so the source-level behavior is compatible with the
project's ARM64 and x64 targets. Native Windows launcher/package acceptance
remains governed by Issue 32.

## Evidence

- `desktop-first-record.png`: first traversal boundary at `1 of 194`, Previous
  disabled, and Next enabled.
- `desktop-interior-record.png`: derived parent at `38 of 194` with exact
  persisted no-prompt explanation and both traversal controls enabled.
- `desktop-final-record.png`: final traversal boundary at `194 of 194`, Previous
  enabled, and Next disabled.
- `desktop-project-a-walkthrough.png`: restored project-scoped prompt answer.
- `desktop-derived-parent.png`: earlier derived-parent evidence retained for
  comparison.
- `desktop-no-prompt-record.png`: determination-bearing no-prompt record with
  exact persisted direct-assessment explanation.
- `minimum-viewport-no-prompt-record.png`: supported minimum desktop viewport
  at 1280 by 720.
