import { LANGUAGES, t } from "../i18n";

export default function LanguageSelect({ lang, onChoose }) {
  return (
    <div className="text-center pt-6">
      <h1 className="text-2xl font-bold mb-8">{t(lang, "chooseLanguage")}</h1>
      <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
        {LANGUAGES.map((l) => (
          <button key={l.code} className="tap text-2xl py-10" onClick={() => onChoose(l.code)}>
            {l.label}
          </button>
        ))}
      </div>
      <p className="mt-8 text-sm text-slate-400">
        Add languages in <code>src/i18n.js</code> + ontology labels (AI-Speech / Frontend lanes).
      </p>
    </div>
  );
}
