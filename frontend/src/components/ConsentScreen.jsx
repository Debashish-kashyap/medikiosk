import { t } from "../i18n";

// Consent-first, audio-guided (TTS playback is a TODO for the Frontend lane).
export default function ConsentScreen({ lang, busy, onAgree, onBack }) {
  return (
    <div className="bg-white rounded-2xl shadow p-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-2xl">🔒</span>
        <h2 className="text-xl font-bold">{t(lang, "consentTitle")}</h2>
      </div>
      <p className="text-slate-600 mb-6 leading-relaxed text-lg">{t(lang, "consentBody")}</p>
      <div className="flex flex-col sm:flex-row gap-3">
        <button className="tap tap-selected flex-1 py-6" disabled={busy} onClick={onAgree}>
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
