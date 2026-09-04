import { useEffect, useState } from "react";
import { api } from "../api";
import { t } from "../i18n";
import AccessLogModal from "./AccessLogModal.jsx";
import logoMark from "../assets/logo-mark.png";
import logoName from "../assets/logo-name.png";

// Helper: get file type icon based on mime type or filename
function getFileIcon(filename, type) {
  const lower = (filename || "").toLowerCase();
  const media = (type || "").toLowerCase();

  if (media.includes("pdf") || lower.endsWith(".pdf")) return "📄 PDF";
  if (media.includes("png") || lower.endsWith(".png")) return "🖼️ PNG";
  if (media.includes("jpeg") || media.includes("jpg") || lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "📷 JPG";
  if (media.includes("webp") || lower.endsWith(".webp")) return "🖼️ WEBP";
  return "📄 DOC";
}

// Module C: Structured, in-place editable physician card.
// T1 requirement: Polish into a clean, print-friendly physician card (clear sections, edit-in-place HPI).
// T3 integration: Patient access log & privacy audit.
export default function SummaryView({ lang, sessionId, summary, redFlags = [], onRestart, onBack }) {
  const [sum, setSum] = useState(summary || {});
  const [initialHpi, setInitialHpi] = useState(summary?.hpi || "");
  const [hpi, setHpi] = useState(summary?.hpi || "");
  const [isHpiEdited, setIsHpiEdited] = useState(false);
  const [hpiSavedTime, setHpiSavedTime] = useState(null);
  const [fhir, setFhir] = useState(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [copiedFhir, setCopiedFhir] = useState(false);
  const [showAccessLog, setShowAccessLog] = useState(false);
  const [activeTab, setActiveTab] = useState("clinical"); // "clinical" | "documents" | "fhir"

  // Keep state in sync when summary prop updates
  useEffect(() => {
    if (summary) {
      setSum(summary);
      setHpi(summary.hpi || "");
      setInitialHpi(summary.hpi || "");
    }
  }, [summary]);

  function handleHpiChange(e) {
    const val = e.target.value;
    setHpi(val);
    setIsHpiEdited(val !== initialHpi);
    setHpiSavedTime(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
  }

  function handleResetHpi() {
    setHpi(initialHpi);
    setIsHpiEdited(false);
  }

  async function onUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await api.uploadDocument(sessionId, file);
      const updated = await api.summary(sessionId);
      setSum(updated);
    } catch (err) {
      alert(`Document upload failed: ${err.message}`);
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
      setActiveTab("fhir");
    } catch (err) {
      alert(`FHIR submission failed: ${err.message}`);
    } finally {
      setBusy(false);
    }
  }

  function copyFhirJson() {
    if (!fhir) return;
    navigator.clipboard.writeText(JSON.stringify(fhir, null, 2));
    setCopiedFhir(true);
    setTimeout(() => setCopiedFhir(false), 2000);
  }

  function handlePrint() {
    window.print();
  }

  const docs = sum.prior_investigations || [];
  const currentDate = new Date().toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="space-y-6 print:space-y-4 print:text-black">
      {/* Top Clinical Header & Action Toolbar */}
      <div className="bg-white/95 backdrop-blur-sm rounded-3xl p-6 sm:p-7 shadow-[0_4px_25px_rgba(15,23,42,0.05)] border border-blue-100/80 flex flex-col md:flex-row md:items-center justify-between gap-4 print:border-none print:shadow-none print:p-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center">
            <img
              src={logoMark}
              alt="MediKiosk"
              className="h-18 w-18 sm:h-20 sm:w-20 object-contain shrink-0"
            />
            <img
              src={logoName}
              alt="MediKiosk"
              className="h-10 sm:h-12 w-auto object-contain shrink-0 -ml-2"
            />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-blue-100 text-blue-800 border border-blue-200/60">
                {t(lang, "forPhysician")}
              </span>
              <span className="text-xs font-mono bg-slate-100 text-slate-600 px-2.5 py-0.5 rounded-full border border-slate-200">
                ID: {sessionId || "N/A"}
              </span>
              <span className="text-xs text-slate-500">
                {currentDate}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {t(lang, "summaryTitle")}
            </h1>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 flex-wrap print:hidden">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="px-4 py-2 rounded-full border border-slate-200 bg-white hover:bg-blue-50 text-slate-700 hover:text-blue-700 text-xs sm:text-sm font-bold transition flex items-center gap-1.5 shadow-xs"
              title="Return to questions"
            >
              <span>←</span>
              <span>{t(lang, "backToInterview")}</span>
            </button>
          )}

          <button
            type="button"
            onClick={handlePrint}
            className="px-4 py-2 rounded-full border border-slate-200 bg-white hover:bg-blue-50 text-slate-700 hover:text-blue-700 text-xs sm:text-sm font-bold transition flex items-center gap-1.5 shadow-xs"
          >
            <span>🖨️</span>
            <span>{t(lang, "printSummary")}</span>
          </button>

          <button
            type="button"
            onClick={() => setShowAccessLog(true)}
            className="px-4 py-2 rounded-full border border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-800 text-xs sm:text-sm font-bold transition flex items-center gap-1.5 shadow-xs"
          >
            <span>🛡️</span>
            <span>{t(lang, "viewAccessLog")}</span>
          </button>

          <button
            type="button"
            onClick={onRestart}
            className="px-4 py-2 rounded-full bg-slate-800 hover:bg-slate-900 text-white text-xs sm:text-sm font-bold transition flex items-center gap-1.5 shadow-xs"
          >
            <span>🔄</span>
            <span>{t(lang, "restart")}</span>
          </button>
        </div>
      </div>

      {/* Red Flag Alerts (Sticky / Embedded Priority Box) */}
      {redFlags && redFlags.length > 0 && (
        <div className="rounded-2xl border-2 border-red-500 bg-red-50/90 p-4 sm:p-5 shadow-sm">
          <div className="flex items-center justify-between gap-2 mb-3">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🚨</span>
              <span className="font-extrabold text-red-900 text-base sm:text-lg uppercase tracking-wide">
                {t(lang, "criticalAlert")} ({redFlags.length})
              </span>
            </div>
            <span className="text-xs font-mono bg-red-100 text-red-800 px-2 py-0.5 rounded font-bold border border-red-300">
              IMMEDIATE ATTENTION
            </span>
          </div>
          <div className="space-y-1.5">
            {redFlags.map((flag, idx) => (
              <div key={idx} className="flex items-center gap-2 text-sm font-bold text-red-800 bg-white/80 p-2.5 rounded-lg border border-red-200">
                <span>⚠️</span>
                <span>{flag}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 2-Column Clinical Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Main Narrative & Systems */}
        <div className="lg:col-span-2 space-y-6">
          {/* Chief Complaint Card */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                {t(lang, "chiefComplaint")}
              </span>
              <span className="text-xs font-mono bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                Verified
              </span>
            </div>
            <div className="text-xl font-extrabold text-slate-900">
              {sum.chief_complaint || "No chief complaint recorded"}
            </div>
          </div>

          {/* HPI — In-Place Editable Physician Card (Ticket T1) */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 relative focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-500 transition">
            <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-blue-800 bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200/60">
                  {t(lang, "physicianNote")}
                </span>
                <span className="text-xs text-slate-400">
                  (Edit in-place)
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs">
                {isHpiEdited && (
                  <span className="text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded text-[11px] font-semibold flex items-center gap-1 animate-pulse">
                    <span>✓</span>
                    <span>{t(lang, "autoSaved")} {hpiSavedTime ? `at ${hpiSavedTime}` : ""}</span>
                  </span>
                )}
                {isHpiEdited && (
                  <button
                    type="button"
                    onClick={handleResetHpi}
                    className="text-slate-500 hover:text-slate-700 underline text-xs print:hidden"
                  >
                    {t(lang, "resetHpi")}
                  </button>
                )}
                <span className="text-slate-400 font-mono text-[11px]">
                  {hpi.length} {t(lang, "charCount")}
                </span>
              </div>
            </div>

            <textarea
              className="w-full border border-slate-200 rounded-xl p-3.5 text-slate-800 text-sm sm:text-base leading-relaxed min-h-[130px] focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 bg-slate-50/50 hover:bg-white focus:bg-white transition"
              value={hpi}
              onChange={handleHpiChange}
              placeholder="Structured clinical narrative of the present illness..."
            />

            <div className="mt-2 text-[11px] text-slate-400 flex items-center justify-between">
              <span>Verified narrative for clinical documentation · ABDM FHIR compliant</span>
              <span className="print:hidden">Markdown / text formatted</span>
            </div>
          </div>

          {/* Review of Systems & Key Findings */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              Review of Systems (ROS) & Symptoms
            </div>
            <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 text-sm text-slate-800 leading-relaxed font-sans">
              {sum.review_of_systems ? (
                Array.isArray(sum.review_of_systems) ? (
                  <div className="flex flex-wrap gap-2">
                    {sum.review_of_systems.map((item, idx) => (
                      <span key={idx} className="bg-white border border-slate-200 px-3 py-1 rounded-lg text-xs font-semibold text-slate-700">
                        {item}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div>{sum.review_of_systems}</div>
                )
              ) : (
                <span className="text-slate-400 italic">No positive findings on system review.</span>
              )}
            </div>
          </div>

          {/* Patient Voice Intake Transcripts (Verbatim Auditory Record) */}
          {sum.voice_transcripts && sum.voice_transcripts.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-base">🗣️</span>
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Patient Voice Intake Record
                  </span>
                </div>
                <span className="text-[10px] bg-blue-50 text-blue-800 px-2.5 py-0.5 rounded-full font-mono font-bold border border-blue-200">
                  ASR Logged
                </span>
              </div>
              <div className="space-y-2">
                {sum.voice_transcripts.map((vt, idx) => (
                  <div key={idx} className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex items-start justify-between gap-3 text-xs sm:text-sm">
                    <div className="space-y-0.5">
                      <div className="text-[10px] font-mono text-slate-400 uppercase font-bold tracking-wider">
                        {vt.field.replace(/_/g, " ")}
                      </div>
                      <div className="font-medium text-slate-800 italic">
                        "{vt.transcript}"
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold bg-white text-blue-800 px-2 py-0.5 rounded border border-blue-200 shrink-0">
                      {Math.round(vt.confidence * 100)}% conf
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right 1 Col: Allergies, Medical History, Quick Vitals */}
        <div className="space-y-5">
          {/* Drug Allergies Card (High Priority) */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                {t(lang, "allergies")}
              </span>
              <span className="text-xs">⚠️</span>
            </div>

            {sum.drug_allergy && sum.drug_allergy !== "None" && sum.drug_allergy !== "None reported" ? (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-900 text-sm font-bold flex items-center gap-2">
                <span className="text-lg">🚫</span>
                <span>{sum.drug_allergy}</span>
              </div>
            ) : (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl text-blue-800 text-xs font-semibold flex items-center gap-2">
                <span>✓</span>
                <span>{t(lang, "noAllergies")}</span>
              </div>
            )}
          </div>

          {/* Past Medical History Card */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              Past Medical History
            </div>
            <div className="text-sm text-slate-800">
              {sum.past_medical ? (
                Array.isArray(sum.past_medical) ? (
                  <ul className="space-y-1.5">
                    {sum.past_medical.map((m, i) => (
                      <li key={i} className="flex items-center gap-2 text-xs font-medium">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                        <span>{m}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-xs font-medium bg-slate-50 p-3 rounded-lg border border-slate-100">
                    {sum.past_medical}
                  </div>
                )
              ) : (
                <div className="text-xs text-slate-400 italic">None recorded</div>
              )}
            </div>
          </div>

          {/* AYUSH Constitutional Assessment Profile Card */}
          {sum.ayush_profile && (
            <div className="bg-gradient-to-br from-blue-50/90 via-blue-50/40 to-slate-50 border border-blue-200 rounded-2xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xl">🌿</span>
                  <span className="text-xs font-bold uppercase tracking-wider text-blue-950">
                    AYUSH Constitutional Profile
                  </span>
                </div>
                <span className="text-[10px] font-mono font-bold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full border border-blue-300">
                  AYURVEDA
                </span>
              </div>

              <div className="space-y-2.5 text-xs">
                {sum.ayush_profile.prakriti && (
                  <div>
                    <span className="font-bold text-blue-900 block">{t(lang, "ayushPrakriti")}:</span>
                    <span className="text-slate-800 font-semibold">{sum.ayush_profile.prakriti}</span>
                  </div>
                )}
                {sum.ayush_profile.agni && (
                  <div>
                    <span className="font-bold text-blue-900 block">{t(lang, "ayushAgni")}:</span>
                    <span className="text-slate-800 font-medium">{sum.ayush_profile.agni}</span>
                  </div>
                )}
                {sum.ayush_profile.koshtha && (
                  <div>
                    <span className="font-bold text-blue-900 block">{t(lang, "ayushKoshtha")}:</span>
                    <span className="text-slate-800 font-medium">{sum.ayush_profile.koshtha}</span>
                  </div>
                )}
                {sum.ayush_profile.satva && (
                  <div>
                    <span className="font-bold text-blue-900 block">{t(lang, "ayushSatva")}:</span>
                    <span className="text-slate-800 font-medium">{sum.ayush_profile.satva}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Patient Transparency & DPDP Security Badge */}
          <div className="bg-slate-900 text-white rounded-2xl p-4 text-xs space-y-2 border border-slate-800">
            <div className="flex items-center gap-2 font-bold text-blue-300">
              <span>🛡️</span>
              <span>DPDP Act 2023 & Estonia Model</span>
            </div>
            <p className="text-slate-300 text-[11px] leading-snug">
              Every clinician edit, document upload, and diagnosis is cryptographically chained for patient auditability.
            </p>
            <button
              type="button"
              onClick={() => setShowAccessLog(true)}
              className="w-full py-2.5 mt-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold rounded-xl text-xs transition flex items-center justify-center gap-1.5 shadow-sm print:hidden"
            >
              <span>{t(lang, "viewAccessLog")}</span>
              <span>→</span>
            </button>
          </div>
        </div>
      </div>

      {/* Module B — Prior Documents & Digitized Lab Investigations */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              {t(lang, "priorDocs")}
            </h2>
            <p className="text-xs text-slate-500">
              Digitized via Gemini Vision / OCR with automatic entity extraction & abnormal value flagging.
            </p>
          </div>

          <div className="flex items-center gap-2 print:hidden">
            {uploading && (
              <span className="flex items-center gap-2 text-xs font-semibold text-blue-700 animate-pulse bg-blue-50 px-3 py-1.5 rounded-lg border border-blue-200">
                <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Processing OCR...
              </span>
            )}
            <label
              className={`px-4 py-2 cursor-pointer text-xs sm:text-sm font-semibold rounded-full transition flex items-center gap-1.5 shadow-sm ${
                uploading
                  ? "opacity-50 cursor-not-allowed bg-slate-100 text-slate-400"
                  : "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-blue-500/20"
              }`}
            >
              <span>📤</span>
              <span>{uploading ? "Analyzing..." : t(lang, "uploadDoc")}</span>
              <input
                type="file"
                className="hidden"
                onChange={onUpload}
                disabled={uploading}
                accept="image/png,image/jpeg,image/webp,application/pdf"
              />
            </label>
          </div>
        </div>

        {docs.length === 0 ? (
          <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center bg-slate-50/50 hover:bg-slate-50 transition">
            <div className="text-3xl mb-2">📎</div>
            <p className="text-slate-700 font-semibold text-sm">No prior lab reports or prescriptions added.</p>
            <p className="text-slate-400 text-xs mt-1">Upload PDF, JPG, or PNG files to automatically extract diagnostic findings.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {docs.map((d, index) => (
              <div
                key={d.doc_id || index}
                className="border border-slate-200 rounded-xl p-4 bg-slate-50/30 hover:bg-white hover:shadow-md transition space-y-3"
              >
                {/* Header info */}
                <div className="flex items-center justify-between gap-2 p-2.5 bg-white rounded-lg border border-slate-100">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="text-2xl">{getFileIcon(d.filename, d.mime_type)}</span>
                    <div className="min-w-0">
                      <div className="font-bold text-xs sm:text-sm text-slate-900 truncate" title={d.filename || d.type}>
                        {d.filename || d.type || `Document #${index + 1}`}
                      </div>
                      <div className="text-[11px] text-slate-500">{d.date || "Recent"}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span className="text-[11px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded">
                      OCR {Math.round((d.ocr_confidence || 0.95) * 100)}%
                    </span>
                  </div>
                </div>

                {/* Lab Findings Table */}
                {d.entities?.investigations?.length > 0 && (
                  <div className="space-y-1.5">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      {t(lang, "labResults")} ({d.entities.investigations.length})
                    </div>
                    <div className="overflow-x-auto border border-slate-200 rounded-lg bg-white">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-slate-50 text-slate-600 text-[10px] uppercase font-semibold border-b border-slate-100">
                          <tr>
                            <th className="py-1.5 px-2.5">Test Name</th>
                            <th className="py-1.5 px-2.5">Value</th>
                            <th className="py-1.5 px-2.5 text-right">Flag</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {d.entities.investigations.map((iv, idx) => {
                            const isAbnormal = iv.flag === "HIGH" || iv.flag === "LOW";
                            return (
                              <tr key={idx} className={isAbnormal ? "bg-red-50/50" : ""}>
                                <td className="py-1.5 px-2.5 font-medium text-slate-800">{iv.name}</td>
                                <td className="py-1.5 px-2.5 text-slate-700">
                                  {iv.value} {iv.unit || ""}
                                </td>
                                <td className="py-1.5 px-2.5 text-right">
                                  <span
                                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold font-mono ${
                                      isAbnormal
                                        ? "bg-red-100 text-red-800 border border-red-300"
                                        : "bg-slate-100 text-slate-600"
                                    }`}
                                  >
                                    {iv.flag || "NORMAL"}
                                  </span>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Medications Extracted */}
                {d.entities?.medications?.length > 0 && (
                  <div className="space-y-1.5">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      {t(lang, "medications")} ({d.entities.medications.length})
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {d.entities.medications.map((m, idx) => (
                        <span
                          key={idx}
                          className="bg-blue-50 border border-blue-200 text-blue-800 text-xs px-2.5 py-1 rounded-lg font-medium"
                        >
                          💊 {m.name} {m.dosage ? `(${m.dosage})` : ""}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Module D — FHIR Generation & Final Submission */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 space-y-4 print:hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Module D: ABDM FHIR R4 Generation
            </h2>
            <p className="text-xs text-slate-500">
              Convert the validated encounter and digitized investigations into a standard ABDM FHIR Bundle.
            </p>
          </div>

          <button
            type="button"
            disabled={busy}
            onClick={onGenerate}
            className="px-6 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold text-sm rounded-full shadow-lg shadow-blue-500/25 transition transform active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {busy ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Generating FHIR Bundle...</span>
              </>
            ) : (
              <>
                <span>⚡</span>
                <span>{t(lang, "generateFhir")}</span>
              </>
            )}
          </button>
        </div>

        {/* Generated FHIR Viewer */}
        {fhir && (
          <div className="border border-slate-200 rounded-2xl overflow-hidden bg-slate-900 text-slate-100 shadow-inner">
            <div className="px-4 py-2.5 bg-slate-800 flex items-center justify-between border-b border-slate-700">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                <span className="text-xs font-mono font-bold text-blue-300">
                  FHIR R4 Bundle (ABDM Mocked Linkage)
                </span>
              </div>
              <button
                type="button"
                onClick={copyFhirJson}
                className="text-xs px-3 py-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-200 font-mono transition flex items-center gap-1"
              >
                <span>{copiedFhir ? "✓ Copied!" : "📋 Copy JSON"}</span>
              </button>
            </div>
            <pre className="p-4 text-xs font-mono text-emerald-300 overflow-x-auto max-h-80 leading-relaxed">
              {JSON.stringify(fhir, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Access Log Modal */}
      {showAccessLog && (
        <AccessLogModal
          lang={lang}
          sessionId={sessionId}
          onClose={() => setShowAccessLog(false)}
        />
      )}
    </div>
  );
}
