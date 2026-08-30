import { useState } from "react";
import { api } from "./api";
import { t } from "./i18n";
import LanguageSelect from "./components/LanguageSelect.jsx";
import ConsentScreen from "./components/ConsentScreen.jsx";
import QuestionCard from "./components/QuestionCard.jsx";
import RedFlagBanner from "./components/RedFlagBanner.jsx";
import SummaryView from "./components/SummaryView.jsx";

// Kiosk flow: language -> consent -> interview -> summary.
export default function App() {
  const [lang, setLang] = useState("en");
  const [phase, setPhase] = useState("language");
  const [sessionId, setSessionId] = useState(null);
  const [question, setQuestion] = useState(null);
  const [redFlags, setRedFlags] = useState([]);
  const [pendingConfirm, setPendingConfirm] = useState(null);
  const [summary, setSummary] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [autoVoice, setAutoVoice] = useState(false);

  function chooseLanguage(code) {
    setLang(code);
    setPhase("consent");
  }

  async function agreeConsent() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.createSession(lang);
      setSessionId(res.session_id);
      setQuestion(res.question);
      await api.giveConsent(res.session_id, true);
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
        const s = await api.summary(sessionId);
        setSummary(s);
        setPhase("summary");
      } else {
        setQuestion(res.next_question);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const confirmYes = () =>
    submitAnswer({ touch_value: pendingConfirm.interpreted_value, confirmed: true });
  const confirmNo = () => setPendingConfirm(null);

  function restart() {
    setPhase("language");
    setSessionId(null);
    setQuestion(null);
    setRedFlags([]);
    setPendingConfirm(null);
    setSummary(null);
    setError(null);
  }

  return (
    <div className="min-h-full flex flex-col bg-slate-50 print:bg-white">
      <header className="bg-kiosk-primary text-white px-6 py-4 flex items-center justify-between shadow print:hidden">
        <div>
          <div className="text-2xl font-bold">{t(lang, "appTitle")}</div>
          <div className="text-sm opacity-90">{t(lang, "tagline")}</div>
        </div>
        {phase !== "language" && (
          <button onClick={restart} className="text-sm bg-white/15 rounded-lg px-3 py-2 hover:bg-white/25">
            {t(lang, "restart")}
          </button>
        )}
      </header>

      {redFlags.length > 0 && phase === "interview" && (
        <RedFlagBanner lang={lang} flags={redFlags} />
      )}

      <main className={`flex-1 w-full mx-auto px-4 py-6 print:p-0 print:max-w-none ${phase === "summary" ? "max-w-5xl" : "max-w-3xl"}`}>
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 text-red-700 px-4 py-3 text-sm print:hidden">
            {error} — is the API running at {api.base}?
          </div>
        )}

        {phase === "language" && <LanguageSelect lang={lang} onChoose={chooseLanguage} />}

        {phase === "consent" && (
          <ConsentScreen lang={lang} busy={busy} onAgree={agreeConsent} onBack={() => setPhase("language")} />
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
          />
        )}

        {phase === "summary" && summary && (
          <SummaryView lang={lang} sessionId={sessionId} summary={summary} redFlags={redFlags} onRestart={restart} />
        )}
      </main>

      <footer className="text-center text-xs text-slate-400 py-3 print:hidden">
        MediKiosk · PS 26047 · demo scaffold — the LLM is not the source of truth
      </footer>
    </div>
  );
}
