const state = { packets: [], selected: null, detail: null, decision: null, mode: "fixture", liveProof: null };

const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;").replaceAll("'", "&#039;");

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Request failed: ${response.status}`);
  return payload;
}

function toast(message, error = false) {
  const element = $("toast");
  element.textContent = message;
  element.className = `toast visible${error ? " error" : ""}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { element.className = "toast"; }, 3200);
}

function renderPackets() {
  $("packet-list").innerHTML = state.packets.map((packet) => `
    <button class="packet ${state.mode === "fixture" && packet.packet_id === state.selected ? "active" : ""}" data-packet="${escapeHtml(packet.packet_id)}">
      <strong>${escapeHtml(packet.title)}</strong>
      <span>${escapeHtml(packet.scenario)}</span>
    </button>`).join("");
  document.querySelectorAll("[data-packet]").forEach((button) => {
    button.addEventListener("click", () => selectPacket(button.dataset.packet));
  });
}

async function selectPacket(packetId) {
  state.mode = "fixture";
  state.selected = packetId;
  state.decision = null;
  state.detail = await api(`/api/packets/${encodeURIComponent(packetId)}`);
  renderPackets();
  $("packet-id").textContent = state.detail.packet_id;
  $("packet-title").textContent = state.detail.title;
  $("packet-scenario").textContent = state.detail.scenario;
  $("mode-badge").className = "mode";
  $("mode-badge").querySelector("b").textContent = "Sample packet";
  $("live-proof-button").classList.remove("active");
  $("source-banner").hidden = true;
  $("evaluate-button").disabled = false;
  $("evaluate-button").textContent = "Check this packet";
  $("reviewer").disabled = false;
  $("reason").disabled = false;
  $("signature-button").disabled = true;
  $("signature-result").hidden = true;
  renderEvidence();
  resetDecision();
  await renderAudit();
}

function loadLiveProof() {
  const proof = state.liveProof;
  if (!proof?.available) return;
  state.mode = "live";
  state.selected = proof.packet_id;
  state.detail = {
    packet_id: proof.packet_id,
    title: "Northstar closeout packet",
    scenario: "Synthetic documents · verified Nutrient API extraction · saved result",
    documents: proof.documents,
  };
  state.decision = proof.decision;
  renderPackets();
  $("live-proof-button").classList.add("active");
  $("mode-badge").className = "mode live";
  $("mode-badge").querySelector("b").textContent = "Verified Nutrient run";
  $("source-banner").hidden = false;
  $("proof-recorded-at").textContent = new Date(proof.recorded_at).toLocaleString();
  $("packet-id").textContent = proof.packet_id;
  $("packet-title").textContent = state.detail.title;
  $("packet-scenario").textContent = state.detail.scenario;
  $("evaluate-button").textContent = "Verified API result";
  $("evaluate-button").disabled = true;
  $("reviewer").disabled = true;
  $("reason").disabled = true;
  $("signature-button").disabled = true;
  $("signature-result").hidden = false;
  $("signature-result").innerHTML = "<strong>Saved result — view only.</strong><br>Nothing on this screen can call the API, email anyone, move money, or request a signature.";
  renderEvidence();
  renderDecision();
  renderAudit();
}

function resetDecision() {
  const card = $("status-card");
  card.className = "status-card waiting";
  $("status-pill").textContent = "Waiting";
  $("status-title").textContent = "Nothing checked yet";
  $("status-copy").textContent = "This packet has not been approved or sent.";
  $("documents-count").textContent = state.detail?.documents.length ?? "—";
  $("fields-count").textContent = "—";
  $("findings-count").textContent = "—";
  $("policy-version").textContent = "";
  $("findings").className = "findings empty-state";
  $("findings").textContent = "Run the check to see any problems and the document values behind them.";
}

function renderEvidence() {
  const rows = state.detail.documents.flatMap((document) => Object.entries(document.fields).map(([name, field]) => `
    <tr>
      <td>${escapeHtml(document.filename)}</td>
      <td>${escapeHtml(name.replaceAll("_", " "))}</td>
      <td>${escapeHtml(field.value)}${field.human_confirmed ? '<span class="confirmed">✓ confirmed</span>' : ""}</td>
      <td><span class="confidence ${field.confidence < .85 ? "low" : ""}">${Math.round(field.confidence * 100)}%</span></td>
      <td>${escapeHtml(field.page)}</td>
      <td>${state.mode === "live"
        ? `<span class="source-badge live">Nutrient</span><code class="request-id">${escapeHtml(document.request_id)}</code>`
        : '<span class="source-badge">Fixture</span>'}</td>
    </tr>`));
  $("evidence-body").innerHTML = rows.join("");
}

async function evaluate() {
  try {
    $("evaluate-button").disabled = true;
    state.decision = await api(`/api/packets/${encodeURIComponent(state.selected)}/evaluate`, { method: "POST", body: "{}" });
    renderDecision();
    await renderAudit();
  } catch (error) {
    toast(error.message, true);
  } finally {
    $("evaluate-button").disabled = false;
  }
}

function renderDecision() {
  const decision = state.decision;
  const copy = {
    blocked: ["Payment blocked", "Fix these problems in the original documents before continuing."],
    review_required: ["Needs a person", "The documents agree, but one or more values need to be checked."],
    ready_for_approval: ["Checks passed", "A named person must still approve before anything can be sent."],
  }[decision.status];
  $("status-card").className = `status-card ${decision.status}`;
  $("status-pill").textContent = decision.status.replaceAll("_", " ");
  $("status-title").textContent = copy[0];
  $("status-copy").textContent = copy[1];
  $("documents-count").textContent = decision.checked_documents;
  $("fields-count").textContent = decision.checked_fields;
  $("findings-count").textContent = decision.findings.length;
  $("policy-version").textContent = decision.policy_version;
  $("signature-button").disabled = state.mode === "live" || decision.status !== "ready_for_approval";
  renderFindings();
}

function renderFindings() {
  const container = $("findings");
  if (!state.decision.findings.length) {
    container.className = "findings empty-state";
    container.innerHTML = "✓ No document conflicts or low-confidence values found.";
    return;
  }
  container.className = "findings";
  container.innerHTML = state.decision.findings.map((finding) => {
    const evidence = finding.evidence.map((item) =>
      `<span class="evidence-chip">${escapeHtml(item.filename)} · ${escapeHtml(item.field)} · p${escapeHtml(item.page)}</span>`
    ).join("");
    const review = state.mode === "fixture" && finding.severity === "review" && finding.evidence.length
      ? `<button class="review-button" data-review-doc="${escapeHtml(finding.evidence[0].document_id)}" data-review-field="${escapeHtml(finding.evidence[0].field)}">I checked this value</button>`
      : "";
    return `<article class="finding ${escapeHtml(finding.severity)}">
      <div class="finding-top">
        <span class="finding-icon">${finding.severity === "blocker" ? "!" : "?"}</span>
        <div><h3>${escapeHtml(finding.title)}</h3><p>${escapeHtml(finding.message)}</p>
          <p class="remediation"><strong>Next:</strong> ${escapeHtml(finding.remediation)}</p>
          <div class="evidence-chips">${evidence}</div>${review}
        </div>
      </div>
    </article>`;
  }).join("");
  document.querySelectorAll("[data-review-doc]").forEach((button) => {
    button.addEventListener("click", () => confirmField(button.dataset.reviewDoc, button.dataset.reviewField));
  });
}

async function confirmField(documentId, field) {
  try {
    state.decision = await api(`/api/packets/${encodeURIComponent(state.selected)}/review`, {
      method: "POST",
      body: JSON.stringify({
        document_id: documentId,
        field,
        reviewer: $("reviewer").value,
        reason: $("reason").value,
      }),
    });
    state.detail = await api(`/api/packets/${encodeURIComponent(state.selected)}`);
    renderEvidence();
    renderDecision();
    await renderAudit();
    toast("Review saved. ReleaseGate checked the packet again.");
  } catch (error) { toast(error.message, true); }
}

async function requestSignature() {
  try {
    const result = await api(`/api/packets/${encodeURIComponent(state.selected)}/signature`, {
      method: "POST",
      body: JSON.stringify({ reviewer: $("reviewer").value, reason: $("reason").value }),
    });
    const envelope = result.envelope;
    $("signature-result").hidden = false;
    $("signature-result").innerHTML = `<strong>Signature step prepared but not sent.</strong><br>
      Envelope <code>${escapeHtml(envelope.envelope_id)}</code> · ${escapeHtml(envelope.status)}<br>
      ${escapeHtml(envelope.notice)}`;
    await renderAudit();
    toast("Approval saved. Nothing was sent.");
  } catch (error) { toast(error.message, true); }
}

async function renderAudit() {
  if (!state.selected) return;
  if (state.mode === "live") {
    $("audit-eyebrow").textContent = "NUTRIENT API REQUESTS";
    $("audit-title").textContent = "Five verified API calls";
    $("audit-events").className = "audit-events";
    $("audit-events").innerHTML = state.liveProof.documents.map((document, index) => `<div class="audit-event vendor-event">
      <span class="audit-sequence">${index + 1}</span>
      <div><strong>${escapeHtml(document.filename)}</strong><small>HTTP ${escapeHtml(document.vendor_status)} · ${escapeHtml(document.metrics.processing_time_ms)} ms · ${escapeHtml(Object.keys(document.fields).length)} fields</small></div>
      <span class="audit-hash">${escapeHtml(document.request_id)}</span>
    </div>`).join("");
    const summary = state.liveProof.summary;
    $("chain-status").textContent = `✓ ${summary.successful_requests}/${summary.documents} requests succeeded`;
    $("chain-status").className = "chain-status valid";
    return;
  }
  $("audit-eyebrow").textContent = "ACTIVITY HISTORY";
  $("audit-title").textContent = "Audit trail";
  const result = await api(`/api/packets/${encodeURIComponent(state.selected)}/audit`);
  const container = $("audit-events");
  if (!result.events.length) {
    container.className = "audit-events empty-state";
    container.textContent = "Check a packet to begin its protected activity record.";
  } else {
    container.className = "audit-events";
    container.innerHTML = result.events.map((event) => `<div class="audit-event">
      <span class="audit-sequence">${event.sequence}</span>
      <div><strong>${escapeHtml(event.action.replaceAll("_", " "))}</strong><small>${escapeHtml(event.actor)} · ${new Date(event.timestamp).toLocaleTimeString()}</small></div>
      <span class="audit-hash">${escapeHtml(event.hash.slice(0, 12))}…</span>
    </div>`).join("");
  }
  $("chain-status").textContent = result.chain.valid ? `✓ Chain verified · ${result.chain.events} events` : "Chain verification failed";
  $("chain-status").className = `chain-status ${result.chain.valid ? "valid" : ""}`;
}

async function init() {
  try {
    const [result, liveProof] = await Promise.all([api("/api/packets"), api("/api/live-proof")]);
    state.packets = result.packets;
    state.liveProof = liveProof;
    renderPackets();
    if (liveProof.available) {
      const summary = liveProof.summary;
      $("live-proof-button").disabled = false;
      $("live-proof-meta").textContent = `${summary.successful_requests} API calls · ${summary.fields} values found · saved result`;
      loadLiveProof();
    } else {
      $("live-proof-meta").textContent = "Verified API run unavailable. Sample packets are ready.";
      if (state.packets.length) await selectPacket(state.packets[0].packet_id);
    }
  } catch (error) { toast(error.message, true); }
}

$("evaluate-button").addEventListener("click", evaluate);
$("signature-button").addEventListener("click", requestSignature);
$("live-proof-button").addEventListener("click", loadLiveProof);
init();
