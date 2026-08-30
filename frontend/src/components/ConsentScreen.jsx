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
    <div className="bg-white rounded-2xl shadow p-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-2xl">🔒</span>
        <h2 className="text-xl font-bold">{t(lang, "consentTitle")}</h2>
      </div>
      <p className="text-slate-600 mb-6 leading-relaxed text-lg">{t(lang, "consentBody")}</p>

      <div className="space-y-4 mb-6">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">{t(lang, "abhaIdLabel")}</label>
          <input
            type="text"
            value={abhaId}
            onChange={(e) => setAbhaId(e.target.value)}
            placeholder={t(lang, "abhaIdPlaceholder")}
            className="w-full rounded-xl border border-slate-300 px-4 py-3 text-lg focus:border-kiosk-primary focus:outline-none"
            autoComplete="off"
            disabled={busy}
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">{t(lang, "otpLabel")}</label>
          <input
            type="text"
            inputMode="numeric"
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
            placeholder={t(lang, "otpPlaceholder")}
            className="w-full rounded-xl border border-slate-300 px-4 py-3 text-lg focus:border-kiosk-primary focus:outline-none"
            autoComplete="one-time-code"
            disabled={busy}
          />
        </div>
      </div>

      {localError && <div className="mb-4 rounded-lg bg-red-50 border border-red-200 text-red-700 px-3 py-2 text-sm">{localError}</div>}

      <div className="flex flex-col sm:flex-row gap-3">
        <button type="button" className="tap sm:w-40" onClick={readConsentAloud}>
          🔊 {t(lang, "readAloud")}
        </button>
        <button className="tap tap-selected flex-1 py-6" disabled={busy} onClick={handleSubmit}>
          {busy ? "…" : t(lang, "consentAgree")}
        </button>
        <button className="tap sm:w-40" disabled={busy} onClick={onBack}>
          {t(lang, "back")}
        </button>
      </div>
      <p className="mt-4 text-xs text-slate-400">
        DPDP 2023 alignment: data minimization · encryption · revocable, purpose-specific consent · audit trail.
      </p>
    </div>
  );
}
