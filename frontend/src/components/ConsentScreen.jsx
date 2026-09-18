import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { t } from "../i18n";

export default function ConsentScreen({ lang, busy, onAgree, onBack }) {
  const [identityType, setIdentityType] = useState("abha");
  const [identityValue, setIdentityValue] = useState("");
  const [fullName, setFullName] = useState("");
  const [mobileNumber, setMobileNumber] = useState("");
  const [otp, setOtp] = useState("");
  const [localError, setLocalError] = useState("");

  const [speaking, setSpeaking] = useState(false);
  const audioRef = useRef(null);

  const readConsentAloud = async () => {
    const identityLabel = identityType === "abha"
      ? t(lang, "identityAbha")
      : identityType === "aadhaar"
        ? t(lang, "aadhaarLabel")
        : `${t(lang, "fullNameLabel")} ${t(lang, "mobileLabel")}`;
    const text = `${t(lang, "consentTitle")}. ${t(lang, "consentBody")}. ${t(lang, "identitySpeechPrefix")} ${identityLabel}. ${t(lang, "identitySpeechOtp")}`;
    try {
      setSpeaking(true);
      const blob = await api.synthesizeSpeech(text, lang);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        setSpeaking(false);
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        setSpeaking(false);
      };
      await audio.play();
    } catch {
      setSpeaking(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      readConsentAloud();
    }, 600);

    return () => {
      window.clearTimeout(timer);
      const audio = audioRef.current;
      if (audio) audio.pause();
    };
  }, [lang, identityType]);

  const handleSubmit = () => {
    const cleanedIdentity = identityValue.trim();
    const cleanedName = fullName.trim();
    const cleanedMobile = mobileNumber.replace(/\D/g, "");
    const cleanedOtp = otp.trim();

    if (identityType !== "new_registration" && !cleanedIdentity) {
      setLocalError(identityType === "aadhaar" ? t(lang, "aadhaarRequired") : t(lang, "abhaRequired"));
      return;
    }
    if (identityType === "aadhaar" && cleanedIdentity.replace(/\D/g, "").length !== 12) {
      setLocalError(t(lang, "aadhaarInvalid"));
      return;
    }
    if (identityType === "new_registration" && !cleanedName) {
      setLocalError(t(lang, "fullNameRequired"));
      return;
    }
    if (identityType === "new_registration" && cleanedMobile.length < 10) {
      setLocalError(t(lang, "mobileRequired"));
      return;
    }
    if (!cleanedOtp) {
      setLocalError(t(lang, "otpRequired"));
      return;
    }

    setLocalError("");
    onAgree({
      identity_type: identityType,
      identity_value: identityType === "aadhaar" ? cleanedIdentity.replace(/\D/g, "") : cleanedIdentity || undefined,
      full_name: identityType === "new_registration" ? cleanedName : undefined,
      mobile_number: identityType === "new_registration" ? cleanedMobile.slice(-10) : undefined,
      otp: cleanedOtp,
    });
  };

  return (
    <div className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-[0_4px_25px_rgba(15,23,42,0.05)] border border-blue-100/80 p-7 sm:p-8 max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-3">
        <span className="w-10 h-10 rounded-2xl bg-blue-50 border border-blue-200/70 flex items-center justify-center text-xl text-blue-600 shadow-xs">🔒</span>
        <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">{t(lang, "consentTitle")}</h2>
      </div>
      <p className="text-slate-600 mb-6 leading-relaxed text-base sm:text-lg">{t(lang, "consentBody")}</p>

      <div className="space-y-4 mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2" role="tablist" aria-label={t(lang, "identityMethodLabel")}>
          {[
            ["abha", t(lang, "identityAbha")],
            ["aadhaar", t(lang, "identityAadhaar")],
            ["new_registration", t(lang, "identityNewPatient")],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={identityType === value}
              onClick={() => { setIdentityType(value); setLocalError(""); }}
              className={`rounded-xl border px-3 py-3 text-sm font-bold transition ${identityType === value ? "border-blue-600 bg-blue-50 text-blue-800" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"}`}
              disabled={busy}
            >
              {label}
            </button>
          ))}
        </div>

        {identityType === "new_registration" ? (
          <>
            <div>
              <label className="mb-1.5 block text-sm font-bold text-slate-700">{t(lang, "fullNameLabel")}</label>
              <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder={t(lang, "fullNamePlaceholder")} className="w-full rounded-2xl border border-slate-200/90 bg-slate-50/50 px-4 py-3.5 text-lg focus:bg-white focus:border-blue-600 focus:ring-4 focus:ring-blue-100 transition focus:outline-none font-medium" autoComplete="name" disabled={busy} />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-bold text-slate-700">{t(lang, "mobileLabel")}</label>
              <input type="tel" inputMode="numeric" value={mobileNumber} onChange={(e) => setMobileNumber(e.target.value.replace(/\D/g, "").slice(0, 10))} placeholder={t(lang, "mobilePlaceholder")} className="w-full rounded-2xl border border-slate-200/90 bg-slate-50/50 px-4 py-3.5 text-lg focus:bg-white focus:border-blue-600 focus:ring-4 focus:ring-blue-100 transition focus:outline-none font-medium" autoComplete="tel" disabled={busy} />
            </div>
          </>
        ) : (
        <div>
          <label className="mb-1.5 block text-sm font-bold text-slate-700">{identityType === "aadhaar" ? t(lang, "aadhaarLabel") : t(lang, "abhaIdLabel")}</label>
          <input
            type="text"
            value={identityValue}
            onChange={(e) => setIdentityValue(e.target.value)}
            placeholder={identityType === "aadhaar" ? t(lang, "aadhaarPlaceholder") : t(lang, "abhaIdPlaceholder")}
            className="w-full rounded-2xl border border-slate-200/90 bg-slate-50/50 px-4 py-3.5 text-lg focus:bg-white focus:border-blue-600 focus:ring-4 focus:ring-blue-100 transition focus:outline-none font-medium"
            autoComplete="off"
            disabled={busy}
          />
        </div>
        )}

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
