const state = {
  user: null,
  summary: null,
  objects: [],
  selectedId: null,
  editId: null,
  authorities: [],
  taxonomy: [],
  storageLocations: [],
  intakeItems: [],
  selectedIntakeId: null,
  debounce: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const tabTitles = {
  catalog: ["Catalog", "Search, browse, and retrieve archive records."],
  record: ["Record", "Create or update catalog metadata."],
  authorities: ["Authorities", "Reusable people, organizations, places, events, and taxonomy."],
  storage: ["Storage", "Physical location hierarchy and digital storage references."],
  admin: ["Admin", "Media attachment, backup, and audit operations."],
};

const EXTENDED_FIELDS = [
  "alternative_title",
  "publisher",
  "contributors",
  "source",
  "relation",
  "coverage_spatial",
  "coverage_temporal",
  "physical_description",
  "extent",
  "medium",
  "citation",
  "external_identifier",
  "ark",
  "item_url",
  "thumbnail_url",
  "iiif_manifest_url",
  "license_uri",
  "access_rights",
  "primary_source",
  "resource_type",
  "genre_form",
  "series_title",
  "subcollection",
  "theater",
  "campaign",
  "battle",
  "military_unit",
  "vessel_aircraft",
  "modern_country",
  "wartime_jurisdiction",
  "subject_source",
  "metadata_profile",
  "display_note",
  "internal_note",
  "preservation_note",
  "metadata_json",
  "formal_test_data",
];

const CHECKBOX_FIELDS = ["primary_source", "formal_test_data"];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: options.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (response.status === 401 && path !== "/api/me") {
    showLogin();
  }
  if (!response.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

function showLogin() {
  $("#loginView").classList.remove("hidden");
  $("#appView").classList.add("hidden");
}

function showApp() {
  $("#loginView").classList.add("hidden");
  $("#appView").classList.remove("hidden");
}

function isAdmin() {
  return state.user?.role === "admin";
}

function setAdminMode() {
  $("#userName").textContent = state.user?.display_name || state.user?.username || "";
  $("#userRole").textContent = state.user?.role || "";

  const message = "Read-only account: catalog, authorities, storage, and permitted media are viewable.";
  for (const gate of [$("#recordGate"), $("#adminGate")]) {
    gate.textContent = message;
    gate.classList.toggle("visible", !isAdmin());
  }

  $$("#objectForm input, #objectForm textarea, #objectForm select, #saveRecordButton, #newRecordButton").forEach((el) => {
    el.disabled = !isAdmin();
  });
  $$("#uploadForm input, #uploadForm select, #uploadForm button, #driveLinkForm input, #driveLinkForm select, #driveLinkForm button, #intakeUploadForm input, #intakeUploadForm button, #intakeReviewForm input, #intakeReviewForm textarea, #intakeReviewForm select, #intakeReviewForm button, #refreshIntakeButton, #backupButton").forEach((el) => {
    el.disabled = !isAdmin();
  });
}

async function init() {
  bindEvents();
  try {
    const me = await api("/api/me");
    if (me.authenticated) {
      state.user = me.user;
      showApp();
      setAdminMode();
      await loadEverything();
    } else {
      showLogin();
    }
  } catch {
    showLogin();
  }
}

function bindEvents() {
  $("#loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    $("#loginError").textContent = "";
    const form = new FormData(event.currentTarget);
    try {
      const payload = await api("/api/login", {
        method: "POST",
        body: JSON.stringify({
          username: form.get("username"),
          password: form.get("password"),
        }),
      });
      state.user = payload.user;
      showApp();
      setAdminMode();
      await loadEverything();
    } catch (error) {
      $("#loginError").textContent = error.message;
    }
  });

  $("#logoutButton").addEventListener("click", async () => {
    await api("/api/logout", { method: "POST", body: JSON.stringify({}) }).catch(() => {});
    state.user = null;
    showLogin();
  });

  $$(".nav-tabs button").forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
  });

  [
    "#queryInput",
    "#collectionFilter",
    "#typeFilter",
    "#resourceTypeFilter",
    "#placeFilter",
    "#eventFilter",
    "#subjectFilter",
    "#campaignFilter",
    "#formalTestFilter",
    "#rightsFilter",
    "#dateFromFilter",
    "#dateToFilter",
  ].forEach((selector) => {
    $(selector).addEventListener("input", queueObjectLoad);
    $(selector).addEventListener("change", queueObjectLoad);
  });

  $("#clearFiltersButton").addEventListener("click", () => {
    [
      "#queryInput",
      "#collectionFilter",
      "#typeFilter",
      "#resourceTypeFilter",
      "#placeFilter",
      "#eventFilter",
      "#subjectFilter",
      "#campaignFilter",
      "#formalTestFilter",
      "#rightsFilter",
      "#dateFromFilter",
      "#dateToFilter",
    ].forEach((selector) => {
      $(selector).value = "";
    });
    loadObjects();
  });

  $("#objectList").addEventListener("click", (event) => {
    const card = event.target.closest("[data-object-id]");
    if (!card) return;
    selectObject(Number(card.dataset.objectId));
  });

  $("#recordDetail").addEventListener("click", (event) => {
    const edit = event.target.closest("[data-edit-id]");
    if (edit) {
      const object = state.objects.find((item) => item.id === Number(edit.dataset.editId));
      if (object) {
        fillObjectForm(object);
        switchTab("record");
      }
    }
  });

  $("#newRecordButton").addEventListener("click", () => clearObjectForm());
  $("#objectForm").addEventListener("submit", saveObject);
  $("#uploadForm").addEventListener("submit", uploadMedia);
  $("#driveLinkForm").addEventListener("submit", attachDriveLink);
  $("#intakeUploadForm").addEventListener("submit", uploadIntake);
  $("#refreshIntakeButton").addEventListener("click", loadIntake);
  $("#intakeList").addEventListener("click", (event) => {
    const item = event.target.closest("[data-intake-id]");
    if (!item) return;
    selectIntake(Number(item.dataset.intakeId));
  });
  $("#saveIntakeDraftButton").addEventListener("click", saveIntakeDraft);
  $("#intakeReviewForm").addEventListener("submit", submitIntake);
  $("#rejectIntakeButton").addEventListener("click", rejectIntake);
  $("#intakeSubmitMode").addEventListener("change", updateIntakeSubmitMode);
  $("#backupButton").addEventListener("click", generateBackup);
}

function switchTab(tab) {
  $$(".nav-tabs button").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
  $$(".tab-panel").forEach((panel) => panel.classList.remove("active"));
  $(`#${tab}Tab`).classList.add("active");
  const [title, subtitle] = tabTitles[tab] || tabTitles.catalog;
  $("#pageTitle").textContent = title;
  $("#pageSubtitle").textContent = subtitle;
  if (tab === "admin") {
    loadIntake();
    loadAudit();
  }
}

async function loadEverything() {
  const [summary, authorities, taxonomy] = await Promise.all([
    api("/api/summary"),
    api("/api/authorities"),
    api("/api/taxonomy"),
  ]);
  state.summary = summary;
  state.authorities = authorities.authorities;
  state.taxonomy = taxonomy.terms;
  state.storageLocations = isAdmin() ? (await api("/api/storage-locations")).locations : [];
  renderSummary();
  populateFilters(summary.facets);
  renderAuthorities();
  renderTaxonomy();
  renderStorage();
  await loadObjects();
  await loadIntake();
  await loadAudit();
}

function renderSummary() {
  const counts = state.summary?.counts || {};
  $("#summaryCounts").innerHTML = [
    ["objects", "Objects"],
    ["authorities", "Authorities"],
    ["digital_media", "Media"],
    ["storage_locations", "Locations"],
    ["formal_test_data", "Test Data"],
    ["intake_needs_review", "Intake"],
  ]
    .map(([key, label]) => `<div class="metric"><strong>${counts[key] ?? 0}</strong><span>${label}</span></div>`)
    .join("");
}

function populateFilters(facets) {
  fillSelect("#collectionFilter", facets.collection, "All collections");
  fillSelect("#typeFilter", facets.object_type, "All types");
  fillSelect("#resourceTypeFilter", facets.resource_type, "All resource types");
  fillSelect("#placeFilter", facets.place, "All places");
  fillSelect("#eventFilter", facets.event, "All events");
  fillSelect("#subjectFilter", facets.subject, "All subjects");
  fillSelect("#campaignFilter", facets.campaign, "All campaigns");
  fillSelect("#rightsFilter", facets.rights, "All rights");
}

function fillSelect(selector, values = [], label = "All") {
  const current = $(selector).value;
  $(selector).innerHTML = [`<option value="">${escapeHtml(label)}</option>`]
    .concat(values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`))
    .join("");
  if (values.includes(current)) {
    $(selector).value = current;
  }
}

function queueObjectLoad() {
  window.clearTimeout(state.debounce);
  state.debounce = window.setTimeout(loadObjects, 180);
}

function activeFilters() {
  return {
    query: $("#queryInput").value.trim(),
    collection: $("#collectionFilter").value,
    object_type: $("#typeFilter").value,
    resource_type: $("#resourceTypeFilter").value,
    place: $("#placeFilter").value,
    event: $("#eventFilter").value,
    subject: $("#subjectFilter").value,
    campaign: $("#campaignFilter").value,
    formal_test_data: $("#formalTestFilter").value,
    rights: $("#rightsFilter").value,
    date_from: $("#dateFromFilter").value.trim(),
    date_to: $("#dateToFilter").value.trim(),
  };
}

async function loadObjects() {
  const params = new URLSearchParams();
  Object.entries(activeFilters()).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const payload = await api(`/api/objects?${params.toString()}`);
  state.objects = payload.objects;
  $("#resultCount").textContent = `${payload.count} record${payload.count === 1 ? "" : "s"}`;
  renderObjectList();
  populateObjectSelects();
  if (!state.objects.some((item) => item.id === state.selectedId)) {
    state.selectedId = state.objects[0]?.id || null;
  }
  renderSelectedDetail();
}

function renderObjectList() {
  if (!state.objects.length) {
    $("#objectList").innerHTML = `<div class="empty">No matching records.</div>`;
    return;
  }
  $("#objectList").innerHTML = state.objects
    .map((object) => {
      const active = object.id === state.selectedId ? " active" : "";
      const mediaCount = object.media?.length || 0;
      const testLabel = object.formal_test_data ? " · Formal Test Data" : "";
      return `
        <button class="record-card${active}" type="button" data-object-id="${object.id}">
          <strong>${escapeHtml(object.permanent_id)} · ${escapeHtml(object.title)}</strong>
          <span class="meta-line">${escapeHtml(object.object_type)} · ${escapeHtml(object.date_label)} · ${escapeHtml(object.resource_type || "No resource type")} · ${escapeHtml(object.collection_name || "No collection")}${testLabel}</span>
          <span class="meta-line">${escapeHtml(object.storage_location_path || "No physical location")} · ${mediaCount} media</span>
        </button>
      `;
    })
    .join("");
}

function selectObject(id) {
  state.selectedId = id;
  renderObjectList();
  renderSelectedDetail();
}

function renderSelectedDetail() {
  const object = state.objects.find((item) => item.id === state.selectedId);
  if (!object) {
    $("#recordDetail").innerHTML = `<div class="empty">Select a record.</div>`;
    return;
  }
  const relationshipPills = object.relationships
    .map((rel) => `<span class="pill">${escapeHtml(rel.type)} · ${escapeHtml(rel.name)}</span>`)
    .join("");
  const termPills = object.terms.map((term) => `<span class="pill olive">${escapeHtml(term.vocabulary)} · ${escapeHtml(term.term)}</span>`).join("");
  const mediaRows = renderMediaRows(object);
  const formalPill = object.formal_test_data ? `<span class="pill rust">Formal Test Data</span>` : "";
  const extendedRows = renderExtendedMetadata(object);
  const stewardshipFields = isAdmin()
    ? `${detailField("Physical Location", object.storage_location_path)}`
    : "";
  $("#recordDetail").innerHTML = `
    <div class="detail-header">
      <div class="pill-row">
        <span class="pill rust">${escapeHtml(object.permanent_id)}</span>
        <span class="pill">${escapeHtml(object.object_type)}</span>
        <span class="pill">${escapeHtml(object.rights || "No rights")}</span>
        ${formalPill}
      </div>
      <h2>${escapeHtml(object.title)}</h2>
      ${object.alternative_title ? `<p class="muted">${escapeHtml(object.alternative_title)}</p>` : ""}
      <p class="muted">${escapeHtml(object.description || "")}</p>
      ${isAdmin() ? `<div><button type="button" data-edit-id="${object.id}">Edit</button></div>` : ""}
    </div>

    <div class="detail-grid">
      ${detailField("Collection", object.collection_name)}
      ${detailField("Date", object.date_label)}
      ${detailField("Language", object.language)}
      ${detailField("Digitization", object.digitization_status)}
      ${detailField("Condition", object.condition)}
      ${stewardshipFields}
      ${detailField("Resource Type", object.resource_type)}
      ${detailField("Campaign", object.campaign)}
      ${detailField("Battle", object.battle)}
      ${detailField("Access Rights", object.access_rights)}
      ${detailField("Provenance", object.provenance, true)}
      ${detailField("Extended Metadata", extendedRows, true, true)}
      ${detailField("Relationships", `<div class="pill-row">${relationshipPills || '<span class="muted">None</span>'}</div>`, true, true)}
      ${detailField("Taxonomy", `<div class="pill-row">${termPills || '<span class="muted">None</span>'}</div>`, true, true)}
      ${detailField("Digital Media", `<div class="media-list">${mediaRows}</div>`, true, true)}
    </div>
  `;
}

function detailField(label, value, wide = false, raw = false) {
  const content = raw ? value || "" : escapeHtml(value || "—");
  return `<div class="detail-field${wide ? " wide" : ""}"><span>${escapeHtml(label)}</span>${content}</div>`;
}

function renderExtendedMetadata(object) {
  const rows = [
    ["Publisher", object.publisher],
    ["Contributors", object.contributors],
    ["Source", object.source],
    ["Relation", object.relation],
    ["Spatial Coverage", object.coverage_spatial],
    ["Temporal Coverage", object.coverage_temporal],
    ["Physical Description", object.physical_description],
    ["Extent", object.extent],
    ["Medium", object.medium],
    ["Citation", object.citation],
    ["External Identifier", object.external_identifier],
    ["ARK", object.ark],
    ["Item URL", object.item_url],
    ["Thumbnail URL", object.thumbnail_url],
    ["IIIF Manifest URL", object.iiif_manifest_url],
    ["License URI", object.license_uri],
    ["Genre/Form", object.genre_form],
    ["Series", object.series_title],
    ["Subcollection", object.subcollection],
    ["Theater", object.theater],
    ["Military Unit", object.military_unit],
    ["Vessel/Aircraft", object.vessel_aircraft],
    ["Modern Country", object.modern_country],
    ["Wartime Jurisdiction", object.wartime_jurisdiction],
    ["Subject Source", object.subject_source],
    ["Metadata Profile", object.metadata_profile],
    ["Primary Source", object.primary_source ? "True" : "False"],
    ["Display Note", object.display_note],
  ].filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== "");

  if (isAdmin()) {
    [
      ["Internal Note", object.internal_note],
      ["Preservation Note", object.preservation_note],
    ].forEach((row) => {
      if (row[1] !== undefined && row[1] !== null && String(row[1]).trim() !== "") {
        rows.push(row);
      }
    });
  }

  if (!rows.length && !(isAdmin() && object.metadata_json)) {
    return `<span class="muted">No extended metadata.</span>`;
  }
  const tableRows = rows
    .map(([label, value]) => `<tr><th>${escapeHtml(label)}</th><td>${linkifyValue(value)}</td></tr>`)
    .join("");
  const jsonRow = isAdmin() && object.metadata_json
    ? `<tr><th>Metadata JSON</th><td><code>${escapeHtml(object.metadata_json)}</code></td></tr>`
    : "";
  return `<table class="metadata-table"><tbody>${tableRows}${jsonRow}</tbody></table>`;
}

function linkifyValue(value) {
  const text = String(value ?? "");
  if (text.startsWith("http://") || text.startsWith("https://")) {
    return `<a href="${escapeHtml(text)}" target="_blank" rel="noreferrer">${escapeHtml(text)}</a>`;
  }
  return escapeHtml(text);
}

function renderMediaRows(object) {
  if (!object.media?.length) {
    return `<div class="media-row"><span class="muted">No digital media attached.</span></div>`;
  }
  return object.media
    .map((media) => {
      const checksum = isAdmin() && media.checksum_sha256
        ? `<span class="muted">SHA-256 ${escapeHtml(media.checksum_sha256.slice(0, 14))}…</span>`
        : "";
      let action = "";
      if (media.storage_provider === "local") {
        if (object.rights === "Restricted" && !isAdmin()) {
          action = `<span class="muted">Restricted</span>`;
        } else {
          action = `<a href="/local-media/${media.id}">Download local file</a>`;
        }
      } else if (media.google_drive_url) {
        action = `<a href="${escapeHtml(media.google_drive_url)}" target="_blank" rel="noreferrer">Open Drive link</a>`;
      }
      return `
        <div class="media-row">
          <strong>${escapeHtml(media.filename)}</strong>
          <span class="muted">${escapeHtml(media.derivative_type)} · ${escapeHtml(media.storage_provider)} · ${escapeHtml(media.media_type || "unknown")} · ${media.size_bytes || 0} bytes</span>
          ${checksum}
          ${action}
        </div>
      `;
    })
    .join("");
}

function renderAuthorities() {
  const grouped = groupBy(state.authorities, "type");
  $("#authorityList").innerHTML = ["Person", "Organization", "Place", "Event"]
    .map((type) => {
      const rows = grouped[type] || [];
      return `
        <div class="authority-row">
          <strong>${type}</strong>
          ${rows.map((row) => `<span>${escapeHtml(row.name)} <small class="muted">${escapeHtml(row.aliases || "")}</small></span>`).join("") || '<span class="muted">None</span>'}
        </div>
      `;
    })
    .join("");
}

function renderTaxonomy() {
  const grouped = groupBy(state.taxonomy, "vocabulary");
  $("#taxonomyList").innerHTML = Object.keys(grouped)
    .sort()
    .map((vocab) => {
      return `
        <div class="taxonomy-row">
          <strong>${escapeHtml(vocab)}</strong>
          <div class="pill-row">
            ${grouped[vocab].map((row) => `<span class="pill">${escapeHtml(row.term)}</span>`).join("")}
          </div>
        </div>
      `;
    })
    .join("");
}

function renderStorage() {
  if (!isAdmin()) {
    $("#storageTree").innerHTML = `<div class="empty">Admin access required for storage locations.</div>`;
    return;
  }
  $("#storageTree").innerHTML = state.storageLocations
    .map((location) => {
      return `
        <div class="storage-row">
          <strong>${escapeHtml(location.path)}</strong>
          <span class="muted">${escapeHtml(location.location_type)} ${location.code ? "· " + escapeHtml(location.code) : ""}</span>
        </div>
      `;
    })
    .join("");
}

function populateObjectSelects() {
  const options = state.objects
    .map((object) => `<option value="${object.id}">${escapeHtml(object.permanent_id)} · ${escapeHtml(object.title)}</option>`)
    .join("");
  $("#uploadObjectSelect").innerHTML = options;
  $("#driveObjectSelect").innerHTML = options;
  $("#intakeExistingObjectSelect").innerHTML = options;
}

const INTAKE_FIELDS = [
  "permanent_id",
  "title",
  "object_type",
  "collection",
  "date_label",
  "date_start",
  "date_end",
  "language",
  "rights",
  "condition",
  "digitization_status",
  "storage_location",
  "description",
  "provenance",
  "creators",
  "people",
  "organizations",
  "places",
  "events",
  "subjects",
  "resource_type",
  "genre_form",
  "theater",
  "campaign",
  "battle",
  "modern_country",
  "metadata_profile",
  "display_note",
  "internal_note",
  "preservation_note",
  "metadata_json",
];

async function loadIntake() {
  if (!isAdmin()) {
    $("#intakeList").innerHTML = `<div class="empty">Admin access required.</div>`;
    $("#intakeReviewForm").classList.add("hidden");
    return;
  }
  try {
    const payload = await api("/api/admin/intake");
    state.intakeItems = payload.items;
    renderIntakeList();
    if (state.selectedIntakeId && !state.intakeItems.some((item) => item.id === state.selectedIntakeId)) {
      state.selectedIntakeId = null;
    }
  } catch (error) {
    $("#intakeList").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
}

function renderIntakeList() {
  if (!state.intakeItems.length) {
    $("#intakeList").innerHTML = `<div class="empty">No intake drafts yet.</div>`;
    $("#intakeReviewForm").classList.add("hidden");
    return;
  }
  $("#intakeList").innerHTML = state.intakeItems
    .map((item) => {
      const active = item.id === state.selectedIntakeId ? " active" : "";
      const draft = item.edited || item.suggested || {};
      return `
        <button class="record-card${active}" type="button" data-intake-id="${item.id}">
          <strong>${escapeHtml(item.filename)}</strong>
          <span class="meta-line">${escapeHtml(item.status)} · ${escapeHtml(draft.title || "Untitled draft")}</span>
          <span class="meta-line">${escapeHtml(item.media_type || "unknown")} · ${item.size_bytes || 0} bytes · ${escapeHtml(item.created_at)}</span>
        </button>
      `;
    })
    .join("");
}

function selectIntake(id) {
  state.selectedIntakeId = id;
  renderIntakeList();
  const item = state.intakeItems.find((row) => row.id === id);
  if (!item) return;
  fillIntakeForm(item);
}

function fillIntakeForm(item) {
  const form = $("#intakeReviewForm");
  const draft = item.edited || item.suggested || {};
  INTAKE_FIELDS.forEach((field) => {
    if (!form.elements[field]) return;
    form.elements[field].value = draft[field] || "";
  });
  form.elements.derivative_type.value = draft.derivative_type || "preservation_master";
  form.elements.submit_mode.value = "create_object";
  $("#intakeEditorTitle").textContent = item.filename;
  $("#intakeStatus").textContent = `${item.status} · SHA-256 ${(item.checksum_sha256 || "").slice(0, 14)}…`;
  $("#intakeMessage").textContent = "";
  form.classList.remove("hidden");
  updateIntakeSubmitMode();
}

function intakeFormPayload() {
  const form = $("#intakeReviewForm");
  const payload = {};
  INTAKE_FIELDS.forEach((field) => {
    if (!form.elements[field]) return;
    payload[field] = form.elements[field].value.trim();
  });
  payload.primary_source = "true";
  payload.formal_test_data = "false";
  return payload;
}

function updateIntakeSubmitMode() {
  const attachMode = $("#intakeSubmitMode").value === "attach_existing";
  $("#intakeExistingObjectLabel").classList.toggle("hidden", !attachMode);
  INTAKE_FIELDS.forEach((field) => {
    const element = $("#intakeReviewForm").elements[field];
    if (element) element.disabled = attachMode && field !== "metadata_json";
  });
}

async function uploadIntake(event) {
  event.preventDefault();
  if (!isAdmin()) return;
  const form = event.currentTarget;
  const files = Array.from(form.elements.files.files || []);
  if (!files.length) return;
  const body = new FormData();
  files.forEach((file) => body.append("files", file));
  $("#intakeUploadMessage").textContent = "Uploading…";
  try {
    const result = await api("/api/admin/intake/upload", { method: "POST", body });
    $("#intakeUploadMessage").textContent = `Created ${result.items.length} draft${result.items.length === 1 ? "" : "s"}.`;
    form.reset();
    state.selectedIntakeId = result.items[0]?.id || null;
    await refreshAfterMutation();
    selectIntake(state.selectedIntakeId);
  } catch (error) {
    $("#intakeUploadMessage").textContent = error.message;
  }
}

async function saveIntakeDraft() {
  if (!isAdmin() || !state.selectedIntakeId) return;
  $("#intakeMessage").textContent = "Saving draft…";
  try {
    const payload = await api(`/api/admin/intake/${state.selectedIntakeId}`, {
      method: "PUT",
      body: JSON.stringify({ edited: intakeFormPayload() }),
    });
    const index = state.intakeItems.findIndex((item) => item.id === state.selectedIntakeId);
    if (index >= 0) state.intakeItems[index] = payload.item;
    $("#intakeMessage").textContent = "Draft saved.";
    renderIntakeList();
    await loadAudit();
  } catch (error) {
    $("#intakeMessage").textContent = error.message;
  }
}

async function submitIntake(event) {
  event.preventDefault();
  if (!isAdmin() || !state.selectedIntakeId) return;
  const form = event.currentTarget;
  const mode = form.submit_mode.value;
  const body = {
    mode,
    derivative_type: form.derivative_type.value,
    edited: intakeFormPayload(),
  };
  if (mode === "attach_existing") {
    body.object_id = form.object_id.value;
  }
  $("#intakeMessage").textContent = "Submitting…";
  try {
    const result = await api(`/api/admin/intake/${state.selectedIntakeId}/submit`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    state.selectedId = result.object.id;
    state.selectedIntakeId = null;
    $("#intakeReviewForm").classList.add("hidden");
    await refreshAfterMutation();
    switchTab("catalog");
  } catch (error) {
    $("#intakeMessage").textContent = error.message;
  }
}

async function rejectIntake() {
  if (!isAdmin() || !state.selectedIntakeId) return;
  const reason = window.prompt("Reject reason", "Rejected during curator review.") || "";
  $("#intakeMessage").textContent = "Rejecting…";
  try {
    await api(`/api/admin/intake/${state.selectedIntakeId}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
    state.selectedIntakeId = null;
    $("#intakeReviewForm").classList.add("hidden");
    await refreshAfterMutation();
  } catch (error) {
    $("#intakeMessage").textContent = error.message;
  }
}

function groupBy(rows, key) {
  return rows.reduce((acc, row) => {
    const value = row[key] || "Other";
    acc[value] = acc[value] || [];
    acc[value].push(row);
    return acc;
  }, {});
}

function clearObjectForm() {
  state.editId = null;
  $("#objectForm").reset();
  const primary = $("#objectForm [name=primary_source]");
  if (primary) primary.checked = true;
  $("#recordMessage").textContent = "";
  $("#objectForm [name=permanent_id]").focus();
}

function fillObjectForm(object) {
  state.editId = object.id;
  const form = $("#objectForm");
  form.permanent_id.value = object.permanent_id || "";
  form.title.value = object.title || "";
  form.object_type.value = object.object_type || "";
  form.collection.value = object.collection_name || "";
  form.date_label.value = object.date_label || "";
  form.date_start.value = object.date_start || "";
  form.date_end.value = object.date_end || "";
  form.language.value = object.language || "";
  form.rights.value = object.rights || "";
  form.condition.value = object.condition || "";
  form.digitization_status.value = object.digitization_status || "";
  form.storage_location.value = object.storage_location_path || "";
  form.description.value = object.description || "";
  form.provenance.value = object.provenance || "";
  form.creators.value = namesBy(object, "Person", "creator").join(", ");
  form.people.value = namesBy(object, "Person", "person").join(", ");
  form.organizations.value = namesBy(object, "Organization").join(", ");
  form.places.value = namesBy(object, "Place").join(", ");
  form.events.value = namesBy(object, "Event").join(", ");
  form.subjects.value = (object.terms || []).filter((term) => term.vocabulary === "Subject").map((term) => term.term).join(", ");
  EXTENDED_FIELDS.forEach((field) => {
    if (!form.elements[field]) return;
    if (CHECKBOX_FIELDS.includes(field)) {
      form.elements[field].checked = Boolean(object[field]);
    } else {
      form.elements[field].value = object[field] || "";
    }
  });
  $("#recordMessage").textContent = `Editing ${object.permanent_id}`;
}

function namesBy(object, type, role = null) {
  return (object.relationships || [])
    .filter((rel) => rel.type === type && (!role || rel.role === role))
    .map((rel) => rel.name);
}

async function saveObject(event) {
  event.preventDefault();
  if (!isAdmin()) return;
  const form = event.currentTarget;
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  CHECKBOX_FIELDS.forEach((field) => {
    payload[field] = form.elements[field]?.checked ? "true" : "false";
  });
  const method = state.editId ? "PUT" : "POST";
  const path = state.editId ? `/api/objects/${state.editId}` : "/api/objects";
  $("#recordMessage").textContent = "Saving…";
  try {
    const saved = await api(path, { method, body: JSON.stringify(payload) });
    state.selectedId = saved.object.id;
    state.editId = saved.object.id;
    $("#recordMessage").textContent = `Saved ${saved.object.permanent_id}`;
    await refreshAfterMutation();
    switchTab("catalog");
  } catch (error) {
    $("#recordMessage").textContent = error.message;
  }
}

async function uploadMedia(event) {
  event.preventDefault();
  if (!isAdmin()) return;
  const form = event.currentTarget;
  const objectId = form.object_id.value;
  const body = new FormData();
  body.set("derivative_type", form.derivative_type.value);
  body.set("file", form.file.files[0]);
  try {
    await api(`/api/objects/${objectId}/media`, { method: "POST", body });
    form.reset();
    await refreshAfterMutation();
  } catch (error) {
    alert(error.message);
  }
}

async function attachDriveLink(event) {
  event.preventDefault();
  if (!isAdmin()) return;
  const form = event.currentTarget;
  const objectId = form.object_id.value;
  const payload = Object.fromEntries(new FormData(form).entries());
  delete payload.object_id;
  try {
    await api(`/api/objects/${objectId}/media-link`, { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    await refreshAfterMutation();
  } catch (error) {
    alert(error.message);
  }
}

async function generateBackup() {
  if (!isAdmin()) return;
  $("#backupResult").textContent = "Generating…";
  try {
    const result = await api("/api/admin/backup", { method: "POST", body: JSON.stringify({}) });
    $("#backupResult").innerHTML = `
      <strong>${escapeHtml(result.backup)}</strong>
      <code>${escapeHtml(result.path)}</code>
    `;
    await loadAudit();
  } catch (error) {
    $("#backupResult").textContent = error.message;
  }
}

async function refreshAfterMutation() {
  const [summary, authorities, taxonomy] = await Promise.all([
    api("/api/summary"),
    api("/api/authorities"),
    api("/api/taxonomy"),
  ]);
  state.summary = summary;
  state.authorities = authorities.authorities;
  state.taxonomy = taxonomy.terms;
  state.storageLocations = isAdmin() ? (await api("/api/storage-locations")).locations : [];
  renderSummary();
  populateFilters(summary.facets);
  renderAuthorities();
  renderTaxonomy();
  renderStorage();
  await loadObjects();
  await loadIntake();
  await loadAudit();
}

async function loadAudit() {
  if (!state.user) return;
  if (!isAdmin()) {
    $("#auditList").innerHTML = `<div class="empty">Admin access required for audit logs.</div>`;
    return;
  }
  try {
    const payload = await api("/api/audit");
    $("#auditList").innerHTML = payload.logs
      .map((log) => {
        return `
          <div class="audit-row">
            <strong>${escapeHtml(log.action)} · ${escapeHtml(log.entity_type)}:${escapeHtml(log.entity_id)}</strong>
            <span class="muted">${escapeHtml(log.actor)} · ${escapeHtml(log.created_at)}</span>
            <span>${escapeHtml(log.details || "")}</span>
          </div>
        `;
      })
      .join("");
  } catch {
    $("#auditList").innerHTML = `<div class="empty">Audit unavailable.</div>`;
  }
}

init();
