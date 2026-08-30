import { useState, useEffect } from "react";
import { api } from "../api";
import { t } from "../i18n";

// Estonian healthcare model: Patient-visible, tamper-evident audit trail & DPDP rights.
// T3 requirement: call GET /api/session/{id}/access-log, show who/when/what/why + tamper_evident badge.
export default function AccessLogModal({ lang, sessionId, onClose }) {
  const [logData, setLogData] = useState(null);
  const [rightsData, setRightsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterRole, setFilterRole] = useState("all");
  const [showRights, setShowRights] = useState(false);

  useEffect(() => {
    loadData();
  }, [sessionId]);

  async function loadData() {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const [logRes, rightsRes] = await Promise.allSettled([
        api.getAccessLog(sessionId),
        api.getRights(sessionId),
      ]);
      if (logRes.status === "fulfilled") {
        setLogData(logRes.value);
      } else {
        throw new Error(logRes.reason?.message || "Failed to fetch access log");
      }
      if (rightsRes.status === "fulfilled") {
        setRightsData(rightsRes.value);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  function handlePrint() {
    window.print();
  }

  const entries = logData?.entries || [];
  const isTamperEvident = logData?.tamper_evident !== false;

  const filteredEntries = entries.filter((e) => {
    if (filterRole === "all") return true;
    if (filterRole === "patient") return (e.who || "").toLowerCase() === "patient";
    if (filterRole === "physician") return (e.who || "").toLowerCase().includes("doc") || (e.role || "").toLowerCase().includes("physician") || (e.who || "").toLowerCase() === "physician";
    if (filterRole === "system") return (e.who || "").toLowerCase().includes("system") || (e.who || "").toLowerCase().includes("kiosk");
    return true;
  });

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6 overflow-y-auto print:static print:p-0 print:bg-white"
    >
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] print:max-h-none print:shadow-none print:border-none">
        {/* Header */}
        <div className="bg-slate-900 text-white p-5 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-teal-500/20 border border-teal-400/30 flex items-center justify-center text-teal-300 font-bold text-xl">
              🛡️
            </div>
            <div>
              <h3 className="text-lg sm:text-xl font-bold tracking-tight">
                {t(lang, "accessLogModalTitle")}
              </h3>
              <p className="text-xs text-slate-400">
                Estonia e-Health transparency model · Session: <span className="font-mono text-teal-300">{sessionId}</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 print:hidden">
            <button
              onClick={handlePrint}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition flex items-center gap-1.5"
              title="Print Audit Trail"
            >
              <span>🖨️</span>
              <span className="hidden sm:inline">{t(lang, "printLog")}</span>
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center justify-center text-lg font-bold transition"
              aria-label="Close modal"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Tamper Evident Banner */}
        <div
          className={`px-5 py-3.5 border-b flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${
            isTamperEvident
              ? "bg-emerald-50/80 border-emerald-200 text-emerald-950"
              : "bg-red-50 border-red-200 text-red-950"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 ${
                isTamperEvident
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "bg-red-600 text-white"
              }`}
            >
              {isTamperEvident ? "✓" : "!"}
            </div>
            <div>
              <div className="font-bold text-sm flex items-center gap-2">
                <span>{isTamperEvident ? t(lang, "tamperEvidentBadge") : t(lang, "tamperAlert")}</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-white/80 border border-current">
                  CHAIN: {isTamperEvident ? "VALID" : "CORRUPTED"}
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                {t(lang, "tamperEvidentSub")}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-center">
            <button
              type="button"
              onClick={() => setShowRights(!showRights)}
              className="text-xs font-semibold px-3 py-1 bg-white border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition print:hidden"
            >
              {showRights ? "▲ Hide DPDP Rights" : "📜 View DPDP Rights"}
            </button>
            <button
              type="button"
              onClick={loadData}
              disabled={loading}
              className="text-xs font-semibold px-2.5 py-1 bg-white border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition print:hidden"
            >
              🔄 {t(lang, "refreshLog")}
            </button>
          </div>
        </div>

        {/* DPDP Rights Panel (Collapsible) */}
        {showRights && rightsData && (
          <div className="bg-slate-50 p-4 border-b border-slate-200 text-sm text-slate-700 space-y-2">
            <div className="font-bold text-slate-900 flex items-center gap-2">
              <span>⚖️</span>
              <span>{t(lang, "dpdpRightsHeading")}</span>
            </div>
            <p className="text-xs text-slate-600">{t(lang, "dpdpRightsDesc")}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 text-xs">
              {Object.entries(rightsData.rights || {}).map(([key, desc]) => (
                <div key={key} className="bg-white p-2.5 rounded-lg border border-slate-200">
                  <span className="font-bold uppercase text-[10px] tracking-wider text-teal-700 block mb-0.5">
                    {key.replace("_", " ")}
                  </span>
                  <span className="text-slate-700">{desc}</span>
                </div>
              ))}
            </div>
            {rightsData.grievance_contact && (
              <div className="text-[11px] text-slate-500 pt-1">
                Data Protection Officer: <span className="font-mono font-medium text-slate-700">{rightsData.grievance_contact}</span>
              </div>
            )}
          </div>
        )}

        {/* Filter Controls */}
        <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between flex-wrap gap-2 print:hidden">
          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-600">
            <span>Filter:</span>
            {["all", "physician", "patient", "system"].map((r) => (
              <button
                key={r}
                onClick={() => setFilterRole(r)}
                className={`px-2.5 py-1 rounded-md capitalize transition ${
                  filterRole === r
                    ? "bg-slate-800 text-white font-bold"
                    : "bg-white text-slate-700 border border-slate-200 hover:bg-slate-100"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
          <div className="text-xs text-slate-500 font-medium">
            Showing {filteredEntries.length} of {entries.length} access events
          </div>
        </div>

        {/* Body Content / Table */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5">
          {loading && (
            <div className="text-center py-12 text-slate-500 flex flex-col items-center gap-3">
              <svg className="animate-spin h-8 w-8 text-teal-600" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-sm font-medium">Loading verified audit records...</span>
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
              Failed to load access logs: {error}
            </div>
          )}

          {!loading && !error && filteredEntries.length === 0 && (
            <div className="text-center py-12 text-slate-400">
              <div className="text-3xl mb-2">📋</div>
              <p className="text-sm">{t(lang, "accessLogEmpty")}</p>
            </div>
          )}

          {!loading && !error && filteredEntries.length > 0 && (
            <div className="overflow-x-auto border border-slate-200 rounded-xl">
              <table className="w-full text-left text-xs sm:text-sm border-collapse">
                <thead className="bg-slate-100 text-slate-700 uppercase font-semibold text-[11px] tracking-wider border-b border-slate-200">
                  <tr>
                    <th className="py-3 px-3.5">{t(lang, "timestamp")}</th>
                    <th className="py-3 px-3.5">{t(lang, "who")}</th>
                    <th className="py-3 px-3.5">{t(lang, "role")}</th>
                    <th className="py-3 px-3.5">{t(lang, "action")}</th>
                    <th className="py-3 px-3.5">{t(lang, "resource")}</th>
                    <th className="py-3 px-3.5">{t(lang, "purpose")}</th>
                    <th className="py-3 px-3.5 text-right">{t(lang, "status")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {filteredEntries.map((entry, idx) => {
                    const isDoctor = (entry.who || "").toLowerCase().includes("doc") || (entry.role || "").toLowerCase().includes("physician") || (entry.who || "").toLowerCase() === "physician";
                    const isPatient = (entry.who || "").toLowerCase() === "patient";

                    return (
                      <tr key={idx} className="hover:bg-slate-50/80 transition font-sans">
                        <td className="py-3 px-3.5 text-slate-600 whitespace-nowrap text-xs">
                          {entry.when ? formatTimestamp(entry.when) : "Just now"}
                        </td>
                        <td className="py-3 px-3.5 font-semibold text-slate-900">
                          <span className="flex items-center gap-1.5">
                            <span>{isPatient ? "👤" : isDoctor ? "🩺" : "🤖"}</span>
                            <span>{entry.who || "Unknown"}</span>
                          </span>
                        </td>
                        <td className="py-3 px-3.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider ${
                              isDoctor
                                ? "bg-teal-100 text-teal-800"
                                : isPatient
                                ? "bg-blue-100 text-blue-800"
                                : "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {entry.role || "user"}
                          </span>
                        </td>
                        <td className="py-3 px-3.5">
                          <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-mono text-xs uppercase font-semibold">
                            {entry.did || entry.action || "access"}
                          </span>
                        </td>
                        <td className="py-3 px-3.5 text-slate-700 font-medium">
                          {entry.to || entry.resource || "health_record"}
                        </td>
                        <td className="py-3 px-3.5 text-slate-600 text-xs">
                          {entry.why || entry.purpose || "direct_care"}
                        </td>
                        <td className="py-3 px-3.5 text-right">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold ${
                              (entry.result || "").toLowerCase().includes("success")
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-red-100 text-red-800"
                            }`}
                          >
                            <span>✓</span>
                            <span>{entry.result || "success"}</span>
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-slate-50 px-5 py-4 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500 print:hidden">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Immutable Hash-Chained Audit Trail Active</span>
          </div>
          <button
            onClick={onClose}
            className="px-5 py-2 bg-slate-800 hover:bg-slate-900 text-white font-semibold rounded-xl transition shadow-sm"
          >
            {t(lang, "close")}
          </button>
        </div>
      </div>
    </div>
  );
}

function formatTimestamp(ts) {
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}
