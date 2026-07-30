"""Render the pinned HIPAA catalog and its prompt layer as a clickable walkthrough.

This is a **review instrument, not application code**. It exists to answer one
question before Slice 4's assessment surface is designed: does walking a HIPAA
standard question-by-question feel like running a CMMC gap analysis?

It is deliberately disposable. Nothing here is promoted into the production
application; the production surface is reimplemented against the real
architecture. What survives this page is the practitioner's marks on it.

It reads the same two pinned files the Markdown export reads, so what it shows
is what the catalog and the prompt layer actually contain -- no separate
fixture to drift.

Usage:
    python catalog/render_walkthrough.py --out <path.html>

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG = REPO_ROOT / "catalog" / "versions" / "hipaa-45cfr164-2026-07-01.json"
LAYER = REPO_ROOT / "catalog" / "versions" / "hipaa-45cfr164-2026-07-01-prompts.json"

STYLE = """
:root {
  color-scheme: light dark;
  --ground: #FBFCFD;
  --surface: #FFFFFF;
  --surface-sunk: #F2F5F7;
  --line: #DFE5EA;
  --line-strong: #C4CED6;
  --ink: #131A21;
  --ink-muted: #5A6672;
  --ink-faint: #7C8894;
  --accent: #0E5C63;
  --accent-soft: #E3EFF0;
  --met: #2E7D5B;
  --notmet: #B3402F;
  --pending: #A8730F;
  --na: #6B7684;
  --shadow: 0 1px 2px rgba(19, 26, 33, .06), 0 4px 12px rgba(19, 26, 33, .04);
  --serif: ui-serif, Georgia, "Iowan Old Style", "Times New Roman", serif;
  --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --ground: #0F1419;
    --surface: #171C22;
    --surface-sunk: #12171C;
    --line: #262E36;
    --line-strong: #38424C;
    --ink: #E4E9EE;
    --ink-muted: #93A0AC;
    --ink-faint: #75828E;
    --accent: #5FB6C0;
    --accent-soft: #13333A;
    --met: #5FBE90;
    --notmet: #E0806F;
    --pending: #D9A441;
    --na: #8C97A3;
    --shadow: 0 1px 2px rgba(0, 0, 0, .4), 0 4px 14px rgba(0, 0, 0, .3);
  }
}
:root[data-theme="dark"] {
  --ground: #0F1419;
  --surface: #171C22;
  --surface-sunk: #12171C;
  --line: #262E36;
  --line-strong: #38424C;
  --ink: #E4E9EE;
  --ink-muted: #93A0AC;
  --ink-faint: #75828E;
  --accent: #5FB6C0;
  --accent-soft: #13333A;
  --met: #5FBE90;
  --notmet: #E0806F;
  --pending: #D9A441;
  --na: #8C97A3;
  --shadow: 0 1px 2px rgba(0, 0, 0, .4), 0 4px 14px rgba(0, 0, 0, .3);
}
:root[data-theme="light"] {
  --ground: #FBFCFD;
  --surface: #FFFFFF;
  --surface-sunk: #F2F5F7;
  --line: #DFE5EA;
  --line-strong: #C4CED6;
  --ink: #131A21;
  --ink-muted: #5A6672;
  --ink-faint: #7C8894;
  --accent: #0E5C63;
  --accent-soft: #E3EFF0;
  --met: #2E7D5B;
  --notmet: #B3402F;
  --pending: #A8730F;
  --na: #6B7684;
  --shadow: 0 1px 2px rgba(19, 26, 33, .06), 0 4px 12px rgba(19, 26, 33, .04);
}

* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--accent); }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 3px; }

/* ---- masthead ---- */
.masthead {
  position: sticky; top: 0; z-index: 20;
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 20px;
  padding: 14px 22px;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
}
.masthead h1 {
  margin: 0; font-family: var(--serif); font-weight: 600;
  font-size: 19px; letter-spacing: -.01em; text-wrap: balance;
}
.masthead .version {
  font-family: var(--mono); font-size: 11.5px; color: var(--ink-faint);
}
.tally { margin-left: auto; display: flex; gap: 14px; flex-wrap: wrap; }
.tally div { display: flex; align-items: baseline; gap: 5px; }
.tally b {
  font-variant-numeric: tabular-nums; font-size: 15px; font-weight: 600;
}
.tally span {
  font-size: 10.5px; text-transform: uppercase; letter-spacing: .07em;
  color: var(--ink-faint);
}

/* ---- shell ---- */
.shell { display: grid; grid-template-columns: 330px minmax(0, 1fr); align-items: start; }
@media (max-width: 900px) { .shell { grid-template-columns: minmax(0, 1fr); } }

.rail {
  position: sticky; top: 57px; max-height: calc(100vh - 57px); overflow-y: auto;
  border-right: 1px solid var(--line); background: var(--surface-sunk);
  padding: 4px 0 40px;
}
@media (max-width: 900px) {
  .rail { position: static; max-height: 420px; border-right: 0; border-bottom: 1px solid var(--line); }
}
.area-head {
  padding: 16px 18px 6px;
  font-size: 10.5px; text-transform: uppercase; letter-spacing: .09em;
  color: var(--ink-faint); font-weight: 600;
}
.sec-head {
  padding: 9px 18px 3px;
  font-family: var(--mono); font-size: 11.5px; color: var(--ink-muted);
}
.nav-item {
  display: grid; grid-template-columns: 7px minmax(0, 1fr); gap: 9px; align-items: start;
  width: 100%; text-align: left; cursor: pointer;
  padding: 6px 16px 6px 22px; border: 0; background: none; color: inherit;
  font: inherit; line-height: 1.35;
  border-left: 2px solid transparent;
}
.nav-item:hover { background: var(--surface); }
.nav-item[aria-current="true"] {
  background: var(--surface); border-left-color: var(--accent);
}
.nav-item.child { padding-left: 38px; }
/* A rollup header is not a stop on the walkthrough. It reads as a heading so
   the eye skips it, because five separate rounds of confusion traced back to
   it looking like something to work. */
.nav-item.rollup .nav-title {
  font-size: 11px; text-transform: uppercase; letter-spacing: .06em;
  color: var(--ink-faint); font-weight: 700;
}
.nav-item.rollup .nav-cite { font-size: 10px; }
.rail.worklist .nav-item.rollup { display: none; }
.rail-tools {
  position: sticky; top: 0; z-index: 2; display: flex; align-items: center;
  gap: 8px; padding: 9px 16px 9px 22px; background: var(--surface-sunk);
  border-bottom: 1px solid var(--line);
}
.rail-tools label {
  display: flex; align-items: center; gap: 6px; cursor: pointer;
  font-size: 11.5px; color: var(--ink-muted);
}
.rail-tools input { accent-color: var(--accent); cursor: pointer; }
.walk-nav {
  display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
  margin-top: 22px; padding-top: 16px; border-top: 1px solid var(--line);
}
.walk-nav button {
  font: inherit; font-size: 13px; cursor: pointer; padding: 6px 16px;
  border-radius: 3px; border: 1px solid var(--accent);
  background: var(--accent); color: #fff; font-weight: 600;
}
.walk-nav button.ghost { background: none; color: var(--accent); }
.walk-nav button:disabled { opacity: .4; cursor: default; }
.walk-nav .pos {
  font-size: 12px; color: var(--ink-faint); font-variant-numeric: tabular-nums;
}
.nav-cite {
  display: block; font-family: var(--mono); font-size: 11px; color: var(--ink-faint);
}
.nav-title { display: block; font-size: 13px; }
.dot { width: 7px; height: 7px; border-radius: 50%; margin-top: 6px; background: var(--line-strong); }
.dot.met { background: var(--met); }
.dot.notmet { background: var(--notmet); }
.dot.pending { background: var(--pending); }
.dot.na { background: var(--na); }
.dot.derived { background: transparent; border: 1.5px solid var(--line-strong); }

/* ---- working area ---- */
.work { padding: 26px 30px 100px; max-width: 900px; }
@media (max-width: 640px) { .work { padding: 20px 16px 80px; } }

.crumb {
  font-family: var(--mono); font-size: 11.5px; color: var(--ink-faint);
  margin-bottom: 14px;
}

.guidance {
  background: var(--surface); border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: 4px; padding: 16px 18px; margin-bottom: 26px;
  box-shadow: var(--shadow);
}
.guidance .label {
  font-size: 10.5px; text-transform: uppercase; letter-spacing: .08em;
  color: var(--accent); font-weight: 700; margin-bottom: 8px;
}
.guidance .why {
  font-size: 12.5px; color: var(--ink-muted); margin: 8px 0 0;
}
.fold { margin-top: 10px; border-top: 1px solid var(--line); padding-top: 8px; }
.fold > summary {
  cursor: pointer; list-style: none; display: inline-flex; align-items: center; gap: 6px;
  font-size: 11px; text-transform: uppercase; letter-spacing: .07em;
  font-weight: 700; color: var(--accent); padding: 3px 0;
}
.fold > summary::-webkit-details-marker { display: none; }
.fold > summary::before {
  content: "▸"; font-size: 10px; transition: transform .12s ease;
}
.fold[open] > summary::before { transform: rotate(90deg); }
.fold > summary:hover { text-decoration: underline; }
.roll { font-weight: 700; }
.roll.met { color: var(--met); }
.roll.notmet { color: var(--notmet); }
.roll.pending { color: var(--pending); }
.roll.na { color: var(--na); }
.guidance h2 {
  font-family: var(--serif); font-size: 17px; margin: 0 0 3px; font-weight: 600;
}
.guidance .reg {
  font-size: 14px; color: var(--ink-muted); margin: 6px 0 12px;
}

.unit {
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 5px; margin-bottom: 20px; box-shadow: var(--shadow);
  overflow: hidden;
}
.unit-head {
  display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: baseline;
  padding: 15px 18px 12px; border-bottom: 1px solid var(--line);
}
.unit-head .cite {
  font-family: var(--mono); font-size: 12px; color: var(--accent); font-weight: 600;
}
.unit-head h3 {
  margin: 0; font-family: var(--serif); font-size: 17px; font-weight: 600;
  flex: 1 1 100%; text-wrap: balance;
}
.chip {
  font-size: 10px; text-transform: uppercase; letter-spacing: .07em;
  padding: 2px 7px; border-radius: 3px; font-weight: 700;
  border: 1px solid var(--line-strong); color: var(--ink-muted);
}
.chip.required { border-color: var(--accent); color: var(--accent); }
.chip.addressable { border-color: var(--pending); color: var(--pending); }
.unit-body { padding: 14px 18px 4px; }
.reg-text { margin: 0 0 14px; }

.prompts { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.prompt {
  display: grid; grid-template-columns: 20px minmax(0, 1fr); gap: 10px;
  padding: 7px 4px; border-radius: 4px; align-items: start;
}
.prompt:hover { background: var(--surface-sunk); }
.prompt input { margin: 3px 0 0; width: 15px; height: 15px; accent-color: var(--accent); cursor: pointer; }
.prompt .no-box { }
.prompt p { margin: 0; }
.prompt.ctx p, .prompt.appl p { color: var(--ink-muted); }
.prompt .src {
  display: block; font-family: var(--mono); font-size: 10.5px;
  color: var(--ink-faint); margin-top: 3px;
}
.answer-add {
  font: inherit; font-size: 11px; cursor: pointer; margin-top: 4px;
  padding: 1px 7px; border-radius: 3px; color: var(--ink-faint);
  background: none; border: 1px dashed var(--line-strong);
}
.prompt:hover .answer-add { color: var(--accent); border-color: var(--accent); }
.prompt-tools { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 4px; }
.move-btn {
  font: inherit; font-size: 11px; cursor: pointer; padding: 1px 7px;
  border-radius: 3px; color: var(--ink-faint);
  background: none; border: 1px dashed var(--line-strong);
}
.prompt:hover .move-btn { color: var(--accent); border-color: var(--accent); }
.moved-from {
  display: inline-block; margin-left: 7px; font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .06em; vertical-align: 1px;
  padding: 1px 6px; border-radius: 2px;
  background: var(--accent-soft); color: var(--accent);
}
.move-panel {
  margin-top: 6px; padding: 9px 10px; border-radius: 4px;
  border: 1px solid var(--accent); background: var(--surface);
  display: flex; flex-direction: column; gap: 6px;
}
.move-panel .row { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.move-panel select, .move-panel input {
  font: inherit; font-size: 12.5px; padding: 4px 8px; border-radius: 3px;
  border: 1px solid var(--line-strong); background: var(--surface); color: var(--ink);
}
.move-panel select { max-width: 100%; }
.move-panel input { flex: 1 1 200px; min-width: 0; }
.move-panel .go {
  border-color: var(--accent); background: var(--accent); color: #fff;
  font-weight: 600; cursor: pointer; padding: 4px 12px; border-radius: 3px;
  font: inherit; font-size: 12.5px; border: 1px solid var(--accent);
}
.move-panel .undo {
  background: none; border: 0; color: var(--ink-faint); cursor: pointer;
  font: inherit; font-size: 11.5px; text-decoration: underline; padding: 0;
}
.move-panel .hint2 { font-size: 11.5px; color: var(--ink-muted); }
.export-btn {
  font: inherit; font-size: 12px; cursor: pointer; padding: 3px 11px;
  border-radius: 3px; border: 1px solid var(--accent);
  background: var(--accent); color: #fff; font-weight: 600;
}
textarea.answer {
  display: block; width: 100%; margin-top: 5px; font: inherit; font-size: 13px;
  padding: 6px 9px; border-radius: 3px; resize: vertical; color: var(--ink);
  border: 1px solid var(--line-strong);
  border-left: 2px solid var(--accent); background: var(--surface);
}
.role-tag {
  display: inline-block; font-size: 9.5px; text-transform: uppercase;
  letter-spacing: .07em; font-weight: 700; padding: 1px 5px; border-radius: 2px;
  vertical-align: 1px; margin-right: 6px;
}
.role-tag.appl { background: var(--accent-soft); color: var(--accent); }
.role-tag.ctx { background: var(--surface-sunk); color: var(--ink-faint); border: 1px solid var(--line); }

.determination {
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
  padding: 12px 18px; border-top: 1px solid var(--line); background: var(--surface-sunk);
}
.determination .lbl {
  font-size: 10.5px; text-transform: uppercase; letter-spacing: .08em;
  color: var(--ink-faint); font-weight: 700; margin-right: 4px;
}
.determination button {
  font: inherit; font-size: 13px; cursor: pointer;
  padding: 4px 12px; border-radius: 3px;
  border: 1px solid var(--line-strong); background: var(--surface); color: var(--ink-muted);
}
.determination button:hover { border-color: var(--ink-faint); color: var(--ink); }
.determination button[aria-pressed="true"] { color: #fff; font-weight: 600; }
.determination button.met[aria-pressed="true"] { background: var(--met); border-color: var(--met); }
.determination button.notmet[aria-pressed="true"] { background: var(--notmet); border-color: var(--notmet); }
.determination button.pending[aria-pressed="true"] { background: var(--pending); border-color: var(--pending); }
.determination button.na[aria-pressed="true"] { background: var(--na); border-color: var(--na); }
.derived {
  padding: 12px 18px; border-top: 1px solid var(--line); background: var(--surface-sunk);
  font-size: 13px; color: var(--ink-muted);
}
.derived b { color: var(--ink); font-weight: 600; }

/* ---- the working record: notes, rationale, evidence ---- */
.record-work {
  padding: 0 18px 14px; background: var(--surface-sunk);
  display: flex; flex-direction: column; gap: 12px;
}
.guidance .record-work {
  padding: 12px 0 0; margin-top: 10px; background: none;
  border-top: 1px solid var(--line);
}
.field { display: flex; flex-direction: column; gap: 5px; }
.field > label {
  font-size: 10.5px; text-transform: uppercase; letter-spacing: .08em;
  color: var(--ink-faint); font-weight: 700;
}
.field textarea {
  font: inherit; font-size: 13px; resize: vertical; min-height: 52px;
  padding: 8px 10px; border-radius: 3px; color: var(--ink);
  border: 1px solid var(--line-strong); background: var(--surface);
}
.field textarea::placeholder { color: var(--ink-faint); }
.required-flag { color: var(--notmet); font-weight: 700; }
.disposition { display: flex; flex-wrap: wrap; gap: 6px; }
.disposition button {
  font: inherit; font-size: 12.5px; cursor: pointer; padding: 4px 10px;
  border-radius: 3px; border: 1px solid var(--line-strong);
  background: var(--surface); color: var(--ink-muted);
}
.disposition button:hover { border-color: var(--ink-faint); color: var(--ink); }
.disposition button[aria-pressed="true"] {
  background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600;
}
.evidence { display: flex; flex-direction: column; gap: 6px; }
.ev-row {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
  padding: 7px 10px; border-radius: 3px;
  border: 1px solid var(--line); background: var(--surface);
}
.ev-row .name { font-size: 13px; font-weight: 600; }
.ev-row .shared {
  font-size: 11px; color: var(--accent); background: var(--accent-soft);
  padding: 1px 6px; border-radius: 2px;
}
.ev-row .why { flex: 1 1 100%; font-size: 12px; color: var(--ink-muted); }
.ev-row button {
  margin-left: auto; font: inherit; font-size: 11.5px; cursor: pointer;
  background: none; border: 0; color: var(--ink-faint); text-decoration: underline;
  padding: 0;
}
.ev-add {
  display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
}
.ev-add select, .ev-add input {
  font: inherit; font-size: 12.5px; padding: 5px 8px; border-radius: 3px;
  border: 1px solid var(--line-strong); background: var(--surface); color: var(--ink);
}
.ev-add input { flex: 1 1 220px; min-width: 0; }
.ev-add button {
  font: inherit; font-size: 12.5px; cursor: pointer; padding: 5px 12px;
  border-radius: 3px; border: 1px solid var(--accent);
  background: var(--accent); color: #fff; font-weight: 600;
}
.gate {
  font-size: 12px; padding: 7px 10px; border-radius: 3px;
  background: var(--surface); border: 1px solid var(--notmet); color: var(--notmet);
}

.empty-note {
  padding: 12px 18px; border-top: 1px solid var(--line);
  font-size: 12.5px; color: var(--ink-faint); font-style: italic;
}
.hint {
  margin: 0 0 22px; font-size: 13px; color: var(--ink-muted);
  border-bottom: 1px solid var(--line); padding-bottom: 16px;
}
.hint b { color: var(--ink); }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
"""

SCRIPT = r"""
const $ = (s, r) => (r || document).querySelector(s);
// evidence: the project's artifact library, one entry per real document.
// mappings: recordId -> [{artifact, rationale}]. AC-007 -- one artifact
// supports many records, and each mapping keeps its own rationale, so the
// same policy can be relevant to two determinations for different reasons.
const state = {
  determinations: {}, ticks: {}, notes: {}, naRationale: {},
  disposition: {}, dispositionNote: {}, evidence: [], mappings: {},
  answers: {}, moves: {},
};
try {
  const saved = localStorage.getItem('hipaa-walkthrough');
  if (saved) Object.assign(state, JSON.parse(saved));
} catch (e) { /* private mode: run without persistence */ }
function save() {
  try { localStorage.setItem('hipaa-walkthrough', JSON.stringify(state)); } catch (e) {}
}

const byId = {};
DATA.records.forEach(r => { byId[r.id] = r; });
const childrenOf = {};
DATA.records.forEach(r => {
  if (r.parent_id) (childrenOf[r.parent_id] = childrenOf[r.parent_id] || []).push(r.id);
});
// A record with implementation specifications beneath it has no editable
// determination; its status is derived from its children.
const isDerived = id => (childrenOf[id] || []).some(
  c => byId[c].record_type === 'implementation_specification'
);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

// The approved rollup rule, docs/specification.md: all children Met, or Met
// with a documented N/A where the framework allows it, derives Met; any child
// Not Met derives Not Met; otherwise any child Pending derives Pending;
// otherwise the parent remains Blank. Not Met takes precedence over Pending.
// A child with nothing recorded is Blank, which cannot derive Met.
function derivedStatus(id) {
  const kids = (childrenOf[id] || []).filter(
    c => byId[c].record_type === 'implementation_specification'
  );
  if (!kids.length) return null;
  const vals = kids.map(c => state.determinations[c] || null);
  if (vals.every(v => v === null)) return null;
  if (vals.includes('notmet')) return 'notmet';
  if (vals.includes('pending')) return 'pending';
  if (vals.every(v => v === 'met' || v === 'na')) return 'met';
  return null;
}
const statusOf = id => isDerived(id) ? derivedStatus(id) : (state.determinations[id] || null);

const LABEL = { met: 'Met', notmet: 'Not Met', pending: 'Pending', na: 'N/A' };

/* ---------- navigation rail ---------- */
function buildRail() {
  const rail = $('#rail');
  let html = '';
  DATA.areas.forEach(area => {
    html += `<div class="area-head">${esc(area.label)}</div>`;
    let section = null;
    DATA.records.filter(r => r.work_area === area.id).forEach(r => {
      if (r.section !== section) {
        section = r.section;
        html += `<div class="sec-head">45 CFR ${esc(section)}</div>`;
      }
      const child = r.parent_id ? ' child' : '';
      const roll = isDerived(r.id) ? ' rollup' : '';
      html += `<button class="nav-item${child}${roll}" data-id="${esc(r.id)}" aria-current="false">
        <span class="dot" data-dot="${esc(r.id)}"></span>
        <span>
          <span class="nav-cite">${esc(r.id)}</span>
          <span class="nav-title">${esc(r.title)}</span>
        </span>
      </button>`;
    });
  });
  const determinable = DATA.records.filter(r => !isDerived(r.id)).length;
  rail.innerHTML = `<div class="rail-tools"><label>
      <input type="checkbox" id="worklist"> Only what I determine (${determinable})
    </label></div>` + html;
  rail.addEventListener('change', e => {
    if (e.target.id === 'worklist') rail.classList.toggle('worklist', e.target.checked);
  });
  rail.addEventListener('click', e => {
    const btn = e.target.closest('.nav-item');
    if (btn) select(btn.dataset.id);
  });
}

function refreshDots() {
  document.querySelectorAll('[data-dot]').forEach(el => {
    const id = el.getAttribute('data-dot');
    const s = statusOf(id);
    el.className = 'dot' + (s ? ' ' + s : (isDerived(id) ? ' derived' : ''));
  });
  const total = DATA.records.filter(r => !isDerived(r.id)).length;
  const done = DATA.records.filter(r => !isDerived(r.id) && state.determinations[r.id]).length;
  $('#tally-done').textContent = done;
  $('#tally-total').textContent = total;
  const moves = $('#tally-moves');
  if (moves) moves.textContent = moveCount();
}

/* ---------- prompt rendering ---------- */
// ---- moves -------------------------------------------------------------
// A question sits where 800-66r2's tagging put it, and that tagging is not
// consistent. The practitioner's test is the reliable one: if you want to mark
// a question Met, name the rule it would be Met against. Name it and the
// question belongs on that rule's record; fail to and it is context. This lets
// that judgement be applied in place, and exports it so it can be baked into
// the pipeline as recorded exceptions.
const PROMPT_INDEX = {};   // key -> {prompt, home}
Object.entries(DATA.prompts).forEach(([rid, list]) => {
  list.forEach((prompt, i) => { PROMPT_INDEX[rid + '#' + i] = { prompt, home: rid }; });
});
const MOVE_CONTEXT = '__context';

function destinationOf(key) {
  const m = state.moves[key];
  return m ? m.to : PROMPT_INDEX[key].home;
}

// Prompts to render on a record: those that started here and have not left,
// plus those moved in from elsewhere.
function promptsFor(recordId) {
  const out = [];
  Object.entries(PROMPT_INDEX).forEach(([key, { prompt, home }]) => {
    const dest = destinationOf(key);
    if (dest === recordId) out.push({ key, prompt, movedFrom: home === recordId ? null : home });
  });
  return out;
}

function moveCount() { return Object.keys(state.moves).length; }

// A prompt carries no status and no evidence of its own -- the determination
// and its evidence belong to the record. What it does need is somewhere to put
// the answer: eighteen questions sharing one notes box loses which question
// produced which fact. The answer field is collapsed until it holds something,
// so a long question list stays readable.
function answerHtml(key) {
  const answer = state.answers[key] || '';
  if (!answer) {
    return `<button class="answer-add" data-answer-open="${esc(key)}">+ answer</button>`;
  }
  return `<textarea class="answer" data-answer="${esc(key)}" rows="2"
    aria-label="Answer to this question">${esc(answer)}</textarea>`;
}

function promptHtml(recordId, entry) {
  const { key, prompt: p, movedFrom } = entry;
  const moved = state.moves[key];
  const role = (moved && moved.to === MOVE_CONTEXT) ? 'context' : (p.role || 'assessment_check');
  const src = p.cfr_paragraph || (p.source + (p.source_detail ? ' — ' + p.source_detail : ''));
  const from = movedFrom
    ? `<span class="moved-from">moved from ${esc(movedFrom)}</span>` : '';
  const mover = `<button class="move-btn" data-move="${esc(key)}">move…</button>`;
  if (role === 'assessment_check') {
    const on = state.ticks[key] ? ' checked' : '';
    return `<li class="prompt">
      <input type="checkbox" data-tick="${esc(key)}"${on} aria-label="Asked">
      <p>${esc(p.text)}${from}<span class="src">${esc(src)}</span>
        <span class="prompt-tools">${answerHtml(key)}${mover}</span></p>
    </li>`;
  }
  const tag = role === 'applicability_note'
    ? '<span class="role-tag appl">Applicability</span>'
    : '<span class="role-tag ctx">Context</span>';
  const cls = role === 'applicability_note' ? 'appl' : 'ctx';
  return `<li class="prompt ${cls}">
    <span class="no-box"></span>
    <p>${tag}${esc(p.text)}${from}<span class="src">${esc(src)}</span>
      <span class="prompt-tools">${mover}</span></p>
  </li>`;
}

function unitHtml(r) {
  const prompts = promptsFor(r.id);
  const derived = isDerived(r.id);
  const desig = r.designation
    ? `<span class="chip ${esc(r.designation)}">${esc(r.designation)}</span>` : '';
  let body = `<div class="unit-body"><p class="reg-text">${esc(r.text)}</p>`;
  body += prompts.length
    ? `<ul class="prompts">${prompts.map(e => promptHtml(r.id, e)).join('')}</ul></div>`
    : `</div>`;
  let foot;
  if (derived) {
    const s = derivedStatus(r.id);
    foot = `<div class="derived">Status is <b>derived</b> from the implementation
      specifications beneath this standard${s ? ` — currently <b>${LABEL[s]}</b>` : ''}.
      No determination is recorded here.</div>`;
  } else {
    foot = `<div class="determination"><span class="lbl">Determination</span>` +
      ['met', 'notmet', 'pending', 'na'].map(v =>
        `<button class="${v}" data-det="${esc(r.id)}" data-val="${v}"
          aria-pressed="${state.determinations[r.id] === v}">${LABEL[v]}</button>`
      ).join('') + `</div>`;
  }
  const note = (!prompts.length && !derived)
    ? `<div class="empty-note">${esc(DATA.noPrompts[r.id] || 'No prompts.')}</div>` : '';
  const work = derived ? '' : workingRecord(r);
  return `<section class="unit">
    <div class="unit-head">
      <span class="cite">45 CFR ${esc(r.id)}</span>${desig}
      <h3>${esc(r.title)}</h3>
    </div>${body}${note}${foot}${work}</section>`;
}

/* ---------- the working record ---------- */
const DISPOSITIONS = {
  standard: 'Standard measure',
  alternative: 'Equivalent alternative',
  none: 'Not implemented',
};

// `rollup` renders the working record for a parent standard: the scoping
// conversation and the artifacts that support the standard as a whole, but no
// determination controls. 45 CFR 164.306(c) makes the standard itself
// mandatory, so the work done at that level is real and has to be recorded --
// losing the ePHI-scoping discussion because it belonged to no single child
// was a genuine gap. What the parent still does not get is an editable status:
// 164.306(d)(2) satisfies a standard through its implementation
// specifications, and an independently settable parent status would allow a
// standard to read Met while one of its specifications reads Not Met.
function workingRecord(r, options) {
  const rollup = options && options.rollup;
  const id = r.id;
  const det = state.determinations[id];
  let html = '<div class="record-work">';

  // Addressable specifications must record which route was taken. This has no
  // CMMC equivalent: "addressable" is not optional, and a non-implementation
  // has to carry its documented reasoning.
  if (!rollup && r.designation === 'addressable') {
    const d = state.disposition[id];
    html += `<div class="field">
      <label>Addressable disposition${d ? '' : ' <span class="required-flag">required</span>'}</label>
      <div class="disposition">${Object.entries(DISPOSITIONS).map(([k, v]) =>
        `<button data-disp="${esc(id)}" data-val="${k}"
          aria-pressed="${d === k}">${esc(v)}</button>`).join('')}</div>`;
    if (d === 'alternative' || d === 'none') {
      const lbl = d === 'alternative'
        ? 'What equivalent alternative is in place, and why is it reasonable and appropriate?'
        : 'Why is the standard measure not reasonable and appropriate here?';
      html += `<textarea data-dispnote="${esc(id)}" placeholder="${esc(lbl)}"
        aria-label="${esc(lbl)}">${esc(state.dispositionNote[id] || '')}</textarea>`;
    }
    html += '</div>';
  }

  if (!rollup && det === 'na') {
    html += `<div class="field">
      <label>N/A rationale <span class="required-flag">required</span></label>
      <textarea data-na="${esc(id)}" aria-label="N/A rationale"
        placeholder="Why does this requirement not apply to this client?">${esc(state.naRationale[id] || '')}</textarea>
    </div>`;
  }

  const noteLabel = rollup ? 'Standard-level notes' : 'Implementation notes';
  const notePlaceholder = rollup
    ? 'Scope and context for the whole standard: where ePHI lives, which systems and owners are in scope, what the client described.'
    : 'What the client described, what was observed, what was demonstrated.';
  html += `<div class="field">
    <label>${noteLabel}</label>
    <textarea data-note="${esc(id)}" aria-label="${noteLabel}"
      placeholder="${esc(notePlaceholder)}">${esc(state.notes[id] || '')}</textarea>
  </div>`;

  // Evidence is mapped from the project library, not uploaded per record.
  const maps = state.mappings[id] || [];
  const evLabel = rollup
    ? `Evidence supporting the standard (${maps.length})`
    : `Evidence mapped (${maps.length})`;
  html += `<div class="field"><label>${evLabel}</label><div class="evidence">`;
  maps.forEach((m, i) => {
    const uses = Object.values(state.mappings)
      .filter(list => list.some(x => x.artifact === m.artifact)).length;
    html += `<div class="ev-row">
      <span class="name">${esc(m.artifact)}</span>
      ${uses > 1 ? `<span class="shared">mapped to ${uses} records</span>` : ''}
      <button data-unmap="${esc(id)}" data-i="${i}">Remove mapping</button>
      <span class="why">${esc(m.rationale || 'No rationale recorded for this mapping.')}</span>
    </div>`;
  });
  const opts = state.evidence.map(e =>
    `<option value="${esc(e)}">${esc(e)}</option>`).join('');
  html += `<div class="ev-add">
      <select data-evpick="${esc(id)}" aria-label="Choose an artifact">
        <option value="">Add artifact…</option>${opts}
        <option value="__new">＋ New artifact…</option>
      </select>
      <input data-evwhy="${esc(id)}" placeholder="Why this artifact supports this record"
        aria-label="Mapping rationale">
      <button data-evadd="${esc(id)}">Map</button>
    </div>`;
  // The gate applies to Met alone, and the specification allows either route:
  // mapped evidence *or* a documented interview/observation record. Not Met
  // and Pending carry no evidence requirement -- Pending is precisely the
  // state for insufficient evidence while follow-up is requested.
  const observed = (state.notes[id] || '').trim().length > 0;
  if (det === 'met' && !maps.length && !observed) {
    html += `<div class="gate">A final Met determination requires mapped evidence
      or a documented interview/observation record. Map an artifact above, or
      record what was observed or demonstrated in the notes.</div>`;
  }
  html += '</div></div>';
  return html + '</div>';
}

// The walk is over the records that carry a determination. A rollup header is
// passed through on the way, not stopped at.
const WALK = DATA.records.filter(r => !isDerived(r.id)).map(r => r.id);

function walkNavHtml(id) {
  // Selecting a rollup header shows its children, so the walk position is the
  // first child being worked rather than the header itself.
  let i = WALK.indexOf(id);
  if (i < 0) {
    const firstChild = (childrenOf[id] || []).find(c => WALK.includes(c));
    i = firstChild ? WALK.indexOf(firstChild) : -1;
  }
  if (i < 0) return '';
  const prev = i > 0 ? WALK[i - 1] : null;
  const next = i < WALK.length - 1 ? WALK[i + 1] : null;
  return `<div class="walk-nav">
    <button class="ghost" data-go="${esc(prev || '')}" ${prev ? '' : 'disabled'}>← Previous</button>
    <button data-go="${esc(next || '')}" ${next ? '' : 'disabled'}>Next requirement →</button>
    <span class="pos">${i + 1} of ${WALK.length}</span>
  </div>`;
}

/* ---------- selecting a record ---------- */
function select(id) {
  const r = byId[id];
  // Working a child means working it in the context of its standard, so the
  // standard's own guidance stays on screen above it.
  const parent = r.parent_id ? byId[r.parent_id] : null;
  const standard = parent || r;
  const kids = (childrenOf[standard.id] || []).map(c => byId[c])
    .filter(c => c.record_type === 'implementation_specification');

  let html = `<div class="crumb">${esc(DATA.areaLabel[r.work_area])} &nbsp;›&nbsp;
    45 CFR ${esc(r.section)} &nbsp;›&nbsp; ${esc(r.id)}</div>`;

  if (kids.length) {
    const gp = promptsFor(standard.id);
    html += `<div class="guidance">
      <div class="label">Standard context</div>
      <h2>45 CFR ${esc(standard.id)} — ${esc(standard.title)}</h2>
      <p class="reg">${esc(standard.text)}</p>`;
    // The standard's own text and derived status stay in view; its question
    // list folds away. Rendering all of them open pushed the determination the
    // assessor came to work below the fold -- 20 questions deep on
    // 164.308(a)(1). Context should be at hand, not in the way.
    if (gp.length) {
      const open = (standard.id === id) ? ' open' : '';
      html += `<details class="fold"${open}>
        <summary>${gp.length} standard-level question${gp.length === 1 ? '' : 's'}</summary>
        <ul class="prompts">${gp.map(e => promptHtml(standard.id, e)).join('')}</ul>
      </details>`;
    }
    const ds = derivedStatus(standard.id);
    const rolled = ds
      ? ` Currently <b class="roll ${ds}">${LABEL[ds]}</b>.`
      : ' Currently <b class="roll">Blank</b>.';
    html += `<p class="why">45 CFR 164.306(c) makes this standard mandatory, and
      164.306(d)(2) satisfies it through the implementation specifications below,
      so its status is derived rather than set here.${rolled}</p>`;
    html += workingRecord(standard, { rollup: true });
    html += `</div>`;
    kids.forEach(k => { html += unitHtml(k); });
  } else {
    html += unitHtml(standard);
  }

  html += walkNavHtml(r.id);
  $('#work').innerHTML = html;
  document.querySelectorAll('.nav-item').forEach(b =>
    b.setAttribute('aria-current', String(b.dataset.id === id)));
  window.scrollTo({ top: 0, behavior: 'instant' });
}

/* ---------- events ---------- */
document.addEventListener('click', e => {
  const det = e.target.closest('[data-det]');
  if (det) {
    const id = det.dataset.det;
    state.determinations[id] = state.determinations[id] === det.dataset.val
      ? undefined : det.dataset.val;
    if (!state.determinations[id]) delete state.determinations[id];
    save();
    document.querySelectorAll(`[data-det="${CSS.escape(id)}"]`).forEach(b =>
      b.setAttribute('aria-pressed', String(state.determinations[id] === b.dataset.val)));
    // A child's determination can change its standard's derived status.
    const cur = document.querySelector('.nav-item[aria-current="true"]');
    if (cur) select(cur.dataset.id);
    refreshDots();
  }
});
document.addEventListener('change', e => {
  const t = e.target.closest('[data-tick]');
  if (t) {
    if (t.checked) state.ticks[t.dataset.tick] = 1;
    else delete state.ticks[t.dataset.tick];
    save();
  }
});

// Text fields save as typed and must not re-render underneath the cursor.
document.addEventListener('input', e => {
  const el = e.target;
  const bind = [['data-note', 'notes'], ['data-na', 'naRationale'],
                ['data-dispnote', 'dispositionNote'], ['data-answer', 'answers']];
  for (const [attr, key] of bind) {
    const id = el.getAttribute && el.getAttribute(attr);
    if (id) {
      if (el.value.trim()) state[key][id] = el.value;
      else delete state[key][id];
      save();
      return;
    }
  }
});

// Build the destination list for a prompt: the children of its standard first,
// then every other record, because a question can belong to a different
// standard entirely -- "Is there a formal contingency plan?" under Security
// management process belongs to 164.308(a)(7).
function movePanelHtml(key) {
  const { prompt, home } = PROMPT_INDEX[key];
  const homeRec = byId[home];
  const standardId = homeRec.parent_id || home;
  const siblings = [standardId].concat(childrenOf[standardId] || []);
  const current = destinationOf(key);
  const opt = (id, label) =>
    `<option value="${esc(id)}"${current === id ? ' selected' : ''}>${esc(label)}</option>`;
  let html = '<div class="move-panel"><div class="row"><select data-movepick="' + esc(key) + '">';
  html += '<optgroup label="This standard">';
  siblings.forEach(id => {
    const r = byId[id];
    html += opt(id, `${id} — ${r.title}${id === standardId ? ' (standard)' : ''}`);
  });
  html += '</optgroup><optgroup label="Not a requirement">';
  html += opt(MOVE_CONTEXT, 'Context only — no rule to be Met against');
  html += '</optgroup><optgroup label="Another standard">';
  DATA.records.forEach(r => {
    if (siblings.includes(r.id)) return;
    html += opt(r.id, `${r.id} — ${r.title}`);
  });
  html += '</optgroup></select>';
  html += `<input data-movewhy="${esc(key)}" placeholder="Which rule would this be Met against?"
    value="${esc((state.moves[key] || {}).reason || '')}">`;
  html += `<button class="go" data-movego="${esc(key)}">Move</button></div>`;
  html += `<div class="row"><span class="hint2">Currently on ${esc(current === MOVE_CONTEXT ? 'context' : current)}.</span>`;
  if (state.moves[key]) {
    html += `<button class="undo" data-moveundo="${esc(key)}">Undo this move</button>`;
  }
  html += '</div></div>';
  return html;
}

document.addEventListener('click', e => {
  const nav = e.target.closest('[data-go]');
  if (nav && nav.dataset.go) { select(nav.dataset.go); return; }
  const mv = e.target.closest('[data-move]');
  if (mv) {
    const key = mv.dataset.move;
    const existing = mv.parentElement.querySelector('.move-panel');
    if (existing) { existing.remove(); return; }
    mv.insertAdjacentHTML('afterend', movePanelHtml(key));
    return;
  }
  const go = e.target.closest('[data-movego]');
  if (go) {
    const key = go.dataset.movego;
    const to = document.querySelector(`[data-movepick="${CSS.escape(key)}"]`).value;
    const reason = (document.querySelector(`[data-movewhy="${CSS.escape(key)}"]`).value || '').trim();
    if (to === PROMPT_INDEX[key].home) delete state.moves[key];
    else state.moves[key] = { to, reason };
    save(); reselect();
    return;
  }
  const undo = e.target.closest('[data-moveundo]');
  if (undo) { delete state.moves[undo.dataset.moveundo]; save(); reselect(); return; }
  if (e.target.closest('#export')) { exportDecisions(); return; }
  const open = e.target.closest('[data-answer-open]');
  if (open) {
    const key = open.dataset.answerOpen;
    // Placeholder value so the field renders; cleared again if left empty.
    const box = document.createElement('textarea');
    box.className = 'answer'; box.rows = 2;
    box.setAttribute('data-answer', key);
    box.setAttribute('aria-label', 'Answer to this question');
    open.replaceWith(box);
    box.focus();
    return;
  }
  const disp = e.target.closest('[data-disp]');
  if (disp) {
    const id = disp.dataset.disp;
    state.disposition[id] = state.disposition[id] === disp.dataset.val
      ? undefined : disp.dataset.val;
    if (!state.disposition[id]) delete state.disposition[id];
    save();
    reselect();
    return;
  }
  const unmap = e.target.closest('[data-unmap]');
  if (unmap) {
    const id = unmap.dataset.unmap;
    (state.mappings[id] || []).splice(Number(unmap.dataset.i), 1);
    if (!state.mappings[id].length) delete state.mappings[id];
    save();
    reselect();
    return;
  }
  const add = e.target.closest('[data-evadd]');
  if (add) {
    const id = add.dataset.evadd;
    const pick = document.querySelector(`[data-evpick="${CSS.escape(id)}"]`);
    const why = document.querySelector(`[data-evwhy="${CSS.escape(id)}"]`);
    let artifact = pick.value;
    if (artifact === '__new') {
      artifact = (prompt('Name of the artifact, as the client would recognise it:') || '').trim();
      if (!artifact) return;
    }
    if (!artifact) return;
    if (!state.evidence.includes(artifact)) state.evidence.push(artifact);
    (state.mappings[id] = state.mappings[id] || []).push({
      artifact, rationale: (why.value || '').trim(),
    });
    save();
    reselect();
  }
});

// The practitioner's marks have to reach the pipeline, so they leave as data
// rather than as a screenshot.
function exportDecisions() {
  const rows = Object.entries(state.moves).map(([key, m]) => {
    const { prompt, home } = PROMPT_INDEX[key];
    return {
      from_record: home,
      to: m.to === MOVE_CONTEXT ? 'context' : m.to,
      key_activity: prompt.group || null,
      question: prompt.text,
      reason: m.reason || '',
    };
  });
  const payload = JSON.stringify(
    { framework_version: DATA.version, moves: rows,
      answers: state.answers, determinations: state.determinations }, null, 2);
  const blob = new Blob([payload], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'walkthrough-decisions.json';
  a.click();
  URL.revokeObjectURL(a.href);
}

function reselect() {
  const cur = document.querySelector('.nav-item[aria-current="true"]');
  if (cur) select(cur.dataset.id);
  refreshDots();
}

buildRail();
refreshDots();
select(WALK[0]);
"""


def build(catalog: dict, layer: dict) -> str:
    records = catalog["records"]
    prompts = {
        record_id: entry["prompts"]
        for record_id, entry in layer["entries"].items()
    }
    no_prompts = {
        item["record_id"]: item["reason"].capitalize() + "."
        for item in layer["records_without_prompts"]
    }
    areas = [
        {"id": area["id"], "label": area["label"]}
        for area in catalog["catalog_areas"]
    ]
    data = {
        "records": [
            {
                key: record[key]
                for key in (
                    "id", "title", "text", "record_type", "designation",
                    "work_area", "section", "parent_id",
                )
            }
            for record in records
        ],
        "prompts": prompts,
        "noPrompts": no_prompts,
        "areas": areas,
        "areaLabel": {area["id"]: area["label"] for area in areas},
        "version": catalog["framework_version"]["id"],
    }

    counts = layer["counts"]
    version = catalog["framework_version"]["id"]
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    return f"""<title>HIPAA assessment walkthrough — review build</title>
<style>{STYLE}</style>
<header class="masthead">
  <h1>HIPAA assessment walkthrough</h1>
  <span class="version">{version}</span>
  <div class="tally">
    <div><b id="tally-done">0</b><span>recorded</span></div>
    <div><b id="tally-total">0</b><span>determinations</span></div>
    <div><b>{counts['prompts_total']}</b><span>prompts</span></div>
    <div><b>{len(records)}</b><span>records</span></div>
    <div><b id="tally-moves">0</b><span>moves</span></div>
    <div><button class="export-btn" id="export">Export decisions</button></div>
  </div>
</header>
<div class="shell">
  <nav class="rail" id="rail" aria-label="Catalog records"></nav>
  <main class="work" id="work"></main>
</div>
<script>const DATA = {payload};{SCRIPT}</script>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    layer = json.loads(LAYER.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build(catalog, layer), encoding="utf-8")
    print(
        f"Wrote {args.out}: {len(catalog['records'])} records, "
        f"{layer['counts']['prompts_total']} prompts"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
