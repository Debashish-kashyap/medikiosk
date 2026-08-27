import { t } from "../i18n";

// Sticky priority alert. Driven by the backend rule engine (red_flags.py), not the LLM.
export default function RedFlagBanner({ lang, flags }) {
  const top = flags[0];
  const color = top.priority === "HIGH" ? "bg-kiosk-danger" : "bg-kiosk-warn";
  return (
    <div className={`${color} text-white px-6 py-3`}>
      <div className="max-w-3xl mx-auto flex items-center gap-3">
        <span className="text-2xl">⚠️</span>
        <div>
          <div className="font-bold uppercase text-xs tracking-widest">
            {t(lang, "redFlag")} · {top.priority}
          </div>
          <div className="text-sm">
            {top.label} — {top.action}
          </div>
        </div>
      </div>
    </div>
  );
}
