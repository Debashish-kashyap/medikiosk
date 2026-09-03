import { LANGUAGES, t } from "../i18n";

export default function LanguageSelect({ lang, ayushMode, onToggleAyush, onChoose }) {
  return (
    <div className="pt-4 max-w-2xl mx-auto">
      {/* Consultation Mode Switcher Card */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-6 mb-8 transition">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl">🩺</span>
              <h2 className="text-xl font-bold text-slate-900">{t(lang, "intakeModeHeading")}</h2>
            </div>
            <p className="text-sm text-slate-500 mt-0.5">{t(lang, "intakeModeSub")}</p>
          </div>

          {/* Quick status pill */}
          <div className={`self-start sm:self-auto inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
            ayushMode ? "bg-emerald-100 text-emerald-800 border border-emerald-300" : "bg-blue-100 text-blue-800 border border-blue-300"
          }`}>
            <span className="w-2 h-2 rounded-full animate-ping" style={{ backgroundColor: ayushMode ? "#059669" : "#2563eb" }}></span>
            <span>{ayushMode ? "AYUSH Active" : "General Active"}</span>
          </div>
        </div>

        {/* Segmented Switch Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" role="radiogroup" aria-label="Consultation Mode">
          {/* General / Allopathic Mode */}
          <button
            type="button"
            role="radio"
            aria-checked={!ayushMode}
            onClick={() => onToggleAyush(false)}
            className={`p-4 rounded-xl border-2 text-left transition relative flex flex-col justify-between ${
              !ayushMode
                ? "border-blue-600 bg-blue-50/50 text-slate-900 shadow-sm ring-2 ring-blue-500/20"
                : "border-slate-200 bg-slate-50/50 hover:bg-slate-100/70 text-slate-600"
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className="text-2xl">🏥</span>
                <span className="font-bold text-base sm:text-lg">{t(lang, "modeGeneral")}</span>
              </div>
              <span className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                !ayushMode ? "border-blue-600 bg-blue-600 text-white" : "border-slate-300 bg-white"
              }`}>
                {!ayushMode && <svg className="w-3 h-3 fill-current" viewBox="0 0 12 12"><path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>}
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-500 leading-snug">{t(lang, "modeGeneralDesc")}</p>
          </button>

          {/* AYUSH Mode */}
          <button
            type="button"
            role="radio"
            aria-checked={ayushMode}
            onClick={() => onToggleAyush(true)}
            className={`p-4 rounded-xl border-2 text-left transition relative flex flex-col justify-between ${
              ayushMode
                ? "border-emerald-600 bg-emerald-50/50 text-slate-900 shadow-sm ring-2 ring-emerald-500/20"
                : "border-slate-200 bg-slate-50/50 hover:bg-slate-100/70 text-slate-600"
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span className="text-2xl">🌿</span>
                <span className="font-bold text-base sm:text-lg">{t(lang, "modeAyush")}</span>
              </div>
              <span className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                ayushMode ? "border-emerald-600 bg-emerald-600 text-white" : "border-slate-300 bg-white"
              }`}>
                {ayushMode && <svg className="w-3 h-3 fill-current" viewBox="0 0 12 12"><path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>}
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-500 leading-snug">{t(lang, "modeAyushDesc")}</p>
          </button>
        </div>

        {ayushMode && (
          <div className="mt-3 p-3 rounded-xl bg-emerald-50 border border-emerald-200/70 flex items-start gap-2.5 text-xs text-emerald-900 leading-relaxed">
            <span className="text-base leading-none">🍃</span>
            <span>
              <strong>AYUSH Mode Selected:</strong> Assesses Ayurvedic body type (Prakriti), digestion (Agni), sleep/bowel patterns, and personal sensitivities alongside standard clinical triage.
            </span>
          </div>
        )}
      </div>

      {/* Language Selection Grid */}
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-6 text-slate-900">{t(lang, "chooseLanguage")}</h1>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              className={`tap py-8 text-2xl font-bold flex flex-col items-center justify-center gap-1 ${
                lang === l.code ? "ring-2 ring-kiosk-primary" : ""
              }`}
              onClick={() => onChoose(l.code, ayushMode)}
            >
              <span>{l.label}</span>
              <span className="text-xs font-normal text-slate-400 uppercase tracking-widest">{l.code}</span>
            </button>
          ))}
        </div>
        <p className="mt-8 text-xs text-slate-400">
          MediKiosk · Multilingual Tri-lingual Kiosk (Assamese / Hindi / English)
        </p>
      </div>
    </div>
  );
}
