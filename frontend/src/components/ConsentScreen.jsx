import { useEffect, useState } from "react";
import { SPEECH_LANG, t } from "../i18n";

export default function ConsentScreen({ lang, busy, onAgree, onBack }) {
  const [abhaId, setAbhaId] = useState("");
  const [otp, setOtp] = useState("");
  const [localError, setLocalError] = useState("");

  const readConsentAloud = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      return;
    }

    const text = `${t(lang, "consentTitle")}. ${t(lang, "consentBody")}. ${t(lang, "abhaIdLabel")}. ${t(lang, "otpLabel")}.`;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = SPEECH_LANG[lang] || "en-US";
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
  };

  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      return;
    }

    const timer = window.setTimeout(() => {
      readConsentAloud();
    }, 600);

    return () => {
      window.clearTimeout(timer);
      window.speechSynthesis.cancel();
    };
  }, [lang]);

  const handleSubmit = () => {
    const cleanedAbhaId = abhaId.trim();
    const cleanedOtp = otp.trim();

    if (!cleanedAbhaId) {
      setLocalError(t(lang, "abhaRequired"));
      return;
    }
    if (!cleanedOtp) {
      setLocalError(t(lang, "otpRequired"));
      return;
    }

    setLocalError("");
    onAgree(cleanedAbhaId, cleanedOtp);
  };

  return (
    <div className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-[0_4px_25px_rgba(15,23,42,0.05)] border border-blue-100/80 p-7 sm:p-8 max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-3">
        <span className="w-10 h-10 rounded-2xl bg-blue-50 border border-blue-200/70 flex items-center justify-center text-xl text-blue-600 shadow-xs">🔒</span>
        <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">{t(lang, "consentTitle")}</h2>
      </div>
      <p className="text-slate-600 mb-6 leading-relaxed text-base sm:text-lg">{t(lang, "consentBody")}</p>

      <div className="space-y-4 mb-6">
        <div>
          <label className="mb-1.5 block text-sm font-bold text-slate-700">{t(lang, "abhaIdLabel")}</label>
          <input
            type="text"
            value={abhaId}
            onChange={(e) => setAbhaId(e.target.value)}
            placeholder={t(lang, "abhaIdPlaceholder")}
            className="w-full rounded-2xl border border-slate-200/90 bg-slate-50/50 px-4 py-3.5 text-lg focus:bg-white focus:border-blue-600 focus:ring-4 focus:ring-blue-100 transition focus:outline-none font-medium"
            autoComplete="off"
            disabled={busy}
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-bold text-slate-700">{t(lang, "otpLabel")}</label>
          <input
            type="text"
            inputMode="numeric"
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
            placeholder={t(lang, "otpPlaceholder")}
            className="w-full rounded-2xl border border-slate-200/90 bg-slate-50/50 px-4 py-3.5 text-lg focus:bg-white focus:border-blue-600 focus:ring-4 focus:ring-blue-100 transition focus:outline-none font-medium"
            autoComplete="one-time-code"
            disabled={busy}
          />
        </div>
      </div>

      {localError && <div className="mb-4 rounded-xl bg-red-50 border border-red-200 text-red-700 px-4 py-3 text-sm font-medium">{localError}</div>}

      <div className="flex flex-col sm:flex-row gap-3 items-stretch">
        <button type="button" className="tap sm:w-48 py-4 text-base font-bold flex items-center justify-center gap-2" onClick={readConsentAloud}>
          <span>🔊</span>
          <span>{t(lang, "readAloud")}</span>
        </button>
        <button
          className="tap flex-1 py-4 text-lg font-bold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg shadow-blue-500/25 border-transparent hover:border-transparent active:scale-[0.99] flex items-center justify-center"
          disabled={busy}
          onClick={handleSubmit}
        >
          {busy ? "…" : t(lang, "consentAgree")}
        </button>
        <button type="button" className="tap sm:w-32 py-4 text-base font-bold flex items-center justify-center" disabled={busy} onClick={onBack}>
          {t(lang, "back")}
        </button>
      </div>
      <p className="mt-5 text-xs text-slate-400 text-center">
        DPDP 2023 alignment: data minimization · encryption · revocable, purpose-specific consent · audit trail.
      </p>
    </div>
  );
}
