import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { SPEECH_LANG, t } from "../i18n";

// Default: live voice via the browser Web Speech API (zero setup for the demo).
// Fallback / kiosk path: MediaRecorder → POST /api/asr (faster-whisper when enabled).
// Force the server path with VITE_USE_SERVER_ASR=1 even if Web Speech exists.
const USE_SERVER_ASR = String(import.meta.env.VITE_USE_SERVER_ASR || "") === "1";

function hasWebSpeech() {
  return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
}

export default function VoiceButton({ lang, onResult, disabled }) {
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(true);
  const recRef = useRef(null);
  const mediaRecRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const cbRef = useRef(onResult);
  const langRef = useRef(lang);
  const serverPath = USE_SERVER_ASR || !hasWebSpeech();

  useEffect(() => {
    cbRef.current = onResult;
  });

  useEffect(() => {
    langRef.current = lang;
  }, [lang]);

  useEffect(() => {
    if (serverPath) {
      setSupported(Boolean(navigator.mediaDevices && window.MediaRecorder));
      return;
    }
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
  }, [serverPath]);

  function stopMedia() {
    const rec = mediaRecRef.current;
    if (rec && rec.state === "recording") rec.stop();
  }

  async function startServerCapture() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;
    chunksRef.current = [];
    const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
    const rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
    mediaRecRef.current = rec;
    rec.ondataavailable = (e) => {
      if (e.data && e.data.size) chunksRef.current.push(e.data);
    };
    rec.onstop = async () => {
      stream.getTracks().forEach((tr) => tr.stop());
      streamRef.current = null;
      mediaRecRef.current = null;
      const blob = new Blob(chunksRef.current, { type: rec.mimeType || "audio/webm" });
      setListening(false);
      if (!blob.size) return;
      try {
        const result = await api.transcribeAudio(blob, langRef.current);
        const text = (result.transcript || "").trim();
        const conf = typeof result.confidence === "number" ? result.confidence : 0.0;
        if (text) cbRef.current(text, conf);
      } catch (_) {
        cbRef.current("", 0.0);
      }
    };
    rec.start();
    setListening(true);
  }

  async function toggle() {
    if (!supported || disabled) return;
    if (serverPath) {
      if (listening) {
        stopMedia();
        return;
      }
      try {
        await startServerCapture();
      } catch (_) {
        setListening(false);
      }
      return;
    }
    if (!recRef.current) return;
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
