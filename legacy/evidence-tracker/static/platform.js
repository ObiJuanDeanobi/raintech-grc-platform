const state = {
  clients: [],
  selectedClientId: null,
  selectedClient: null,
  assessments: [],
  selectedAssessmentId: null,
  families: [],
  results: [],
  evidence: [],
};

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: opts.body instanceof FormData ? opts.headers || {} : { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API error");
  }
  if (res.status === 204) return null;
  return res.json();
}

function $(sel) {
  return document.querySelector(sel);
}

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmt(s) {
  return String(s || "Not specified").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function statusBadge(status) {
  const labels = {
    not_assessed: "Not assessed",
    met: "Met",
    partial: "Partial",
    not_met: "Not met",
    escalating: "Escalating",
    na: "N/A",
  };
  return `<span class="status-badge ${esc(status || "not_assessed")}">${esc(labels[status] || status || "Not assessed")}</span>`;
}

function toast(message) {
  let el = $("#platform-toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "platform-toast";
    el.style.cssText = "position:fixed;right:24px;bottom:24px;background:#1F3864;color:white;padding:10px 14px;border-radius:8px;font-weight:800;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,.2)";
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.style.opacity = "1";
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.style.opacity = "0"; }, 2200);
}

async function init() {
  bindEvents();
  state.families = await api("/api/controls/families");
  renderFamilyFilter();
  await loadClients();
}

function bindEvents() {
  $("#refresh-app").addEventListener("click", () => loadClients());
  $("#new-client").addEventListener("click", createNewClient);
  $("#save-profile").addEventListener("click", saveProfile);
  $("#create-assessment").addEventListener("click", createAssessment);
  $("#assessment-select").addEventListener("change", async ev => {
    state.selectedAssessmentId = ev.target.value;
    await loadAssessmentWorkspace();
  });
  $("#family-filter").addEventListener("change", loadControls);
  $("#status-filter").addEventListener("change", loadControls);
  $("#missing-filter").addEventListener("change", loadControls);
  $("#search-filter").addEventListener("input", debounce(loadControls, 250));
  $("#generate-documents").addEventListener("click", generateDocuments);

  document.querySelectorAll(".platform-nav").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".platform-nav").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const panel = btn.dataset.panel;
      document.querySelectorAll("[data-platform-panel]").forEach(el => {
        el.classList.toggle("hidden", el.dataset.platformPanel !== panel);
      });
      if (panel === "documents") loadDocuments();
      if (panel === "exports") loadPoam();
    });
  });
}

function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

async function loadClients() {
  state.clients = await api("/api/clients");
  renderClients();
  if (!state.selectedClientId && state.clients.length) {
    await selectClient(state.clients[0].id);
  } else if (state.selectedClientId) {
    await selectClient(state.selectedClientId);
  }
}

function renderClients() {
  const wrap = $("#client-list");
  if (!state.clients.length) {
    wrap.innerHTML = `<div class="client-meta">No clients yet.</div>`;
    return;
  }
  wrap.innerHTML = state.clients.map(client => `
    <div class="client-card ${client.id === state.selectedClientId ? "active" : ""}" data-client-id="${esc(client.id)}">
      <div class="client-name">${esc(client.name)}</div>
      <div class="client-meta">${esc(client.latest_package || "No quote yet")}</div>
      <div class="client-meta">${esc(client.assessment_count || 0)} assessment(s)</div>
    </div>
  `).join("");
  wrap.querySelectorAll(".client-card").forEach(card => {
    card.addEventListener("click", () => selectClient(card.dataset.clientId));
  });
}

async function selectClient(clientId) {
  state.selectedClientId = clientId;
  state.selectedClient = await api(`/api/clients/${clientId}`);
  renderClients();
  fillProfileForm();
  renderQuote();
  await loadAssessments();
  await loadDocuments();
}

function fillProfileForm() {
  const form = $("#profile-form");
  const client = state.selectedClient || {};
  const profile = client.profile || {};
  form.name.value = client.name || "";
  form.primary_contact_name.value = client.primary_contact_name || "";
  form.primary_contact_email.value = client.primary_contact_email || "";
  form.primary_contact_phone.value = client.primary_contact_phone || "";
  for (const field of [
    "system_name", "environment_shape", "required_cloud", "current_cloud",
    "cui_type", "cui_flow", "cui_users", "endpoint_management",
    "external_access", "mfa_status", "timeline", "external_service_providers"
  ]) {
    if (form[field]) form[field].value = profile[field] ?? "";
  }
}

function profilePayload() {
  const form = $("#profile-form");
  return {
    client: {
      name: form.name.value.trim(),
      primary_contact_name: form.primary_contact_name.value.trim(),
      primary_contact_email: form.primary_contact_email.value.trim(),
      primary_contact_phone: form.primary_contact_phone.value.trim(),
      notes: state.selectedClient?.notes || "",
    },
    profile: {
      legal_name: form.name.value.trim(),
      system_name: form.system_name.value.trim(),
      environment_shape: form.environment_shape.value,
      required_cloud: form.required_cloud.value,
      current_cloud: form.current_cloud.value,
      cui_type: form.cui_type.value,
      cui_flow: form.cui_flow.value.trim(),
      cui_location: state.selectedClient?.profile?.cui_location || "",
      cui_users: parseInt(form.cui_users.value, 10) || null,
      endpoint_management: form.endpoint_management.value,
      external_access: form.external_access.value,
      external_service_providers: form.external_service_providers.value.trim(),
      mfa_status: form.mfa_status.value,
      timeline: form.timeline.value,
      internal_owner: state.selectedClient?.profile?.internal_owner || "owner_it",
      ongoing_support: state.selectedClient?.profile?.ongoing_support || "yes",
      questionnaire_complete: true,
      create_quote: true,
    }
  };
}

async function saveProfile() {
  if (!state.selectedClientId) return;
  const payload = profilePayload();
  await api(`/api/clients/${state.selectedClientId}`, { method: "PUT", body: JSON.stringify(payload.client) });
  await api(`/api/clients/${state.selectedClientId}/profile`, { method: "PUT", body: JSON.stringify(payload.profile) });
  toast("Profile saved and quote refreshed.");
  await selectClient(state.selectedClientId);
}

async function createNewClient() {
  const name = prompt("Client name?");
  if (!name) return;
  const client = await api("/api/clients", { method: "POST", body: JSON.stringify({ name }) });
  toast("Client created.");
  await loadClients();
  await selectClient(client.id);
}

function renderQuote() {
  const quote = state.selectedClient?.latest_quote;
  const card = $("#quote-card");
  if (!quote) {
    card.className = "quote-card empty";
    card.innerHTML = "Save the implementation profile to create a quote.";
    return;
  }
  card.className = "quote-card";
  card.innerHTML = `
    <div class="quote-package">${esc(quote.package_name)}</div>
    <div class="quote-range">${esc(quote.quote_range)}</div>
    <div><strong>Readiness:</strong> ${esc(quote.readiness_score)} / 100</div>
    <div><strong>Confidence:</strong> ${esc(quote.confidence)}</div>
    ${quote.assumptions ? `<p class="client-meta">${esc(quote.assumptions).replace(/\n/g, "<br>")}</p>` : ""}
  `;
}

async function loadAssessments() {
  if (!state.selectedClientId) return;
  state.assessments = await api(`/api/assessments?client_id=${encodeURIComponent(state.selectedClientId)}`);
  const sel = $("#assessment-select");
  sel.innerHTML = state.assessments.map(a => `<option value="${esc(a.id)}">${esc(a.name)}</option>`).join("");
  state.selectedAssessmentId = state.assessments[0]?.id || null;
  if (state.selectedAssessmentId) sel.value = state.selectedAssessmentId;
  await loadAssessmentWorkspace();
}

async function createAssessment() {
  if (!state.selectedClientId) return;
  const name = prompt("Assessment name?", "CMMC Level 2 Readiness");
  if (!name) return;
  await api("/api/assessments", {
    method: "POST",
    body: JSON.stringify({ client_id: state.selectedClientId, name }),
  });
  toast("Assessment created.");
  await loadAssessments();
}

async function loadAssessmentWorkspace() {
  if (!state.selectedAssessmentId) {
    $("#score-cards").innerHTML = "";
    $("#controls-table").innerHTML = `<div class="client-meta" style="padding:14px">Create an assessment to begin evidence capture.</div>`;
    updateExportLinks();
    return;
  }
  await refreshScore();
  await loadControls();
  updateExportLinks();
  await loadPoam();
}

async function refreshScore() {
  const score = await api(`/api/assessments/${state.selectedAssessmentId}/score`);
  const counts = score.counts || {};
  $("#score-cards").innerHTML = `
    <div class="score-card"><span>Score</span><strong>${esc(score.score)}%</strong></div>
    <div class="score-card"><span>Evidence files</span><strong>${esc(score.evidence_count)}</strong></div>
    <div class="score-card"><span>Met</span><strong>${esc(counts.met || 0)}</strong></div>
    <div class="score-card"><span>Partial / gaps</span><strong>${esc((counts.partial || 0) + (counts.not_met || 0) + (counts.escalating || 0))}</strong></div>
  `;
}

function renderFamilyFilter() {
  const sel = $("#family-filter");
  sel.innerHTML = `<option value="">All families</option>` + state.families
    .map(f => `<option value="${esc(f.code)}">${esc(f.code)} - ${esc(f.name)}</option>`)
    .join("");
}

async function loadControls() {
  if (!state.selectedAssessmentId) return;
  const params = new URLSearchParams();
  if ($("#family-filter").value) params.set("family", $("#family-filter").value);
  if ($("#status-filter").value) params.set("status", $("#status-filter").value);
  if ($("#missing-filter").checked) params.set("missing", "true");
  if ($("#search-filter").value.trim()) params.set("q", $("#search-filter").value.trim());
  state.results = await api(`/api/assessments/${state.selectedAssessmentId}/results?${params.toString()}`);
  renderControls();
}

function renderControls() {
  const wrap = $("#controls-table");
  if (!state.results.length) {
    wrap.innerHTML = `<div class="client-meta" style="padding:14px">No objectives match the current filters.</div>`;
    return;
  }
  wrap.innerHTML = state.results.map(row => `
    <div class="control-row" data-result-id="${esc(row.result_id)}">
      <div>
        <div class="control-id">${esc(row.objective_id)}</div>
        <div class="client-meta">${esc(row.family)} - ${esc(row.requirement_id)}</div>
      </div>
      <div class="control-text">
        <strong>${esc(row.requirement_name)}</strong><br>
        ${esc(row.objective_text)}
      </div>
      <div>${statusBadge(row.status)}</div>
      <div><strong>${esc(row.evidence_count)}</strong> evidence</div>
    </div>
  `).join("");
  wrap.querySelectorAll(".control-row").forEach(row => {
    row.addEventListener("click", () => openResult(row.dataset.resultId));
  });
}

async function openResult(resultId) {
  const result = await api(`/api/results/${resultId}`);
  const guidance = await api(`/api/tailored-evidence/${state.selectedClientId}/${encodeURIComponent(result.objective_id)}`).catch(() => null);
  state.evidence = await api(`/api/evidence?assessment_id=${encodeURIComponent(state.selectedAssessmentId)}`);
  $("#result-detail").innerHTML = resultDetailHtml(result, guidance);
  bindResultDetail(result);
  $("#result-dialog").showModal();
}

function resultDetailHtml(result, guidance) {
  return `
    <h2>${esc(result.objective_id)} - ${esc(result.requirement_name)}</h2>
    <p class="client-meta">${esc(result.objective_text)}</p>
    <div class="detail-grid">
      <section class="detail-section">
        <h3>Status and notes</h3>
        <label>Status
          <select id="detail-status">
            ${["not_assessed","met","partial","not_met","escalating","na"].map(s => `<option value="${s}" ${result.status === s ? "selected" : ""}>${fmt(s)}</option>`).join("")}
          </select>
        </label>
        <label>Owner<input id="detail-owner" value="${esc(result.owner || "")}"></label>
        <label>Due date<input id="detail-due" type="date" value="${esc(result.due_date || "")}"></label>
        <label>Notes<textarea id="detail-notes" rows="5">${esc(result.notes || "")}</textarea></label>
        <button class="btn primary" id="save-result">Save objective</button>
      </section>
      <section class="detail-section">
        <h3>Tailored evidence guidance</h3>
        ${guidance ? `
          <ul class="guidance-list">
            ${(guidance.guidance || []).map(item => `<li>${esc(item)}</li>`).join("")}
          </ul>
          <h4>Recommended sources</h4>
          <ul>${(guidance.recommended_sources || []).map(item => `<li>${esc(item)}</li>`).join("")}</ul>
          <h4>Evidence examples</h4>
          <ul>${(guidance.evidence_examples || []).map(item => `<li>${esc(item)}</li>`).join("")}</ul>
        ` : `<p class="client-meta">No tailored guidance available.</p>`}
      </section>
    </div>
    <div class="detail-grid" style="margin-top:14px">
      <section class="detail-section">
        <h3>Mapped evidence</h3>
        <div class="evidence-list">
          ${(result.evidence || []).map(item => `
            <div class="evidence-item">
              <strong>${esc(item.title)}</strong>
              <div class="client-meta">${esc(item.original_filename)} - ${esc(item.capture_date)}</div>
              <button class="btn secondary unlink-evidence" data-evidence-id="${esc(item.id)}">Unlink</button>
            </div>
          `).join("") || `<p class="client-meta">No evidence mapped yet.</p>`}
        </div>
      </section>
      <section class="detail-section">
        <h3>Capture or reuse evidence</h3>
        <form id="evidence-upload-form">
          <label>Evidence file<input id="evidence-file" name="evidence_file" type="file" required></label>
          <label>Title<input id="evidence-title" name="title"></label>
          <label>Source<input id="evidence-source" name="source" placeholder="Client interview, Entra, Intune, policy repo"></label>
          <label>Notes<textarea id="evidence-notes" name="notes" rows="3"></textarea></label>
          <button class="btn primary" type="submit">Upload and map</button>
        </form>
        <hr>
        <label>Reuse existing evidence
          <select id="reuse-evidence">
            <option value="">Select evidence...</option>
            ${state.evidence.map(item => `<option value="${esc(item.id)}">${esc(item.title)} (${esc(item.original_filename)})</option>`).join("")}
          </select>
        </label>
        <button class="btn secondary" id="link-existing">Link selected evidence</button>
      </section>
    </div>
  `;
}

function bindResultDetail(result) {
  $("#save-result").addEventListener("click", async () => {
    await api(`/api/results/${result.result_id}`, {
      method: "PATCH",
      body: JSON.stringify({
        status: $("#detail-status").value,
        owner: $("#detail-owner").value,
        due_date: $("#detail-due").value,
        notes: $("#detail-notes").value,
      }),
    });
    toast("Objective saved.");
    await refreshAfterDetail(result.result_id);
  });
  $("#evidence-upload-form").addEventListener("submit", async ev => {
    ev.preventDefault();
    const form = new FormData();
    const file = $("#evidence-file").files[0];
    if (!file) return;
    form.append("evidence_file", file);
    form.append("title", $("#evidence-title").value);
    form.append("source", $("#evidence-source").value);
    form.append("notes", $("#evidence-notes").value);
    await api(`/api/results/${result.result_id}/evidence`, { method: "POST", body: form });
    toast("Evidence uploaded and mapped.");
    await refreshAfterDetail(result.result_id);
  });
  $("#link-existing").addEventListener("click", async () => {
    const evidenceId = $("#reuse-evidence").value;
    if (!evidenceId) return;
    await api(`/api/results/${result.result_id}/link`, {
      method: "POST",
      body: JSON.stringify({ evidence_id: evidenceId }),
    });
    toast("Evidence linked.");
    await refreshAfterDetail(result.result_id);
  });
  document.querySelectorAll(".unlink-evidence").forEach(btn => {
    btn.addEventListener("click", async () => {
      await api(`/api/results/${result.result_id}/evidence/${btn.dataset.evidenceId}`, { method: "DELETE" });
      toast("Evidence unlinked.");
      await refreshAfterDetail(result.result_id);
    });
  });
}

async function refreshAfterDetail(resultId) {
  await refreshScore();
  await loadControls();
  await openResult(resultId);
}

async function generateDocuments() {
  if (!state.selectedClientId) return;
  await api(`/api/clients/${state.selectedClientId}/documents/generate?assessment_id=${encodeURIComponent(state.selectedAssessmentId || "")}`, {
    method: "POST",
  });
  toast("Document drafts generated.");
  await loadDocuments();
}

async function loadDocuments() {
  const wrap = $("#documents-list");
  if (!state.selectedClientId) {
    wrap.innerHTML = `<p class="client-meta">Select a client.</p>`;
    return;
  }
  const params = state.selectedAssessmentId ? `?assessment_id=${encodeURIComponent(state.selectedAssessmentId)}` : "";
  const docs = await api(`/api/clients/${state.selectedClientId}/documents${params}`);
  if (!docs.length) {
    wrap.innerHTML = `<p class="client-meta">No generated documents yet.</p>`;
    return;
  }
  wrap.innerHTML = docs.map(doc => `
    <div class="doc-card">
      <input class="doc-title" data-doc-id="${esc(doc.id)}" value="${esc(doc.title)}">
      <div class="client-meta">${esc(fmt(doc.doc_type))} - ${esc(doc.filename || "")}</div>
      <textarea class="doc-body" data-doc-id="${esc(doc.id)}">${esc(doc.body || "")}</textarea>
      <button class="btn primary save-doc" data-doc-id="${esc(doc.id)}">Save draft</button>
    </div>
  `).join("");
  wrap.querySelectorAll(".save-doc").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.docId;
      await api(`/api/documents/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: document.querySelector(`.doc-title[data-doc-id="${id}"]`).value,
          body: document.querySelector(`.doc-body[data-doc-id="${id}"]`).value,
        }),
      });
      toast("Document draft saved.");
    });
  });
}

function updateExportLinks() {
  const disabled = !state.selectedClientId || !state.selectedAssessmentId;
  const evidence = $("#evidence-report");
  const poam = $("#poam-report");
  const pkg = $("#package-export");
  if (disabled) {
    evidence.removeAttribute("href");
    poam.removeAttribute("href");
    pkg.removeAttribute("href");
    return;
  }
  evidence.href = `/api/assessments/${state.selectedAssessmentId}/reports/evidence.xlsx`;
  poam.href = `/api/assessments/${state.selectedAssessmentId}/reports/poam.xlsx`;
  pkg.href = `/api/clients/${state.selectedClientId}/exports/package.zip?assessment_id=${encodeURIComponent(state.selectedAssessmentId)}`;
}

async function loadPoam() {
  const wrap = $("#poam-list");
  if (!state.selectedAssessmentId) {
    wrap.innerHTML = `<p class="client-meta">No assessment selected.</p>`;
    return;
  }
  const rows = await api(`/api/assessments/${state.selectedAssessmentId}/poam`);
  if (!rows.length) {
    wrap.innerHTML = `<p class="client-meta">No POA&M items yet. Mark objectives partial, not met, or escalating to create items.</p>`;
    return;
  }
  wrap.innerHTML = rows.map(row => `
    <div class="poam-item">
      <strong>${esc(row.objective_id)} - ${esc(row.title)}</strong>
      <div class="client-meta">${esc(row.status)} - ${esc(row.priority)} - Owner: ${esc(row.owner || "Unassigned")}</div>
      <p>${esc(row.remediation)}</p>
    </div>
  `).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  init().catch(err => {
    console.error(err);
    toast(err.message);
  });
});
