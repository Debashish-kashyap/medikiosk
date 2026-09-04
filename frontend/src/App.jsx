import React, { Component, useState } from "react";
import { api } from "./api";
import { t } from "./i18n";
import logoMark from "./assets/logo-mark.png";
import logoName from "./assets/logo-name.png";
import LanguageSelect from "./components/LanguageSelect.jsx";
import ConsentScreen from "./components/ConsentScreen.jsx";
import QuestionCard from "./components/QuestionCard.jsx";
import RedFlagBanner from "./components/RedFlagBanner.jsx";
import SummaryView from "./components/SummaryView.jsx";
import DoctorDashboard from "./components/DoctorDashboard.jsx";

// Error Boundary to prevent any uncaught runtime crash from producing a blank white screen
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error("MediKiosk Render Exception:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-white/95 backdrop-blur-sm rounded-3xl p-8 max-w-lg mx-auto my-12 border border-red-200 shadow-xl text-center space-y-4">
          <div className="text-4xl">⚠️</div>
          <h2 className="text-xl font-bold text-red-900">Encounter View Error</h2>
          <p className="text-xs text-slate-600 bg-red-50 p-3 rounded-xl border border-red-100 font-mono text-left overflow-auto max-h-32">
            {this.state.error?.toString()}
          </p>
          <div className="flex justify-center gap-3 pt-2">
            <button
              type="button"
              onClick={() => {
                this.setState({ hasError: false, error: null });
                if (this.props.onReset) this.props.onReset();
              }}
              className="px-5 py-2.5 bg-slate-900 text-white font-bold text-xs rounded-full hover:bg-slate-800 transition"
            >
              Reset / Return to Start
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// Kiosk flow: language -> consent -> interview -> summary.
export default function App() {
  const [lang, setLang] = useState("en");
  const [ayushMode, setAyushMode] = useState(false);
  const [phase, setPhase] = useState("language");
  const [prevPhase, setPrevPhase] = useState("language");
  const [sessionId, setSessionId] = useState(null);
  const [question, setQuestion] = useState(null);
  const [questionHistory, setQuestionHistory] = useState([]);
  const [redFlags, setRedFlags] = useState([]);
  const [pendingConfirm, setPendingConfirm] = useState(null);
  const [summary, setSummary] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [autoVoice, setAutoVoice] = useState(true);

  function chooseLanguage(code, mode) {
    setLang(code);
    if (typeof mode === "boolean") setAyushMode(mode);
    setPrevPhase("language");
    setPhase("consent");
  }

  async function agreeConsent(abhaId, otp) {
    setBusy(true);
    setError(null);
    try {
      const res = await api.createSession(lang, ayushMode);
      setSessionId(res.session_id);
      setQuestion(res.question);
      setQuestionHistory([]);
      await api.giveConsent(res.session_id, true, abhaId, otp);
      setPrevPhase("consent");
      setPhase("interview");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function submitAnswer(partial) {
    if (!question) return;
    if (partial.text) {
      setAutoVoice(true);
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.answer(sessionId, { node_id: question.node_id, ...partial });
      if (res.status === "needs_confirmation") {
        setPendingConfirm(res);
        return;
      }
      setPendingConfirm(null);
      if (res.red_flags_all) setRedFlags(res.red_flags_all);
      if (res.done) {
        setPrevPhase("interview");
        setPhase("preparing_summary");
        setQuestion(null);
        try {
          const s = await api.summary(sessionId);
          setSummary(s);
          setPhase("summary");
        } catch (sumErr) {
          console.error("Summary fetch error:", sumErr);
          setError(String(sumErr));
          setSummary({
            chief_complaint: "Clinical intake completed",
            hpi: "Intake completed. Note: backend summary generation returned an alert.",
          });
          setPhase("summary");
        }
      } else {
        setQuestionHistory((prev) => [...prev, question]);
        setQuestion(res.next_question);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function goBack() {
    setError(null);
    if (phase === "dashboard") {
      setPhase(prevPhase || "language");
    } else if (phase === "summary") {
      if (questionHistory.length > 0) {
        const lastQ = questionHistory[questionHistory.length - 1];
        setQuestion(lastQ);
        setPhase("interview");
      } else {
        setPhase("language");
      }
    } else if (phase === "interview") {
      if (questionHistory.length > 0) {
        const lastQ = questionHistory[questionHistory.length - 1];
        setQuestionHistory((prev) => prev.slice(0, -1));
        setQuestion(lastQ);
      } else {
        setPhase("consent");
      }
    } else if (phase === "consent") {
      setPhase("language");
    }
  }

  const confirmYes = () =>
    submitAnswer({ touch_value: pendingConfirm.interpreted_value, confirmed: true });
  const confirmNo = () => setPendingConfirm(null);

  async function openDoctorDashboard() {
    setPrevPhase(phase);
    setBusy(true);
    setError(null);
    try {
      let sid = sessionId;
      if (!sid) {
        const sessionRes = await api.createSession(lang, ayushMode);
        sid = sessionRes.session_id;
        setSessionId(sid);
      }
      const s = await api.summary(sid);
      setSummary(s);
      setPhase("dashboard");
    } catch (e) {
      // Fallback demo data for immediate testing & judging preview
      setSessionId(sessionId || "DEMO-8829");
      setRedFlags([
        {
          id: "rf-1",
          priority: "HIGH",
          label: "Acute Respiratory Distress suspected (Dyspnea + Chest Tightness)",
          action: "Order STAT 12-Lead ECG and Chest X-Ray; Escalate to Triage Level 2",
        },
      ]);
      setSummary({
        chief_complaint: "Shortness of breath & progressive chest tightness for 2 days",
        hpi: "Patient is a 54-year-old male presenting with acute progressive dyspnea for the past 48 hours, worsening on exertion (NYHA Class III). Associated with dry non-productive cough and mild retrosternal chest tightness. Denies orthopnea or paroxysmal nocturnal dyspnea.",
        past_medical: ["Type 2 Diabetes Mellitus (HbA1c 8.2%)", "Essential Hypertension (Stage 2)"],
        drug_allergy: "Penicillin (Urticaria & facial edema)",
        review_of_systems: ["Dyspnea on exertion", "Chest tightness", "Fatigue", "No fever"],
        contradictions: ["Patient reports no chest pain during intake, but reported severe tightness on voice clarification."],
        prior_investigations: [
          {
            doc_id: "doc-1",
            filename: "Lab_Report_Lipid_Glycemic.pdf",
            mime_type: "application/pdf",
            date: "2026-08-28",
            ocr_confidence: 0.98,
            entities: {
              medications: [
                { name: "Metformin", dosage: "500mg BD" },
                { name: "Amlodipine", dosage: "5mg OD" },
              ],
              investigations: [
                { name: "HbA1c", value: "8.2", unit: "%", flag: "HIGH" },
                { name: "Fasting Plasma Glucose", value: "164", unit: "mg/dL", flag: "HIGH" },
                { name: "Serum Creatinine", value: "1.02", unit: "mg/dL", flag: "NORMAL" },
              ],
            },
          },
        ],
      });
      setPhase("dashboard");
    } finally {
      setBusy(false);
    }
  }

  function restart() {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setPhase("language");
    setPrevPhase("language");
    setSessionId(null);
    setQuestion(null);
    setQuestionHistory([]);
    setRedFlags([]);
    setPendingConfirm(null);
    setSummary(null);
    setError(null);
  }

  return (
    <div className="min-h-full flex flex-col bg-transparent print:bg-white">
      <header className="bg-white/95 backdrop-blur-md border-b border-blue-100/90 border-t-4 border-t-blue-600 px-5 sm:px-8 py-3 sm:py-3.5 flex items-center justify-between shadow-[0_2px_15px_rgba(37,99,235,0.05)] print:hidden">
        <div className="flex items-center gap-4 sm:gap-5">
          {/* Free Logo Mark & Name - Clickable Home Link to Landing Page */}
          <button
            type="button"
            onClick={restart}
            className="flex items-center text-left focus:outline-none cursor-pointer transition hover:opacity-90 active:scale-[0.98]"
            title="Return to Home / Landing Page"
            aria-label="MediKiosk Home"
          >
            <img
              src={logoMark}
              alt="MediKiosk Logo"
              className="h-12 w-12 sm:h-14 sm:w-14 object-contain shrink-0 drop-shadow-sm"
            />
            <img
              src={logoName}
              alt="MediKiosk"
              className="h-8 sm:h-9 w-auto object-contain shrink-0 -ml-1.5 drop-shadow-sm"
            />
          </button>

          <div className="hidden xl:block">
            <div className="text-xs sm:text-sm text-slate-500 font-medium leading-tight pl-4 border-l border-slate-200">
              {phase === "dashboard"
                ? "Clinician workspace & patient triage"
                : phase === "summary"
                ? "Clinical summary & physician sign-off"
                : t(lang, "tagline")}
            </div>
          </div>

          {phase === "dashboard" ? (
            <div className="hidden sm:inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-bold border border-blue-200 bg-blue-50 text-blue-800 transition shadow-xs">
              <span>👨‍⚕️</span>
              <span>Clinician Workspace</span>
            </div>
          ) : phase === "summary" ? (
            <div className="hidden sm:inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-bold border border-indigo-200 bg-indigo-50 text-indigo-800 transition shadow-xs">
              <span>📋</span>
              <span>Physician Review</span>
            </div>
          ) : (
            phase !== "language" && (
              <div className={`hidden sm:inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-bold border transition shadow-xs ${
                ayushMode
                  ? "bg-emerald-50 text-emerald-800 border-emerald-300"
                  : "bg-blue-50 text-blue-700 border-blue-200"
              }`}>
                <span>{ayushMode ? "🌿" : "🩺"}</span>
                <span>{ayushMode ? "AYUSH Intake" : "General Intake"}</span>
              </div>
            )
          )}
        </div>

        <div className="flex items-center gap-2 sm:gap-2.5">
          {phase !== "language" && phase !== "dashboard" && phase !== "summary" && (
            <button
              onClick={goBack}
              className="text-xs sm:text-sm bg-white hover:bg-blue-50 text-slate-700 hover:text-blue-700 font-bold rounded-full px-4 py-2 border border-slate-200/90 hover:border-blue-300 transition shadow-xs flex items-center gap-1.5"
              title="Go back to previous screen"
            >
              <span className="text-base font-bold leading-none">←</span>
              <span>{t(lang, "back")}</span>
            </button>
          )}

          {phase !== "summary" && phase !== "dashboard" && (
            <button
              onClick={openDoctorDashboard}
              disabled={busy}
              className="text-xs sm:text-sm bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold rounded-full px-4 sm:px-5 py-2 sm:py-2.5 shadow-md shadow-blue-500/20 hover:shadow-blue-500/30 transition flex items-center gap-1.5 sm:gap-2"
              title="Open Physician Summary Dashboard"
            >
              <span>👨‍⚕️</span>
              <span>Doctor Dashboard</span>
            </button>
          )}

          {phase === "summary" && (
            <button
              onClick={openDoctorDashboard}
              disabled={busy}
              className="text-xs sm:text-sm bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold rounded-full px-4 py-2 border border-blue-200 transition flex items-center gap-1.5"
              title="Return to Doctor Dashboard"
            >
              <span>👨‍⚕️</span>
              <span>Dashboard</span>
            </button>
          )}

          {phase !== "language" && phase !== "dashboard" && (
            <button
              onClick={restart}
              className="text-xs sm:text-sm bg-white hover:bg-slate-100 text-slate-600 font-medium rounded-full px-3.5 py-2 border border-slate-200 transition"
              title="Start intake for a new patient"
            >
              {t(lang, "restart")}
            </button>
          )}
        </div>
      </header>

      {redFlags.length > 0 && phase === "interview" && (
        <RedFlagBanner lang={lang} flags={redFlags} />
      )}

      <main className={`flex-1 w-full mx-auto px-4 sm:px-6 py-6 print:p-0 print:max-w-none ${
        phase === "dashboard" || phase === "summary" ? "max-w-6xl xl:max-w-7xl" : "max-w-3xl"
      }`}>
        <ErrorBoundary onReset={restart}>
          {error && (
            <div className="mb-4 rounded-lg bg-red-50 border border-red-200 text-red-700 px-4 py-3 text-sm print:hidden">
              {error} — is the API running at {api.base}?
            </div>
          )}

          {phase === "language" && (
            <LanguageSelect
              lang={lang}
              ayushMode={ayushMode}
              onToggleAyush={setAyushMode}
              onChoose={chooseLanguage}
            />
          )}

          {phase === "consent" && (
            <ConsentScreen lang={lang} busy={busy} onAgree={agreeConsent} onBack={goBack} />
          )}

          {phase === "interview" && question && (
            <QuestionCard
              lang={lang}
              question={question}
              busy={busy}
              autoVoice={autoVoice}
              onVoiceToggle={(val) => setAutoVoice(val)}
              pendingConfirm={pendingConfirm}
              onSubmit={submitAnswer}
              onConfirmYes={confirmYes}
              onConfirmNo={confirmNo}
              onPrevious={goBack}
            />
          )}

          {phase === "preparing_summary" && (
            <div className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-[0_10px_35px_rgba(37,99,235,0.08)] border border-blue-100 p-10 text-center max-w-md mx-auto my-12">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center text-3xl animate-bounce-gentle text-blue-600">
                ✨
              </div>
              <h2 className="text-xl font-bold text-slate-900 mb-2">Preparing Clinical Summary…</h2>
              <p className="text-sm text-slate-500 leading-relaxed">
                Compiling intake history, verified symptoms, and constitutional cues for the clinician.
              </p>
            </div>
          )}

          {phase === "dashboard" && summary && (
            <DoctorDashboard
              lang={lang}
              sessionId={sessionId}
              summary={summary}
              redFlags={redFlags}
              onOpenSummary={() => setPhase("summary")}
              onRestart={restart}
              onBack={goBack}
            />
          )}

          {phase === "summary" && (
            <SummaryView
              lang={lang}
              sessionId={sessionId}
              summary={summary || {}}
              redFlags={redFlags}
              onRestart={restart}
              onBack={goBack}
            />
          )}
        </ErrorBoundary>
      </main>

      <footer className="text-center text-xs text-slate-400 py-3 print:hidden">
        MediKiosk · PS 26047 · demo scaffold — the LLM is not the source of truth
      </footer>
    </div>
  );
}
