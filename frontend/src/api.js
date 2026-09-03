// API client — mirrors the FastAPI contract in backend/app/models/schemas.py.
// Change a shape there? Update it here too.

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
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json();
}

export const api = {
  base: BASE,

  createSession: (language, ayush_mode = false) =>
    req("/api/session", { method: "POST", body: JSON.stringify({ language, ayush_mode }) }),

  giveConsent: (sid, given = true, abhaId = "", otp = "") =>
    req(`/api/session/${sid}/consent`, {
      method: "POST",
      body: JSON.stringify({ given, abha_id: abhaId, otp }),
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

  async uploadDocument(sid, file) {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/api/session/${sid}/documents`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json();
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
};
