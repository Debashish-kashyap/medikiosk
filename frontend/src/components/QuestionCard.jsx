import { useEffect, useRef, useState } from "react";
import { SPEECH_LANG, t } from "../i18n";
import VoiceButton from "./VoiceButton.jsx";

const ICONS = {
  heart: "❤️", thermometer: "🌡️", lungs: "🫁", brain: "🧠", stomach: "🍽️", more: "➕",
  clock: "⏱️", calendar: "📅", target: "🎯", "arrow-left": "⬅️", "arrow-right": "➡️",
  compress: "🤏", fire: "🔥", bolt: "⚡", cloud: "☁️", arm: "💪", face: "😬", back: "🧍",
  no: "🚫", check: "✅", snow: "❄️", spots: "🔴", drop: "💧", gauge: "📈", gland: "🦋", warning: "⚠️",
  wind: "💨", flame: "🔥", shield: "🛡️", "help-circle": "❓", activity: "📈", zap: "⚡",
  "battery-low": "🪫", "alert-triangle": "⚠️", smile: "😊", "alert-circle": "⚠️", lock: "🔒",
};

export default function QuestionCard({
  lang,
  question,
  busy,
  autoVoice,
  onVoiceToggle,
  pendingConfirm,
  onSubmit,
  onConfirmYes,
  onConfirmNo,
}) {
  const [multi, setMulti] = useState([]);
  const [freeText, setFreeText] = useState("");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [listenSignal, setListenSignal] = useState(null);

  const speechTimerRef = useRef(null);
  const safetyTimerRef = useRef(null);
  const listenTimerRef = useRef(null);
  const currentUtteranceRef = useRef(null);

  // Reset multi-select & free-text state whenever the question changes.
  useEffect(() => {
    setMulti([]);
    setFreeText("");
  }, [question.node_id]);

  function toggleMulti(v) {
    setMulti((prev) => {
      if (v === "none") return prev.includes("none") ? [] : ["none"];
      const base = prev.filter((x) => x !== "none");
      return base.includes(v) ? base.filter((x) => x !== v) : [...base, v];
    });
  }

  const isInfoScreen = question.type === "info_screen";
  const isFreeText = question.type === "free_text";
  const isMulti = question.type === "multi_select";
  const isScale = question.type === "scale";

  function stopSpeaking() {
    clearTimeout(speechTimerRef.current);
    clearTimeout(safetyTimerRef.current);
    clearTimeout(listenTimerRef.current);
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (_) { }
    }
    setIsSpeaking(false);
    currentUtteranceRef.current = null;
  }

  function readTextAloud(text) {
    stopSpeaking();

    if (!text) {
      if (autoVoice && !busy && question.allow_voice) {
        listenTimerRef.current = setTimeout(() => {
          setListenSignal(Date.now());
        }, 300);
      }
      return;
    }

    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      if (autoVoice && !busy && question.allow_voice) {
        listenTimerRef.current = setTimeout(() => {
          setListenSignal(Date.now());
        }, 300);
      }
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = SPEECH_LANG[lang] || "en-US";
    utterance.rate = 0.95;
    currentUtteranceRef.current = utterance;

    const onTTSFinished = () => {
      clearTimeout(safetyTimerRef.current);
      setIsSpeaking(false);
      currentUtteranceRef.current = null;

      // Turn-based transition: quiet pause of 250ms before opening mic to avoid echoing TTS
      if (autoVoice && !busy && question.allow_voice) {
        listenTimerRef.current = setTimeout(() => {
          setListenSignal(Date.now());
        }, 250);
      }
    };

    utterance.onstart = () => {
      setIsSpeaking(true);
    };

    utterance.onend = () => {
      onTTSFinished();
    };

    utterance.onerror = (err) => {
      console.warn("[QuestionCard TTS warning]", err);
      onTTSFinished();
    };

    // Safety fallback timer for browsers with buggy onend events
    const safetyMs = Math.max(3500, (text.length / 10) * 1000 + 2500);
    safetyTimerRef.current = setTimeout(onTTSFinished, safetyMs);

    setIsSpeaking(true);
    try {
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("[QuestionCard TTS speak error]", e);
      onTTSFinished();
    }
  }

  const readQuestionAloud = () => {
    const text = [
      question.prompt,
      question.help,
      ...(question.options || []).map((option) => option.label || option.text || ""),
      ...(question.quick_options || []).map((qo) => qo.label || ""),
    ]
      .filter(Boolean)
      .join(". ");

    readTextAloud(text);
  };

  function handleSkipTTS() {
    stopSpeaking();
    // Immediately open microphone for user answer
    if (question.allow_voice && !busy) {
      setListenSignal(Date.now());
    }
  }

  // Turn-based loop: automatically read question on load, then open mic on completion
  useEffect(() => {
    if (!question || !question.prompt) return;

    speechTimerRef.current = setTimeout(() => {
      readQuestionAloud();
    }, 400);

    return () => {
      stopSpeaking();
    };
  }, [question.node_id, lang]);

  // Turn-based confirmation read aloud
  useEffect(() => {
    if (pendingConfirm) {
      const confirmText = `${pendingConfirm.message || ""} ${t(lang, "confirmHeading")} ${pendingConfirm.interpreted_label || ""}`;
      speechTimerRef.current = setTimeout(() => {
        readTextAloud(confirmText);
      }, 300);
    }
  }, [pendingConfirm]);

  // Grouping for multi-select options (e.g. sleep vs bowel in ayush_sleep_bowel)
  const options = question.options || [];
  const hasGroups = options.some((opt) => Boolean(opt.group));
  const groups = hasGroups
    ? Array.from(new Set(options.map((opt) => opt.group).filter(Boolean)))
    : [];

  return (
    <div className="bg-white rounded-2xl shadow p-6">
      {/* Question Header */}
      <div className="flex items-start justify-between gap-3 mb-1">
        <div className="flex-1">
          {question.section === "ayush" && (
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 mb-2 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300/60">
              <span>🌿</span>
              <span>{t(lang, "ayushBadge")} Intake</span>
            </div>
          )}
          <h2 className="text-2xl font-bold text-slate-900 leading-snug">{question.prompt}</h2>
        </div>

        <button
          type="button"
          className={`tap px-3 py-2 text-sm flex items-center gap-1.5 transition shrink-0 ${
            isSpeaking ? "bg-amber-100 text-amber-900 ring-2 ring-amber-400 font-semibold" : ""
          }`}
          onClick={readQuestionAloud}
          disabled={busy}
        >
          <span>{isSpeaking ? "🔊" : "🔈"}</span>
          <span>{isSpeaking ? t(lang, "kioskSpeakingTitle") : t(lang, "readAloud")}</span>
        </button>
      </div>

      {question.help && <p className="text-slate-500 mb-5 leading-relaxed">{question.help}</p>}

      {/* Low-confidence confirmation loop (noisy-room / ASR safety). */}
      {pendingConfirm && (
        <div className="mb-5 rounded-xl border-2 border-kiosk-warn bg-orange-50 p-4">
          <p className="text-slate-700 mb-3">{pendingConfirm.message}</p>
          {pendingConfirm.interpreted_value != null && (
            <div className="flex items-center gap-3 flex-wrap">
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

      {/* INFO SCREEN (e.g. ayush_intro acknowledgment) */}
      {isInfoScreen && (
        <div className="mt-4 pt-2">
          <div className="p-5 rounded-2xl bg-emerald-50/80 border border-emerald-200/80 mb-6 flex items-start gap-4">
            <span className="text-3xl">🍃</span>
            <div className="text-sm text-emerald-950 space-y-1">
              <p className="font-semibold">Quick 60–90 second overview</p>
              <p className="opacity-90">Your responses give your doctor and vaidya immediate constitutional cues. You can skip at any time.</p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-4">
            <button
              type="button"
              className="tap tap-selected w-full sm:flex-1 py-5 text-xl font-bold flex items-center justify-center gap-2"
              disabled={busy}
              onClick={() => {
                stopSpeaking();
                onSubmit({ touch_value: "start" });
              }}
            >
              <span>{question.cta || t(lang, "ayushStart")}</span>
              <span>➡️</span>
            </button>

            {question.skip_option && (
              <button
                type="button"
                className="tap text-slate-500 hover:text-slate-800 w-full sm:w-auto py-5 px-6 font-medium text-base border-slate-200"
                disabled={busy}
                onClick={() => {
                  stopSpeaking();
                  onSubmit({ touch_value: "skip" });
                }}
              >
                {question.skip_option}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Voice input (turn-based: speaks first, then records cleanly). */}
      {!isInfoScreen && question.allow_voice && (
        <div className="mb-5">
          <VoiceButton
            lang={lang}
            questionId={question.node_id}
            autoVoice={autoVoice}
            onAutoVoiceToggle={onVoiceToggle}
            disabled={busy}
            isSpeaking={isSpeaking}
            onSkipTTS={handleSkipTTS}
            listenSignal={listenSignal}
            onResult={(text, confidence) => {
              if (isFreeText) {
                setFreeText(text);
              }
              onSubmit({ text, confidence });
            }}
          />
          <p className="text-center text-slate-400 text-sm mt-2">{t(lang, "orType")}</p>
        </div>
      )}

      {/* FREE TEXT INPUT (e.g. ayush_satmya with quick chips) */}
      {isFreeText && (
        <div className="space-y-4">
          {/* Quick Option Chips */}
          {question.quick_options && question.quick_options.length > 0 && (
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Quick Choices:
              </label>
              <div className="flex flex-wrap gap-2">
                {question.quick_options.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      stopSpeaking();
                      onSubmit({ touch_value: opt.value });
                    }}
                    className="px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-emerald-50 hover:border-emerald-300 text-slate-800 text-sm font-semibold transition active:scale-95 flex items-center gap-1.5"
                  >
                    <span>✦</span>
                    <span>{opt.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Text Input Box */}
          <div className="space-y-2">
            <textarea
              rows={3}
              value={freeText}
              onChange={(e) => setFreeText(e.target.value)}
              placeholder={t(lang, "freeTextPlaceholder")}
              className="w-full rounded-xl border border-slate-300 p-4 text-base focus:border-kiosk-primary focus:outline-none focus:ring-2 focus:ring-kiosk-primary/20"
              disabled={busy}
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                disabled={busy || !freeText.trim()}
                onClick={() => {
                  stopSpeaking();
                  onSubmit({ touch_value: freeText.trim() });
                }}
                className="tap tap-selected px-6 py-3 text-base font-bold"
              >
                {t(lang, "submitAnswer")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SCALE INPUT (0 to 10) */}
      {isScale && (
        <div className="grid grid-cols-6 sm:grid-cols-11 gap-2">
          {Array.from({ length: (question.scale_max ?? 10) - (question.scale_min ?? 0) + 1 }, (_, i) => i + (question.scale_min ?? 0)).map(
            (n) => (
              <button
                key={n}
                className="tap py-4 text-lg"
                disabled={busy}
                onClick={() => {
                  stopSpeaking();
                  onSubmit({ touch_value: n });
                }}
              >
                {n}
              </button>
            )
          )}
        </div>
      )}

      {/* STANDARD SINGLE / MULTI SELECT INPUT */}
      {!isInfoScreen && !isFreeText && !isScale && (
        <>
          {hasGroups ? (
            <div className="space-y-5">
              {groups.map((grp) => {
                const groupOpts = options.filter((o) => o.group === grp);
                const groupTitle = grp.charAt(0).toUpperCase() + grp.slice(1);
                return (
                  <div key={grp} className="p-4 rounded-xl bg-slate-50/70 border border-slate-200">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                      {groupTitle}
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {groupOpts.map((opt) => {
                        const selected = isMulti && multi.includes(opt.value);
                        return (
                          <button
                            key={opt.value}
                            disabled={busy}
                            className={`tap flex items-center gap-3 text-left py-3.5 px-4 ${selected ? "tap-selected" : ""}`}
                            onClick={() => {
                              if (isMulti) {
                                toggleMulti(opt.value);
                              } else {
                                stopSpeaking();
                                onSubmit({ touch_value: opt.value });
                              }
                            }}
                          >
                            <span className="text-2xl">{ICONS[opt.icon] || (selected ? "☑️" : "⬜")}</span>
                            <span className="text-base font-medium">{opt.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {options.map((opt) => {
                const selected = isMulti && multi.includes(opt.value);
                return (
                  <button
                    key={opt.value}
                    disabled={busy}
                    className={`tap flex items-center gap-3 text-left ${selected ? "tap-selected" : ""}`}
                    onClick={() => {
                      if (isMulti) {
                        toggleMulti(opt.value);
                      } else {
                        stopSpeaking();
                        onSubmit({ touch_value: opt.value });
                      }
                    }}
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
              className="tap tap-selected w-full mt-5 py-5 text-xl font-bold"
              disabled={busy || multi.length === 0}
              onClick={() => {
                stopSpeaking();
                onSubmit({ touch_value: multi });
              }}
            >
              {t(lang, "done")}
            </button>
          )}
        </>
      )}

      {/* Optional Question Skip Link */}
      {question.optional && !isInfoScreen && (
        <div className="mt-4 pt-3 border-t border-slate-100 text-center">
          <button
            type="button"
            className="text-sm font-semibold text-slate-400 hover:text-slate-600 transition underline underline-offset-4"
            disabled={busy}
            onClick={() => {
              stopSpeaking();
              onSubmit({ touch_value: "prefer_not_to_answer" });
            }}
          >
            {t(lang, "ayushOptionalSkip")}
          </button>
        </div>
      )}
    </div>
  );
}
