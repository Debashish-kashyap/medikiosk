import { useState } from "react";
import { api } from "../api";
import { t } from "../i18n";

// Module C output for the physician: structured, EDITABLE, verifiable — never an
// autonomous diagnosis. Also hosts Module B (document upload) and Module D (FHIR/submit).
export default function SummaryView({ lang, sessionId, summary, redFlags, onRestart }) {
  const [sum, setSum] = useState(summary);
  const [hpi, setHpi] = useState(summary.hpi);
  const [fhir, setFhir] = useState(null);
  const [busy, setBusy] = useState(false);

  async function onUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      await api.uploadDocument(sessionId, file);
      setSum(await api.summary(sessionId)); // refresh timeline + investigations
    } finally {
      setBusy(false);
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
        <div className="flex items-center justify-between mb-3">
          <div className="font-semibold">Prior documents & investigations</div>
          <label className="tap px-4 py-2 cursor-pointer text-sm">
            {busy ? "…" : t(lang, "uploadDoc")}
            <input type="file" className="hidden" onChange={onUpload} disabled={busy} />
          </label>
        </div>
        {docs.length === 0 ? (
          <p className="text-slate-400 text-sm">No documents added yet.</p>
        ) : (
          <ul className="space-y-3">
            {docs.map((d) => (
              <li key={d.doc_id} className="border rounded-xl p-3">
                <div className="text-sm text-slate-500">
                  {d.date} · {d.type} · OCR {Math.round((d.ocr_confidence || 0) * 100)}%
                </div>
                {d.entities?.medications?.length > 0 && (
                  <div className="text-sm mt-1">
                    💊 {d.entities.medications.map((m) => `${m.name} ${m.dose} ${m.frequency}`).join(", ")}
                  </div>
                )}
                {d.entities?.investigations?.length > 0 && (
                  <div className="text-sm mt-1 space-x-2">
                    {d.entities.investigations.map((iv, idx) => (
                      <span
                        key={idx}
                        className={iv.flag === "HIGH" || iv.flag === "LOW" ? "text-kiosk-danger font-semibold" : "text-slate-700"}
                      >
                        {iv.name}: {iv.value}
                        {iv.unit} {iv.flag !== "NORMAL" ? `(${iv.flag})` : ""}
                      </span>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
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
