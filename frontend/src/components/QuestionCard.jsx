import { useEffect, useState } from "react";
import { SPEECH_LANG, t } from "../i18n";
import VoiceButton from "./VoiceButton.jsx";

const ICONS = {
  heart: "❤️", thermometer: "🌡️", lungs: "🫁", brain: "🧠", stomach: "🍽️", more: "➕",
  clock: "⏱️", calendar: "📅", target: "🎯", "arrow-left": "⬅️", "arrow-right": "➡️",
  compress: "🤏", fire: "🔥", bolt: "⚡", cloud: "☁️", arm: "💪", face: "😬", back: "🧍",
  no: "🚫", check: "✅", snow: "❄️", spots: "🔴", drop: "💧", gauge: "📈", gland: "🦋", warning: "⚠️",
};

export default function QuestionCard({ lang, question, busy, autoVoice, onVoiceToggle, pendingConfirm, onSubmit, onConfirmYes, onConfirmNo }) {
  const [multi, setMulti] = useState([]);

  // Reset multi-select state whenever the question changes.
  useEffect(() => {
    setMulti([]);
  }, [question.node_id]);

  function toggleMulti(v) {
    setMulti((prev) => {
      if (v === "none") return prev.includes("none") ? [] : ["none"];
      const base = prev.filter((x) => x !== "none");
      return base.includes(v) ? base.filter((x) => x !== v) : [...base, v];
    });
  }

  const isMulti = question.type === "multi_select";
  const isScale = question.type === "scale";

  const readQuestionAloud = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      return;
    }

    const text = [question.prompt, question.help, ...(question.options || []).map((option) => option.label || option.text || "")]
      .filter(Boolean)
      .join(". ");

    if (!text) {
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = SPEECH_LANG[lang] || "en-US";
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
  };

  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window) || !question || !question.prompt) {
      return;
    }

    const timer = window.setTimeout(() => {
      readQuestionAloud();
    }, 700);

    return () => {
      window.clearTimeout(timer);
      window.speechSynthesis.cancel();
    };
  }, [question.node_id, lang]);

  return (
    <div className="bg-white rounded-2xl shadow p-6">
      <div className="flex items-start justify-between gap-3 mb-1">
        <h2 className="text-2xl font-bold">{question.prompt}</h2>
        <button type="button" className="tap px-3 py-2 text-sm" onClick={readQuestionAloud} disabled={busy}>
          🔊 {t(lang, "readAloud")}
        </button>
      </div>
      {question.help && <p className="text-slate-500 mb-4">{question.help}</p>}

      {/* Low-confidence confirmation loop (noisy-room / ASR safety). */}
      {pendingConfirm && (
        <div className="mb-5 rounded-xl border-2 border-kiosk-warn bg-orange-50 p-4">
          <p className="text-slate-700 mb-3">{pendingConfirm.message}</p>
          {pendingConfirm.interpreted_value != null && (
            <div className="flex items-center gap-3">
              <span className="font-semibold">
                {t(lang, "confirmHeading")} “{pendingConfirm.interpreted_label}”
              </span>
              <button className="tap tap-selected px-4 py-2" disabled={busy} onClick={onConfirmYes}>
                {t(lang, "confirmYes")}
              </button>
              <button className="tap px-4 py-2" disabled={busy} onClick={onConfirmNo}>
                {t(lang, "confirmNo")}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Voice input (dual-mode: speak OR tap). */}
      {question.allow_voice && (
        <div className="mb-4">
          <VoiceButton
            lang={lang}
            questionId={question.node_id}
            autoVoice={autoVoice}
            onAutoVoiceToggle={onVoiceToggle}
            disabled={busy}
            onResult={(text, confidence) => onSubmit({ text, confidence })}
          />
          <p className="text-center text-slate-400 text-sm mt-2">{t(lang, "orType")}</p>
        </div>
      )}

      {/* Touch input. */}
      {isScale ? (
        <div className="grid grid-cols-6 sm:grid-cols-11 gap-2">
          {Array.from({ length: (question.scale_max ?? 10) - (question.scale_min ?? 0) + 1 }, (_, i) => i + (question.scale_min ?? 0)).map(
            (n) => (
              <button key={n} className="tap py-4 text-lg" disabled={busy} onClick={() => onSubmit({ touch_value: n })}>
                {n}
              </button>
            )
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {question.options.map((opt) => {
            const selected = isMulti && multi.includes(opt.value);
            return (
              <button
                key={opt.value}
                disabled={busy}
                className={`tap flex items-center gap-3 text-left ${selected ? "tap-selected" : ""}`}
                onClick={() => (isMulti ? toggleMulti(opt.value) : onSubmit({ touch_value: opt.value }))}
              >
                <span className="text-2xl">{ICONS[opt.icon] || "•"}</span>
                <span>{opt.label}</span>
              </button>
            );
          })}
        </div>
      )}

      {isMulti && (
        <button
          className="tap tap-selected w-full mt-4 py-5"
          disabled={busy || multi.length === 0}
          onClick={() => onSubmit({ touch_value: multi })}
        >
          {t(lang, "done")}
        </button>
      )}
    </div>
  );
}
