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
const state = { determinations: {}, ticks: {} };
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
      html += `<button class="nav-item${child}" data-id="${esc(r.id)}" aria-current="false">
        <span class="dot" data-dot="${esc(r.id)}"></span>
        <span>
          <span class="nav-cite">${esc(r.id)}</span>
          <span class="nav-title">${esc(r.title)}</span>
        </span>
      </button>`;
    });
  });
  rail.innerHTML = html;
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
}

/* ---------- prompt rendering ---------- */
function promptHtml(recordId, p, i) {
  const key = recordId + '#' + i;
  const role = p.role || 'assessment_check';
  const src = p.cfr_paragraph || (p.source + (p.source_detail ? ' — ' + p.source_detail : ''));
  if (role === 'assessment_check') {
    const on = state.ticks[key] ? ' checked' : '';
    return `<li class="prompt">
      <input type="checkbox" data-tick="${esc(key)}"${on} aria-label="Reviewed">
      <p>${esc(p.text)}<span class="src">${esc(src)}</span></p>
    </li>`;
  }
  const tag = role === 'applicability_note'
    ? '<span class="role-tag appl">Applicability</span>'
    : '<span class="role-tag ctx">Context</span>';
  const cls = role === 'applicability_note' ? 'appl' : 'ctx';
  return `<li class="prompt ${cls}">
    <span class="no-box"></span>
    <p>${tag}${esc(p.text)}<span class="src">${esc(src)}</span></p>
  </li>`;
}

function unitHtml(r) {
  const prompts = (DATA.prompts[r.id] || []);
  const derived = isDerived(r.id);
  const desig = r.designation
    ? `<span class="chip ${esc(r.designation)}">${esc(r.designation)}</span>` : '';
  let body = `<div class="unit-body"><p class="reg-text">${esc(r.text)}</p>`;
  body += prompts.length
    ? `<ul class="prompts">${prompts.map((p, i) => promptHtml(r.id, p, i)).join('')}</ul></div>`
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
  return `<section class="unit">
    <div class="unit-head">
      <span class="cite">45 CFR ${esc(r.id)}</span>${desig}
      <h3>${esc(r.title)}</h3>
    </div>${body}${note}${foot}</section>`;
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
    const gp = DATA.prompts[standard.id] || [];
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
        <ul class="prompts">${gp.map((p, i) => promptHtml(standard.id, p, i)).join('')}</ul>
      </details>`;
    }
    const ds = derivedStatus(standard.id);
    const rolled = ds
      ? ` Currently <b class="roll ${ds}">${LABEL[ds]}</b>.`
      : ' Currently <b class="roll">Blank</b>.';
    html += `<p class="why">Determinations are made on the implementation
      specifications below. This standard's status is derived from them.${rolled}</p></div>`;
    kids.forEach(k => { html += unitHtml(k); });
  } else {
    html += unitHtml(standard);
  }

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

buildRail();
refreshDots();
select(DATA.records[0].id);
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
