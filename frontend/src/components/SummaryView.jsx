import { useState } from "react";
import { api } from "../api";
import { t } from "../i18n";

// Helper: get file type icon based on mime type or filename
function getFileIcon(filename, type) {
  const lower = (filename || "").toLowerCase();
  const media = (type || "").toLowerCase();

  if (media.includes("pdf")) return "📄";
  if (media.includes("image")) {
    if (media.includes("png")) return "🖼️ PNG";
    if (media.includes("jpeg") || media.includes("jpg")) return "📷 JPG";
    if (media.includes("webp")) return "🖼️ WEBP";
  }
  if (lower.endsWith(".pdf")) return "📄";
  if (lower.endsWith(".png")) return "🖼️ PNG";
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "📷 JPG";
  if (lower.endsWith(".webp")) return "🖼️ WEBP";
  return "📄";
}

// Module C output for the physician: structured, EDITABLE, verifiable — never an
// autonomous diagnosis. Also hosts Module B (document upload) and Module D (FHIR/submit).
export default function SummaryView({ lang, sessionId, summary, redFlags, onRestart }) {
  const [sum, setSum] = useState(summary);
  const [hpi, setHpi] = useState(summary.hpi);
  const [fhir, setFhir] = useState(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);

  async function onUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await api.uploadDocument(sessionId, file);
      setSum(await api.summary(sessionId)); // refresh timeline + investigations
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function onGenerate() {
    setBusy(true);
    try {
      const res = await api.submit(sessionId, false);
      setFhir(res.fhir_bundle);
    } finally {
      setBusy(false);
    }
  }

  const docs = sum.prior_investigations || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">{t(lang, "summaryTitle")}</h2>
        <span className="text-xs bg-slate-200 rounded-full px-3 py-1">{t(lang, "forPhysician")}</span>
      </div>

      {(redFlags?.length ?? 0) > 0 && (
        <div className="rounded-xl border-2 border-kiosk-danger bg-red-50 p-4">
          <div className="font-bold text-kiosk-danger mb-2">⚠️ Priority alerts</div>
          <ul className="list-disc ml-5 text-sm text-red-800">
            {redFlags.map((f) => (
              <li key={f.id}>
                <b>[{f.priority}]</b> {f.label} — {f.action}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="bg-white rounded-2xl shadow divide-y">
        <Row label="Chief complaint" value={sum.chief_complaint} />
        <div className="p-4">
          <div className="text-xs uppercase tracking-wide text-slate-400 mb-1">{t(lang, "physicianNote")}</div>
          <textarea
            className="w-full border rounded-lg p-3 text-slate-800 min-h-[80px]"
            value={hpi}
            onChange={(e) => setHpi(e.target.value)}
          />
        </div>
        <Row label="Past medical history" value={sum.past_medical} />
        <Row label="Drug allergy" value={sum.drug_allergy} />
        <Row label="Review of systems" value={sum.review_of_systems} />
        {sum.contradictions?.length > 0 && (
          <Row label="⚠ To verify" value={sum.contradictions.join(" ")} />
        )}
      </div>

      {/* Module B — digitized documents / prior investigations. */}
      <div className="bg-white rounded-2xl shadow p-4">
        {/* Header with upload zone */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <div className="font-semibold">Prior documents & investigations</div>
            <div className="flex items-center gap-2">
              {uploading && (
                <span className="flex items-center gap-2 text-sm text-kiosk-primary animate-pulse">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Processing with Gemini...
                </span>
              )}
              <label className={`tap px-4 py-2 cursor-pointer text-sm rounded-lg border ${uploading ? "opacity-50 cursor-not-allowed border-slate-300 bg-slate-100" : "border-kiosk-primary bg-kiosk-primary text-white hover:bg-kiosk-primary/90"}`}>
                {uploading ? "Uploading..." : t(lang, "uploadDoc")}
                <input type="file" className="hidden" onChange={onUpload} disabled={uploading} accept="image/png,image/jpeg,image/webp,application/pdf" />
              </label>
            </div>
          </div>

          {/* Drag and drop zone */}
          {!uploading && docs.length === 0 && (
            <div className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center hover:border-kiosk-primary hover:bg-kiosk-primary/5 transition">
              <div className="text-4xl mb-2">📎</div>
              <p className="text-slate-600 font-medium">Drag & drop medical documents here</p>
              <p className="text-slate-400 text-sm mt-1">PDF, PNG, JPG, WEBP supported</p>
            </div>
          )}
        </div>

        {/* Documents Grid */}
        {docs.length === 0 ? (
          <p className="text-slate-400 text-sm text-center py-8">No documents added yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {docs.map((d) => (
              <div key={d.doc_id} className="border border-slate-200 rounded-xl p-4 hover:shadow-md transition hover:border-kiosk-primary/50">
                {/* Thumbnail/Preview */}
                <div className="flex items-center gap-3 mb-3 p-3 bg-slate-50 rounded-lg">
                  <div className="text-3xl flex-shrink-0">{getFileIcon(d.filename || "", d.mime_type || "")}</div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm text-slate-900 truncate" title={d.filename || d.type}>
                      {d.filename || d.type}
                    </div>
                    <div className="text-xs text-slate-500">{d.date}</div>
                  </div>
                </div>

                {/* Metadata */}
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-xs bg-slate-100 px-2 py-1 rounded text-slate-600">
                      OCR {Math.round((d.ocr_confidence || 0) * 100)}%
                    </span>
                    {d.entities?.medications?.length > 0 && (
                      <span className="text-xs bg-green-50 px-2 py-1 rounded text-green-700">
                        📄 Meds ({d.entities.medications.length})
                      </span>
                    )}
                    {d.entities?.investigations?.length > 0 && (
                      <span className="text-xs bg-blue-50 px-2 py-1 rounded text-blue-700">
                        📊 Labs ({d.entities.investigations.length})
                      </span>
                    )}
                  </div>

                  {/* Preview Medications */}
                  {d.entities?.medications?.length > 0 && (
                    <div className="text-sm text-slate-700">
                      <div className="text-xs uppercase tracking-wide text-slate-400 mb-1">Medications</div>
                      <div className="text-xs">
                        {d.entities.medications.slice(0, 3).map((m) => (
                          <span key={m.name} className="inline-block bg-slate-100 rounded px-2 py-1 mr-1 mb-1">
                            {m.name}
                          </span>
                        ))}
                        {d.entities.medications.length > 3 && (
                          <span className="text-slate-400">+{d.entities.medications.length - 3} more</span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Preview Investigations */}
                  {d.entities?.investigations?.length > 0 && (
                    <div className="text-sm text-slate-700">
                      <div className="text-xs uppercase tracking-wide text-slate-400 mb-1">Investigations</div>
                      <div className="space-y-1">
                        {d.entities.investigations.slice(0, 3).map((iv, idx) => (
                          <div key={idx} className="flex justify-between text-xs">
                            <span className={iv.flag === "HIGH" || iv.flag === "LOW" ? "text-kiosk-danger font-semibold" : "text-slate-700"}>
                              {iv.name}
                            </span>
                            <span className={iv.flag === "HIGH" || iv.flag === "LOW" ? "text-kiosk-danger font-semibold" : "text-slate-600"}>
                              {iv.value} {iv.unit} {iv.flag !== "NORMAL" && `(${iv.flag})`}
                            </span>
                          </div>
                        ))}
                        {d.entities.investigations.length > 3 && (
                          <div className="text-slate-400 text-xs">+{d.entities.investigations.length - 3} more</div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Module D — generate FHIR bundle (ABDM push mocked). */}
      <button className="tap tap-selected w-full py-5" disabled={busy} onClick={onGenerate}>
        {t(lang, "generateFhir")}
      </button>

      {fhir && (
        <div className="bg-white rounded-2xl shadow p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="font-semibold text-kiosk-primary">✅ {t(lang, "submitted")}</div>
            <span className="text-xs text-slate-400">{t(lang, "abdmNote")}</span>
          </div>
          <pre className="text-xs bg-slate-900 text-green-200 rounded-lg p-3 overflow-auto max-h-72">
            {JSON.stringify(fhir, null, 2)}
          </pre>
        </div>
      )}

      <button className="tap w-full" onClick={onRestart}>
        {t(lang, "restart")}
      </button>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="p-4">
      <div className="text-xs uppercase tracking-wide text-slate-400 mb-1">{label}</div>
      <div className="text-slate-800">{Array.isArray(value) ? value.join(", ") : value}</div>
    </div>
  );
}
