// API client — mirrors the FastAPI contract in backend/app/models/schemas.py.
// Change a shape there? Update it here too.

import { enqueueFile, enqueueMutation, listFiles, listMutations, removeFile, removeMutation } from "./offlineStore";

const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// Must be defined before it's used by transcribeAudio below.
function blobFilename(blob) {
  const type = (blob.type || "").toLowerCase();
  if (type.includes("mp4") || type.includes("m4a")) return "clip.m4a";
  if (type.includes("ogg")) return "clip.ogg";
  if (type.includes("wav")) return "clip.wav";
  return "clip.webm";
}

async function req(path, opts = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
  } catch (error) {
    const offlineError = new Error("Network unavailable. Your work can be saved locally and synced when connection returns.");
    offlineError.name = "OfflineError";
    offlineError.cause = error;
    throw offlineError;
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json();
}

export function isOfflineError(error) {
  return error?.name === "OfflineError" || (typeof navigator !== "undefined" && !navigator.onLine);
}

export async function queueOfflineMutation(path, opts = {}) {
  await enqueueMutation({
    path,
    method: opts.method || "POST",
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    body: opts.body || null,
  });
}

export async function flushOfflineMutations() {
  const pending = await listMutations();
  for (const mutation of pending) {
    try {
      await req(mutation.path, {
        method: mutation.method,
        headers: mutation.headers,
        body: mutation.body,
      });
      await removeMutation(mutation.id);
    } catch (error) {
      if (isOfflineError(error)) break;
      // Keep validation/auth failures queued for an explicit retry.
      break;
    }
  }
  for (const file of await listFiles()) {
    try {
      await uploadDocumentOnline(file.sessionId, file.blob, file.name, file.type);
      await removeFile(file.id);
    } catch (error) {
      if (isOfflineError(error)) break;
      break;
    }
  }
}

export async function queueOfflineUpload(sessionId, file) {
  await enqueueFile({ sessionId, blob: file, name: file.name, type: file.type });
}

async function uploadDocumentOnline(sessionId, file, name = "document", type = "") {
  const fd = new FormData();
  fd.append("file", file, name);
  let res;
  try {
    res = await fetch(`${BASE}/api/session/${sessionId}/documents`, { method: "POST", body: fd });
  } catch (error) {
    const offlineError = new Error("Network unavailable while uploading document.");
    offlineError.name = "OfflineError";
    offlineError.cause = error;
    throw offlineError;
  }
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export const api = {
  base: BASE,

  createSession: (language, ayush_mode = false) =>
    req("/api/session", { method: "POST", body: JSON.stringify({ language, ayush_mode }) }),

  giveConsent: (sid, identity = {}) =>
    req(`/api/session/${sid}/consent`, {
      method: "POST",
      body: JSON.stringify({ given: true, ...identity }),
    }),

  next: (sid) => req(`/api/session/${sid}/next`),

  // payload: { node_id, touch_value?, text?, confidence?, confirmed? }
  answer: (sid, payload) =>
    req(`/api/session/${sid}/answer`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  summary: (sid) => req(`/api/session/${sid}/summary`),

  submit: (sid, clear = false) =>
    req(`/api/session/${sid}/submit?clear=${clear}`, { method: "POST" }),

  queue: (userId = "dashboard", role = "physician", token = "") =>
    req("/api/queue", { headers: token ? { Authorization: `Bearer ${token}` } : { "X-User-Id": userId, "X-Role": role } }),
  physicianLogin: (userId, password) =>
    req("/api/auth/physician", { method: "POST", body: JSON.stringify({ user_id: userId, password }) }),
  savePhysicianReview: (sid, hpi, token) =>
    req(`/api/records/${sid}/physician-review`, { method: "PATCH", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ hpi }) }),
  signOffRecord: (sid, token) =>
    req(`/api/records/${sid}/sign-off`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }),
  updateQueuePriority: (sid, priority, token) =>
    req(`/api/queue/${sid}`, { method: "PATCH", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ priority }) }),

  async uploadDocument(sid, file) {
    return uploadDocumentOnline(sid, file, file.name, file.type);
  },

  // Module D & Privacy / Access Log (Estonian model & DPDP)
  getAccessLog: (sid) => req(`/api/session/${sid}/access-log`),
  getRights: (sid) => req(`/api/session/${sid}/rights`),
  setPermissions: (sid, permissions) =>
    req(`/api/session/${sid}/permissions`, {
      method: "POST",
      body: JSON.stringify(permissions),
    }),
  eraseData: (sid) => req(`/api/session/${sid}/data`, { method: "DELETE" }),

  // Check which ASR engine is active on the server.
  asrStatus: () => req("/api/asr/status"),

  // Testing helper — bypasses real ASR.
  async transcribe(text, language = "en") {
    const fd = new FormData();
    fd.append("mock_text", text);
    fd.append("language", language);
    const res = await fetch(`${BASE}/api/asr`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(`ASR mock failed: ${res.status}`);
    return res.json();
  },

  // Production path — send a recorded audio blob to the server ASR engine.
  async transcribeAudio(blob, language = "en") {
    const fd = new FormData();
    fd.append("audio", blob, blobFilename(blob));
    fd.append("language", language);
    const res = await fetch(`${BASE}/api/asr`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(`ASR failed: ${res.status}`);
    return res.json();
  },

  async synthesizeSpeech(text, language = "en") {
    const fd = new FormData();
    fd.append("text", text);
    fd.append("language", language);
    const res = await fetch(`${BASE}/api/tts`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(`TTS unavailable: ${res.status}`);
    return res.blob();
  },
};
