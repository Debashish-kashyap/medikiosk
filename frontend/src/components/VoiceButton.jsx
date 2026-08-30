import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { SPEECH_LANG, t } from "../i18n";

const SILENCE_MS = 2500;
const INITIAL_WAIT = 10000;
const MAX_RECORD = 30000;

function hasWebSpeech() {
  return Boolean(typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition));
}

// Preferred recording mime types in priority order
const PREFERRED_MIMES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/ogg",
  "audio/mp4",
  "audio/wav",
];

export default function VoiceButton({
  lang,
  questionId,
  autoVoice,
  onAutoVoiceToggle,
  onResult,
  disabled,
}) {
  const [listening, setListening] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [audioLevel, setAudioLevel] = useState(0); // 0 to 100 for live meter
  const [lastHeard, setLastHeard] = useState(null);
  const [engineMode, setEngineMode] = useState("server"); // "server" (faster-whisper) | "webspeech"
  const [serverStatus, setServerStatus] = useState(null);

  const onResultRef = useRef(onResult);
  const langRef = useRef(lang);
  const listeningRef = useRef(false);

  const mediaRecRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const mimeRef = useRef("audio/webm");
  const maxTimerRef = useRef(null);
  const audioCtxRef = useRef(null);
  const vadFrameRef = useRef(null);
  const srRef = useRef(null);

  useEffect(() => { onResultRef.current = onResult; }, [onResult]);
  useEffect(() => { langRef.current = lang; }, [lang]);

  // Check server ASR status on mount
  useEffect(() => {
    api.asrStatus()
      .then((status) => {
        setServerStatus(status);
        if (status?.available && status.engine === "faster-whisper") {
          setEngineMode("server");
        } else if (hasWebSpeech()) {
          setEngineMode("webspeech");
        }
      })
      .catch(() => {
        if (hasWebSpeech()) setEngineMode("webspeech");
      });
  }, []);

  // Web Speech instance setup
  useEffect(() => {
    if (!hasWebSpeech()) return;

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SR();
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.continuous = false;

    rec.onresult = (e) => {
      const alt = e.results[0][0];
      const conf = typeof alt.confidence === "number" && alt.confidence > 0 ? alt.confidence : 0.88;
      const text = (alt.transcript || "").trim();
      setListening(false);
      listeningRef.current = false;
      setErrorMsg(null);
      setLastHeard({ text, conf, engine: "Web Speech" });
      onResultRef.current(text, conf);
    };

    rec.onerror = (e) => {
      setListening(false);
      listeningRef.current = false;
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        setErrorMsg(t(langRef.current, "micPermissionDenied"));
      } else if (e.error === "audio-capture") {
        setErrorMsg(t(langRef.current, "micNotFound"));
      } else if (e.error === "no-speech") {
        setErrorMsg(t(langRef.current, "asrError"));
      } else if (e.error === "network") {
        // Fallback to server ASR
        setEngineMode("server");
        setErrorMsg("Web Speech network unavailable — switched to Server Whisper ASR.");
      } else {
        setErrorMsg(`Speech recognition error: ${e.error}`);
      }
    };

    rec.onend = () => {
      setListening(false);
      listeningRef.current = false;
    };

    srRef.current = rec;
    return () => {
      try { rec.abort(); } catch (_) {}
    };
  }, []);

  // Auto-voice trigger on question change
  useEffect(() => {
    if (autoVoice && !disabled) {
      const id = setTimeout(() => startRecording(), 400);
      return () => clearTimeout(id);
    }
  }, [questionId]);

  // Clean up on unmount
  useEffect(() => () => stopAll(), []);

  // ── Audio Context & Live Visualizer / VAD ──────────────────────────────────
  function startVAD(stream) {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      
      if (ctx.state === "suspended") {
        ctx.resume();
      }

      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.5;

      const source = ctx.createMediaStreamSource(stream);
      source.connect(analyser);
      audioCtxRef.current = ctx;

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      const t0 = Date.now();
      let heardSpeech = false;
      let lastSound = Date.now();

      function tick() {
        if (!listeningRef.current) return;
        analyser.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;
        // Normalize 0-100 for visualizer
        const normalized = Math.min(100, Math.round((avg / 128) * 100));
        setAudioLevel(normalized);

        const now = Date.now();
        if (avg > 12) {
          heardSpeech = true;
          lastSound = now;
        }

        // Silence after speech detected -> auto stop
        if (heardSpeech && now - lastSound > SILENCE_MS) {
          stopMedia();
          return;
        }

        // Initial silence timeout -> auto stop
        if (!heardSpeech && now - t0 > INITIAL_WAIT) {
          stopMedia();
          return;
        }

        vadFrameRef.current = requestAnimationFrame(tick);
      }

      vadFrameRef.current = requestAnimationFrame(tick);
    } catch (e) {
      console.warn("[VoiceButton] VAD init warning:", e);
    }
  }

  function stopVAD() {
    if (vadFrameRef.current) {
      cancelAnimationFrame(vadFrameRef.current);
      vadFrameRef.current = null;
    }
    if (audioCtxRef.current) {
      try { audioCtxRef.current.close(); } catch (_) {}
      audioCtxRef.current = null;
    }
    setAudioLevel(0);
  }

  // ── Server ASR MediaRecorder Path (faster-whisper) ──────────────────────────
  async function startServerCapture() {
    if (listeningRef.current || processing) return;
    listeningRef.current = true;
    setListening(true);
    setErrorMsg(null);

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    } catch (err) {
      console.error("[VoiceButton] getUserMedia error:", err);
      listeningRef.current = false;
      setListening(false);
      setErrorMsg(
        err.name === "NotFoundError" || err.name === "DevicesNotFoundError"
          ? t(langRef.current, "micNotFound")
          : t(langRef.current, "micPermissionDenied")
      );
      return;
    }

    streamRef.current = stream;
    chunksRef.current = [];

    const mime = PREFERRED_MIMES.find((m) => MediaRecorder.isTypeSupported(m)) || "";
    mimeRef.current = mime || "audio/webm";

    const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : {});
    mediaRecRef.current = rec;

    rec.ondataavailable = (e) => {
      if (e.data?.size > 0) chunksRef.current.push(e.data);
    };

    rec.onstop = async () => {
      clearTimeout(maxTimerRef.current);
      stopVAD();
      stream.getTracks().forEach((tr) => tr.stop());
      streamRef.current = null;
      mediaRecRef.current = null;

      const blobMime = rec.mimeType || mimeRef.current || "audio/webm";
      const blob = new Blob(chunksRef.current, { type: blobMime });
      setListening(false);
      listeningRef.current = false;

      if (!blob.size || blob.size < 200) {
        setErrorMsg(t(langRef.current, "asrError"));
        return;
      }

      setProcessing(true);
      try {
        const result = await api.transcribeAudio(blob, langRef.current);
        const text = (result.transcript || "").trim();
        const conf = typeof result.confidence === "number" ? result.confidence : 0.0;

        if (text) {
          setErrorMsg(null);
          setLastHeard({ text, conf, engine: result.engine || "faster-whisper" });
          onResultRef.current(text, conf);
        } else {
          setErrorMsg(t(langRef.current, "asrError"));
        }
      } catch (err) {
        console.error("[VoiceButton] ASR fetch error:", err);
        setErrorMsg(t(langRef.current, "asrError"));
      } finally {
        setProcessing(false);
      }
    };

    rec.start();
    startVAD(stream);

    maxTimerRef.current = setTimeout(() => {
      if (listeningRef.current) stopMedia();
    }, MAX_RECORD);
  }

  function stopMedia() {
    clearTimeout(maxTimerRef.current);
    stopVAD();
    const rec = mediaRecRef.current;
    if (rec && rec.state === "recording") {
      try { rec.stop(); } catch (_) {}
    }
  }

  // ── Web Speech API Path ───────────────────────────────────────────────────
  function startWebSpeech() {
    if (!srRef.current) {
      setEngineMode("server");
      startServerCapture();
      return;
    }
    setErrorMsg(null);
    try {
      srRef.current.lang = SPEECH_LANG[langRef.current] || "en-IN";
      srRef.current.start();
      setListening(true);
      listeningRef.current = true;
    } catch (e) {
      console.warn("[VoiceButton] Web Speech start error:", e);
      // Fallback to server
      setEngineMode("server");
      startServerCapture();
    }
  }

  function stopWebSpeech() {
    try { srRef.current?.stop(); } catch (_) {}
    setListening(false);
    listeningRef.current = false;
  }

  // ── Unified Controls ──────────────────────────────────────────────────────
  function startRecording() {
    if (disabled || processing) return;
    if (engineMode === "webspeech") {
      startWebSpeech();
    } else {
      startServerCapture();
    }
  }

  function stopRecording() {
    if (engineMode === "webspeech") {
      stopWebSpeech();
    } else {
      stopMedia();
    }
  }

  function stopAll() {
    stopMedia();
    try { srRef.current?.abort(); } catch (_) {}
    setListening(false);
    listeningRef.current = false;
    setProcessing(false);
    stopVAD();
  }

  function toggle() {
    if (disabled || processing) return;
    if (listening) {
      stopRecording();
    } else {
      startRecording();
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Primary Voice Action Button */}
      <button
        type="button"
        onClick={toggle}
        disabled={disabled || processing}
        className={`w-full rounded-2xl py-6 px-4 text-xl font-bold text-white transition-all transform active:scale-[0.99] shadow-md flex items-center justify-center gap-3 relative overflow-hidden ${
          processing
            ? "bg-slate-700 cursor-wait"
            : listening
            ? "bg-gradient-to-r from-red-600 to-rose-600 ring-4 ring-red-300 animate-pulse"
            : "bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 hover:shadow-lg"
        } disabled:opacity-50`}
      >
        {/* Live Audio Level Wave / Glow Background */}
        {listening && audioLevel > 0 && (
          <div
            className="absolute inset-0 bg-white/20 transition-all pointer-events-none"
            style={{ width: `${Math.min(100, audioLevel * 1.8)}%` }}
          />
        )}

        <span className="text-2xl relative z-10">
          {processing ? "🧠" : listening ? "🔴" : "🎤"}
        </span>

        <span className="relative z-10 tracking-wide">
          {processing
            ? t(lang, "asrProcessing")
            : listening
            ? `${t(lang, "listening")} (Tap to finish)`
            : t(lang, "speak")}
        </span>

        {/* Live sound level bars when recording */}
        {listening && (
          <div className="flex items-center gap-1 h-5 relative z-10 ml-2">
            {[40, 80, 60, 100, 50].map((h, i) => (
              <span
                key={i}
                className="w-1 bg-white rounded-full transition-all duration-75"
                style={{
                  height: `${Math.max(4, (audioLevel / 100) * h)}px`,
                  opacity: audioLevel > 5 ? 1 : 0.4,
                }}
              />
            ))}
          </div>
        )}
      </button>

      {/* Engine & Mode Switcher Bar */}
      <div className="flex items-center justify-between text-xs text-slate-500 px-1 flex-wrap gap-2">
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-slate-600">Engine:</span>
          <button
            type="button"
            onClick={() => setEngineMode("server")}
            className={`px-2.5 py-0.5 rounded-full font-mono text-[11px] transition ${
              engineMode === "server"
                ? "bg-teal-700 text-white font-bold shadow-sm"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            🚀 Server Whisper ({serverStatus?.model || "tiny"})
          </button>
          {hasWebSpeech() && (
            <button
              type="button"
              onClick={() => setEngineMode("webspeech")}
              className={`px-2.5 py-0.5 rounded-full font-mono text-[11px] transition ${
                engineMode === "webspeech"
                  ? "bg-indigo-700 text-white font-bold shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              🌐 Browser Web Speech
            </button>
          )}
        </div>

        {onAutoVoiceToggle && (
          <label className="flex items-center gap-1.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoVoice || false}
              onChange={(e) => onAutoVoiceToggle(e.target.checked)}
              className="accent-teal-600 rounded"
            />
            <span>{lang === "hi" ? "माइक स्वतः शुरू करें" : "Auto-listen next question"}</span>
          </label>
        )}
      </div>

      {/* Last Heard Recognition Feedback */}
      {lastHeard && !errorMsg && !listening && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-2.5 text-xs text-emerald-900 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>🗣️</span>
            <span>
              Heard: <b>“{lastHeard.text}”</b>
            </span>
          </div>
          <span className="font-mono text-[10px] bg-white px-2 py-0.5 rounded border border-emerald-300 font-bold text-emerald-800">
            {Math.round(lastHeard.conf * 100)}% conf ({lastHeard.engine})
          </span>
        </div>
      )}

      {/* Error Callout */}
      {errorMsg && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-xs text-red-700 flex items-center justify-between gap-2">
          <span>⚠️ {errorMsg}</span>
          <button
            type="button"
            onClick={toggle}
            className="px-2.5 py-1 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold text-[11px] whitespace-nowrap"
          >
            Retry 🎤
          </button>
        </div>
      )}
    </div>
  );
}
