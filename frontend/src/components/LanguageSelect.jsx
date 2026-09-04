import { LANGUAGES, t } from "../i18n";

export default function LanguageSelect({ lang, ayushMode, onToggleAyush, onChoose }) {
  return (
    <div className="pt-4 max-w-2xl mx-auto">
      {/* Consultation Mode Switcher Card */}
      <div className="bg-white/95 backdrop-blur-sm rounded-3xl shadow-[0_4px_25px_rgba(15,23,42,0.05)] border border-blue-100/80 p-7 mb-8 transition">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl">🩺</span>
              <h2 className="text-xl font-bold text-slate-900">{t(lang, "intakeModeHeading")}</h2>
            </div>
            <p className="text-sm text-slate-500 mt-1">{t(lang, "intakeModeSub")}</p>
          </div>

          {/* Quick status pill */}
          <div className={`self-start sm:self-auto inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider ${
            ayushMode
              ? "bg-emerald-50 text-emerald-800 border border-emerald-300"
              : "bg-blue-50 text-blue-700 border border-blue-200"
          }`}>
            <span className="w-2 h-2 rounded-full animate-ping" style={{ backgroundColor: ayushMode ? "#059669" : "#2563eb" }}></span>
            <span>{ayushMode ? "AYUSH Active" : "General Active"}</span>
          </div>
        </div>

        {/* Segmented Switch Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5" role="radiogroup" aria-label="Consultation Mode">
          {/* General / Allopathic Mode */}
          <button
            type="button"
            role="radio"
            aria-checked={!ayushMode}
            onClick={() => onToggleAyush(false)}
            className={`p-4 sm:p-5 rounded-2xl border-2 text-left transition relative flex flex-col justify-between ${
              !ayushMode
                ? "border-blue-600 bg-gradient-to-br from-blue-50/80 to-indigo-50/40 text-slate-900 shadow-sm ring-2 ring-blue-500/20"
                : "border-slate-200/90 bg-white hover:bg-slate-50 text-slate-600 hover:border-slate-300"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2.5">
                <span className="text-2xl">🏥</span>
                <span className="font-bold text-base sm:text-lg text-slate-900">{t(lang, "modeGeneral")}</span>
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
            className={`p-4 sm:p-5 rounded-2xl border-2 text-left transition relative flex flex-col justify-between ${
              ayushMode
                ? "border-emerald-600 bg-gradient-to-br from-emerald-50/80 to-teal-50/40 text-slate-900 shadow-sm ring-2 ring-emerald-500/20"
                : "border-slate-200/90 bg-white hover:bg-slate-50 text-slate-600 hover:border-slate-300"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2.5">
                <span className="text-2xl">🌿</span>
                <span className="font-bold text-base sm:text-lg text-slate-900">{t(lang, "modeAyush")}</span>
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
          <div className="mt-4 p-3.5 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-start gap-3 text-xs text-emerald-900 leading-relaxed">
            <span className="text-base leading-none">🍃</span>
            <span>
              <strong>AYUSH Mode Selected:</strong> Assesses Ayurvedic body type (Prakriti), digestion (Agni), sleep/bowel patterns, and personal sensitivities alongside standard clinical triage.
            </span>
          </div>
        )}
      </div>

      {/* Language Selection Grid */}
      <div className="text-center">
        <h1 className="text-2xl sm:text-3xl font-extrabold mb-6 text-slate-900 tracking-tight">{t(lang, "chooseLanguage")}</h1>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {LANGUAGES.map((l, idx) => (
            <button
              key={l.code}
              className={`tap py-8 text-2xl font-bold flex flex-col items-center justify-center gap-1.5 relative group ${
                lang === l.code ? "ring-2 ring-blue-600 border-blue-600 bg-gradient-to-br from-blue-50 to-indigo-50/50 text-blue-700 shadow-md shadow-blue-500/15" : ""
              }`}
              onClick={() => onChoose(l.code, ayushMode)}
            >
              <span className="text-[11px] font-mono font-bold text-blue-500/70 tracking-widest uppercase">0{idx + 1}</span>
              <span className="text-2xl font-extrabold text-slate-900 group-hover:text-blue-600 transition">{l.label}</span>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">{l.code}</span>
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
