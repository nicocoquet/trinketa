(() => {
  "use strict";
  const root = document.querySelector("[data-isbn-deposit]");
  if (!root) return;
  const config = window.TRINKETA_ISBN_CONFIG || {};
  const apiBaseUrl = String(config.apiBaseUrl || "").replace(/\/$/, "");
  const allowedUsers = new Set((config.allowedUsers || []).map((value) => value.toLowerCase()));
  const sessionBar = root.querySelector(".isbn-session");
  const elements = {
    login: root.querySelector("[data-login]"), logout: root.querySelector("[data-logout]"),
    sessionLabel: root.querySelector("[data-session-label]"), drop: root.querySelector("[data-drop]"),
    input: root.querySelector("[data-file-input]"), select: root.querySelector("[data-select]"),
    files: root.querySelector("[data-files]"), public: root.querySelector("[data-public]"),
    confirm: root.querySelector("[data-confirm]"), upload: root.querySelector("[data-upload]"),
    uploadStatus: root.querySelector("[data-upload-status]"), uploadResult: root.querySelector("[data-upload-result]"),
    prLink: root.querySelector("[data-pr-link]"), queueCount: root.querySelector("[data-queue-count]"),
    analyse: root.querySelector("[data-analyse]"), analysisStatus: root.querySelector("[data-analysis-status]"),
  };
  const state = { user: null, files: [], session: window.sessionStorage.getItem("trinketaIsbnSession") || "" };
  const callbackSession = new URLSearchParams(window.location.hash.slice(1)).get("session");
  if (callbackSession) {
    state.session = callbackSession;
    window.sessionStorage.setItem("trinketaIsbnSession", callbackSession);
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
  }

  function apiUrl(path) { return `${apiBaseUrl}${path}`; }
  async function api(path, options = {}) {
    const response = await fetch(apiUrl(path), {
      ...options,
      headers: {
        ...(state.session ? { Authorization: `Bearer ${state.session}` } : {}),
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
    });
    const body = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) throw new Error(body?.detail || body?.message || `Erreur du service (${response.status}).`);
    return body;
  }
  function formatBytes(bytes) {
    return bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(0)} Ko` : `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
  }
  function setStatus(element, message, type = "neutral") {
    element.textContent = message;
    element.dataset.type = type;
  }
  function validFile(file) {
    const extension = file.name.toLowerCase().match(/\.[^.]+$/)?.[0] || "";
    if (![".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"].includes(extension)) return "Format non accepté";
    if (!file.size || file.size > 15 * 1024 * 1024) return "Poids supérieur à 15 Mo";
    return "";
  }
  function updateControls() {
    const authorized = Boolean(state.user && allowedUsers.has(state.user.login.toLowerCase()));
    elements.upload.disabled = !(authorized && state.files.length && !state.files.some(validFile) && elements.confirm.checked);
    elements.analyse.disabled = !authorized;
  }
  function renderFiles() {
    elements.files.innerHTML = "";
    state.files.forEach((file, index) => {
      const item = document.createElement("li");
      const error = validFile(file);
      item.innerHTML = `<span><strong></strong><small></small></span><button type="button" aria-label="Retirer cette image">×</button>`;
      item.querySelector("strong").textContent = file.name;
      item.querySelector("small").textContent = error || formatBytes(file.size);
      if (error) item.dataset.invalid = "true";
      item.querySelector("button").addEventListener("click", () => { state.files.splice(index, 1); renderFiles(); });
      elements.files.appendChild(item);
    });
    const hasFiles = state.files.length > 0;
    elements.files.hidden = !hasFiles;
    elements.public.hidden = !hasFiles;
    elements.uploadResult.hidden = true;
    if (!hasFiles) elements.confirm.checked = false;
    if (state.files.some(validFile)) setStatus(elements.uploadStatus, "Retirez les images signalées avant l’envoi.", "error");
    else if (hasFiles) setStatus(elements.uploadStatus, `${state.files.length} photographie(s) prête(s) à être déposée(s).`);
    updateControls();
  }
  function selectFiles(files) {
    const unique = new Map([...state.files, ...files].map((file) => [file.name.toLowerCase(), file]));
    state.files = [...unique.values()].slice(0, 10);
    renderFiles();
    if (unique.size > 10) setStatus(elements.uploadStatus, "Un dépôt est limité à dix photographies.", "error");
  }
  function readAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(",", 2)[1]);
      reader.onerror = () => reject(new Error(`Lecture impossible : ${file.name}`));
      reader.readAsDataURL(file);
    });
  }
  async function loadQueue() {
    if (!state.user) return;
    try {
      const queue = await api("/api/queue");
      elements.queueCount.textContent = String(queue.count);
    } catch (error) {
      elements.queueCount.textContent = "?";
      setStatus(elements.analysisStatus, error.message, "error");
    }
  }
  function updateSession(user) {
    state.user = user;
    const authorized = Boolean(user && allowedUsers.has(user.login.toLowerCase()));
    sessionBar.dataset.sessionState = authorized ? "connected" : "disconnected";
    elements.login.hidden = authorized;
    elements.logout.hidden = !authorized;
    elements.sessionLabel.textContent = authorized ? `Connecté avec GitHub : ${user.login}` : "Connexion GitHub requise";
    updateControls();
    if (authorized) loadQueue();
  }
  async function loadSession() {
    if (!apiBaseUrl) {
      setStatus(elements.uploadStatus, "Le service de dépôt reste à configurer.", "error");
      return;
    }
    if (!state.session) { updateSession(null); return; }
    try {
      const session = await api("/auth/session");
      updateSession(session.user || null);
    } catch (error) {
      state.session = "";
      window.sessionStorage.removeItem("trinketaIsbnSession");
      updateSession(null);
      setStatus(elements.uploadStatus, error.message, "error");
    }
  }
  async function upload() {
    elements.upload.disabled = true;
    setStatus(elements.uploadStatus, "Envoi des photographies et création de la pull request…");
    try {
      const files = await Promise.all(state.files.map(async (file) => ({ filename: file.name, content: await readAsBase64(file) })));
      const result = await api("/api/uploads", { method: "POST", body: JSON.stringify({ files }) });
      elements.prLink.href = result.pullRequest.url;
      elements.prLink.textContent = `Ouvrir la pull request nº ${result.pullRequest.number} →`;
      state.files = [];
      renderFiles();
      elements.uploadResult.hidden = false;
      setStatus(elements.uploadStatus, "Pull request créée avec succès.", "success");
    } catch (error) {
      setStatus(elements.uploadStatus, error.message, "error");
      updateControls();
    }
  }
  async function analyse() {
    elements.analyse.disabled = true;
    setStatus(elements.analysisStatus, "Démarrage du traitement GitHub…");
    try {
      const result = await api("/api/analysis", { method: "POST" });
      setStatus(elements.analysisStatus, "Analyse lancée. Une pull request de validation sera créée à la fin du traitement.", "success");
      window.open(result.actionsUrl, "_blank", "noopener");
    } catch (error) {
      setStatus(elements.analysisStatus, error.message, "error");
    } finally { updateControls(); }
  }

  elements.login.addEventListener("click", () => window.location.assign(apiUrl(`/auth/github?returnTo=${encodeURIComponent(window.location.href)}`)));
  elements.logout.addEventListener("click", async () => {
    try { await api("/auth/logout", { method: "POST" }); } catch (_) { /* session locale supprimée malgré tout */ }
    state.session = "";
    window.sessionStorage.removeItem("trinketaIsbnSession");
    updateSession(null);
  });
  elements.select.addEventListener("click", (event) => { event.stopPropagation(); elements.input.click(); });
  elements.input.addEventListener("change", () => selectFiles([...elements.input.files]));
  elements.confirm.addEventListener("change", updateControls);
  elements.upload.addEventListener("click", upload);
  elements.analyse.addEventListener("click", analyse);
  elements.drop.addEventListener("click", (event) => { if (event.target === elements.drop) elements.input.click(); });
  elements.drop.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); elements.input.click(); }
  });
  ["dragenter", "dragover"].forEach((name) => elements.drop.addEventListener(name, (event) => { event.preventDefault(); elements.drop.classList.add("is-dragging"); }));
  ["dragleave", "drop"].forEach((name) => elements.drop.addEventListener(name, (event) => { event.preventDefault(); elements.drop.classList.remove("is-dragging"); }));
  elements.drop.addEventListener("drop", (event) => selectFiles([...event.dataTransfer.files]));
  loadSession();
})();
