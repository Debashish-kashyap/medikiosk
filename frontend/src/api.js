// API client — mirrors the FastAPI contract in backend/app/models/schemas.py.
// Change a shape there? Update it here too.

const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

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

  createSession: (language) =>
    req("/api/session", { method: "POST", body: JSON.stringify({ language }) }),

  giveConsent: (sid, given = true) =>
    req(`/api/session/${sid}/consent`, { method: "POST", body: JSON.stringify({ given }) }),

  next: (sid) => req(`/api/session/${sid}/next`),

  // payload: { node_id, touch_value?, text?, confidence?, confirmed? }
  answer: (sid, payload) =>
    req(`/api/session/${sid}/answer`, { method: "POST", body: JSON.stringify(payload) }),

  summary: (sid) => req(`/api/session/${sid}/summary`),

  submit: (sid, clear = false) =>
    req(`/api/session/${sid}/submit?clear=${clear}`, { method: "POST" }),

  async uploadDocument(sid, file) {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/api/session/${sid}/documents`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json();
  },

  // Production ASR seam (the demo uses the browser Web Speech API instead).
  async transcribe(text, language = "en") {
    const fd = new FormData();
    fd.append("mock_text", text);
    fd.append("language", language);
    const res = await fetch(`${BASE}/api/asr`, { method: "POST", body: fd });
    return res.json();
  },
};
