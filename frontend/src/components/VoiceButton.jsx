import { useEffect, useRef, useState } from "react";
import { SPEECH_LANG, t } from "../i18n";

// Live voice via the browser Web Speech API (zero setup for the demo).
// PRODUCTION: replace with streaming to /api/asr (faster-whisper / Bhashini) so it
// works offline and in regional languages with a real confidence score.
export default function VoiceButton({ lang, onResult, disabled }) {
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(true);
  const recRef = useRef(null);
  const cbRef = useRef(onResult);

  useEffect(() => {
    cbRef.current = onResult;
  });

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setSupported(false);
      return;
    }
    const rec = new SR();
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (e) => {
      const alt = e.results[0][0];
      const conf = typeof alt.confidence === "number" && alt.confidence > 0 ? alt.confidence : 0.8;
      cbRef.current(alt.transcript, conf);
      setListening(false);
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    recRef.current = rec;
    return () => {
      try {
        rec.abort();
      } catch (_) {}
    };
  }, []);

  function toggle() {
    if (!supported || disabled || !recRef.current) return;
    if (listening) {
      recRef.current.stop();
      setListening(false);
      return;
    }
    try {
      recRef.current.lang = SPEECH_LANG[lang] || "en-IN";
      recRef.current.start();
      setListening(true);
    } catch (_) {
      setListening(false);
    }
  }

  if (!supported) {
    return <p className="text-sm text-slate-500 text-center py-2">{t(lang, "voiceUnsupported")}</p>;
  }

  return (
    <button
      onClick={toggle}
      disabled={disabled}
      className={`w-full rounded-2xl py-6 text-xl font-semibold text-white transition disabled:opacity-50 ${
        listening ? "bg-kiosk-danger animate-pulse" : "bg-kiosk-accent hover:brightness-110"
      }`}
    >
      🎤 {listening ? t(lang, "listening") : t(lang, "speak")}
    </button>
  );
}
