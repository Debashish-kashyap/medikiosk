import { useMemo, useState } from "react";
import { t } from "../i18n";
import logoMark from "../assets/logo-mark.png";
import logoName from "../assets/logo-name.png";

const defaultQueue = [
  { id: "PT-1045", name: "Aarav Sharma", age: 34, complaint: "Chest pain with shortness of breath", priority: "critical", eta: "08 mins" },
  { id: "PT-2018", name: "Meera Nair", age: 47, complaint: "Hypertension follow-up", priority: "review", eta: "14 mins" },
  { id: "PT-3321", name: "Rohit Verma", age: 62, complaint: "Post-op wound review", priority: "routine", eta: "22 mins" },
  { id: "PT-4412", name: "Sonia Patel", age: 29, complaint: "Migraine and nausea", priority: "review", eta: "31 mins" },
];

export default function DoctorDashboard({ lang, sessionId, summary, redFlags = [], onOpenSummary, onRestart, onBack }) {
  const [role, setRole] = useState("doctor");
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [queue, setQueue] = useState(defaultQueue);
  const [selectedId, setSelectedId] = useState(defaultQueue[0].id);
  const [loginOpen, setLoginOpen] = useState(false);
  const [userId, setUserId] = useState("dr.mehta");
  const [password, setPassword] = useState("");

  const alerts = Math.max(redFlags.length, queue.filter((p) => p.priority === "critical").length);
  const docs = summary?.prior_investigations?.length || 0;
  const chiefComplaint = summary?.chief_complaint || "Not captured yet";
  const hpiPreview = summary?.hpi || "No history recorded yet.";
  const selectedPatient = queue.find((patient) => patient.id === selectedId) || queue[0];
  const currentPatientName = summary?.patient_name || selectedPatient?.name || "Current Patient";

  const triageCards = useMemo(
    () => [
      { label: t(lang, "dashboardCritical"), value: queue.filter((p) => p.priority === "critical").length, accent: "red" },
      { label: t(lang, "dashboardMonitoring"), value: queue.filter((p) => p.priority === "review").length, accent: "amber" },
      { label: t(lang, "dashboardRoutine"), value: queue.filter((p) => p.priority === "routine").length, accent: "slate" },
    ],
    [lang, queue],
  );

  const filteredPatients = queue.filter((patient) => {
    const matchesFilter = filter === "all" ? true : patient.priority === filter;
    const q = search.trim().toLowerCase();
    const matchesSearch = !q || patient.name.toLowerCase().includes(q) || patient.id.toLowerCase().includes(q);
    return matchesFilter && matchesSearch;
  });

  const updatePatientPriority = (patientId, nextPriority) => {
    setQueue((current) =>
      current.map((patient) =>
        patient.id === patientId
          ? {
              ...patient,
              priority: nextPriority,
              status: nextPriority === "critical" ? t(lang, "dashboardPriorityHigh") : nextPriority === "review" ? t(lang, "dashboardPriorityReview") : t(lang, "dashboardPriorityRoutine"),
            }
          : patient,
      ),
    );
  };

  const handleLogin = (event) => {
    event.preventDefault();
    if (!userId.trim() || !password.trim()) return;
    setRole("doctor");
    setLoginOpen(false);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {loginOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-7 shadow-2xl border border-blue-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">{t(lang, "dashboardSigninBadge")}</p>
                <h2 className="mt-2 text-2xl font-extrabold text-slate-900">{t(lang, "dashboardSigninTitle")}</h2>
              </div>
              <button type="button" onClick={() => setLoginOpen(false)} className="text-2xl leading-none text-slate-500">×</button>
            </div>

            <form onSubmit={handleLogin} className="mt-5 space-y-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{t(lang, "dashboardUserId")}</label>
                <input value={userId} onChange={(e) => setUserId(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm focus:bg-white focus:border-blue-600 focus:outline-none" />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{t(lang, "dashboardPassword")}</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm focus:bg-white focus:border-blue-600 focus:outline-none" />
              </div>
              <button type="submit" className="w-full rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 px-4 py-3 text-sm font-bold text-white shadow-md shadow-blue-500/25 transition">
                {t(lang, "dashboardSigninButton")}
              </button>
            </form>
          </div>
        </div>
      )}

      <div className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-[0_4px_25px_rgba(15,23,42,0.05)] border border-blue-100/80 p-5 sm:p-7">
        <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="flex items-center hidden sm:flex">
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
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">{t(lang, "dashboardBadge")}</p>
              <h1 className="mt-1 text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">{t(lang, "dashboardTitle")}</h1>
              <div className="mt-2 inline-flex items-center gap-2 rounded-full bg-blue-50 border border-blue-200 px-3.5 py-1 text-sm font-semibold text-blue-800">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-blue-500" />
                <span>{t(lang, "dashboardCurrentPatient")}: {currentPatientName}</span>
              </div>
              <p className="mt-2 text-sm text-slate-600">{t(lang, "dashboardSubtitle")}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3.5 py-2">
              <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">{t(lang, "dashboardRoleLabel")}</div>
              <div className="mt-1 flex items-center gap-1.5">
                {[
                  { key: "doctor", label: t(lang, "dashboardRoleDoctor") },
                  { key: "nurse", label: t(lang, "dashboardRoleNurse") },
                  { key: "admin", label: t(lang, "dashboardRoleAdmin") },
                ].map((option) => (
                  <button
                    key={option.key}
                    type="button"
                    onClick={() => {
                      setRole(option.key);
                      setLoginOpen(option.key === "doctor");
                    }}
                    className={`rounded-xl px-3 py-1 text-xs font-bold transition ${
                      role === option.key ? "bg-blue-600 text-white shadow-xs" : "bg-white text-slate-700 border border-slate-200"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            {onBack && (
              <button
                type="button"
                onClick={onBack}
                className="rounded-full border border-slate-200 bg-white hover:bg-blue-50 text-slate-700 hover:text-blue-700 px-4 py-2.5 text-sm font-bold shadow-xs transition flex items-center gap-1.5"
                title="Return to patient kiosk"
              >
                <span>←</span>
                <span>{t(lang, "backToKiosk")}</span>
              </button>
            )}
            <button type="button" onClick={onOpenSummary} className="rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 px-5 py-2.5 text-sm font-bold text-white shadow-md shadow-blue-500/20 transition">
              {t(lang, "dashboardOpenSummary")}
            </button>
            <button type="button" onClick={onRestart} className="rounded-full border border-slate-200 bg-white hover:bg-slate-50 px-4 py-2.5 text-sm font-bold text-slate-700 shadow-xs transition">
              {t(lang, "restart")}
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {triageCards.map((card) => (
          <div key={card.label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{card.label}</p>
            <div className={`mt-3 text-3xl font-extrabold ${card.accent === "red" ? "text-red-600" : card.accent === "amber" ? "text-amber-600" : "text-slate-900"}`}>
              {card.value}
            </div>
            <p className="mt-2 text-sm text-slate-600">{t(lang, "dashboardQueue")}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.35fr_0.65fr] gap-5">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">{t(lang, "dashboardWaitingList")}</h2>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={t(lang, "dashboardSearchPlaceholder")}
                className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700 placeholder:text-slate-400 focus:bg-white focus:border-blue-600 focus:ring-1 focus:ring-blue-100 focus:outline-none"
              />
              {[
                { key: "all", label: t(lang, "dashboardFilterAll") },
                { key: "critical", label: t(lang, "dashboardFilterCritical") },
                { key: "review", label: t(lang, "dashboardFilterReview") },
                { key: "routine", label: t(lang, "dashboardFilterRoutine") },
              ].map((option) => (
                <button
                  key={option.key}
                  type="button"
                  onClick={() => setFilter(option.key)}
                  className={`rounded-lg px-2.5 py-1.5 text-xs font-bold border transition ${
                    filter === option.key ? "bg-slate-900 text-white border-slate-900" : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            {filteredPatients.map((patient) => (
              <button
                key={patient.id}
                type="button"
                onClick={() => setSelectedId(patient.id)}
                className={`w-full rounded-2xl border bg-slate-50/80 p-4 text-left transition ${selectedId === patient.id ? "border-blue-600 bg-gradient-to-r from-blue-50/80 to-indigo-50/40 shadow-sm ring-1 ring-blue-500/30" : "border-slate-200 hover:border-slate-300"}`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-base font-bold text-slate-900">{patient.name}</span>
                      <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">{patient.id}</span>
                    </div>
                    <div className="mt-1 text-xs text-slate-600">{patient.age} yrs · {patient.complaint}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase ${
                        patient.priority === "critical"
                          ? "bg-red-100 text-red-700"
                          : patient.priority === "review"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-emerald-100 text-emerald-700"
                      }`}
                    >
                      {patient.priority === "critical" ? t(lang, "dashboardPriorityHigh") : patient.priority === "review" ? t(lang, "dashboardPriorityReview") : t(lang, "dashboardPriorityRoutine")}
                    </span>
                    <span className="text-xs font-semibold text-slate-500">{patient.eta}</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-5">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-lg font-bold text-slate-900">{t(lang, "dashboardPatientDetail")}</h2>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-700">
                {selectedPatient?.id}
              </span>
            </div>

            <div className="mt-4 space-y-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{t(lang, "dashboardName")}</p>
                <p className="mt-1 text-base font-semibold text-slate-800">{selectedPatient?.name}</p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{t(lang, "dashboardComplaint")}</p>
                <p className="mt-1 text-sm text-slate-700">{selectedPatient?.complaint || chiefComplaint}</p>
              </div>

              {summary?.ayush_profile && (
                <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200">
                  <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-emerald-800 mb-2">
                    <span>🌿</span>
                    <span>AYUSH Clinical Cues</span>
                  </div>
                  <div className="text-xs space-y-1 text-slate-800">
                    {summary.ayush_profile.prakriti_cue && (
                      <div><span className="font-semibold text-emerald-950">Prakriti:</span> {summary.ayush_profile.prakriti_cue}</div>
                    )}
                    {summary.ayush_profile.ahara_shakti && (
                      <div><span className="font-semibold text-emerald-950">Agni:</span> {summary.ayush_profile.ahara_shakti}</div>
                    )}
                    {summary.ayush_profile.vikriti_current && summary.ayush_profile.vikriti_current.length > 0 && (
                      <div><span className="font-semibold text-emerald-950">Sleep/Bowel:</span> {summary.ayush_profile.vikriti_current.join(", ")}</div>
                    )}
                    {summary.ayush_profile.satmya && (
                      <div><span className="font-semibold text-emerald-950">Satmya:</span> {summary.ayush_profile.satmya}</div>
                    )}
                  </div>
                </div>
              )}

              <div>
                <label className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{t(lang, "dashboardTriage")}</label>
                <select
                  value={selectedPatient?.priority || "routine"}
                  onChange={(e) => updatePatientPriority(selectedPatient.id, e.target.value)}
                  className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-700 focus:border-blue-600 focus:ring-2 focus:ring-blue-100 focus:outline-none"
                >
                  <option value="critical">{t(lang, "dashboardPriorityHigh")}</option>
                  <option value="review">{t(lang, "dashboardPriorityReview")}</option>
                  <option value="routine">{t(lang, "dashboardPriorityRoutine")}</option>
                </select>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900">{t(lang, "dashboardQuickActions")}</h2>
            <div className="mt-4 space-y-3">
              <button type="button" onClick={onOpenSummary} className="w-full rounded-xl bg-slate-900 hover:bg-slate-800 px-4 py-3 text-left text-sm font-semibold text-white transition">
                {t(lang, "dashboardOpenSummary")}
              </button>
              <button type="button" onClick={onOpenSummary} className="w-full rounded-xl border border-slate-300 bg-white hover:bg-slate-50 px-4 py-3 text-left text-sm font-semibold text-slate-700 transition">
                {t(lang, "dashboardReviewDocs")}
              </button>
              <button type="button" onClick={onRestart} className="w-full rounded-xl border border-red-200 bg-red-50 hover:bg-red-100 px-4 py-3 text-left text-sm font-semibold text-red-700 transition">
                {t(lang, "dashboardResetCase")}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
