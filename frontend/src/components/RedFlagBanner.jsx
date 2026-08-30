import { useState } from "react";
import { t } from "../i18n";

// Sticky priority alert driven by the backend rule engine (red_flags.py).
// T2 requirement: impossible to miss (color, icon, sticky) with an "acknowledge" action.
export default function RedFlagBanner({ lang, flags = [], onAcknowledge }) {
  const [acknowledged, setAcknowledged] = useState({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [expanded, setExpanded] = useState(false);

  if (!flags || flags.length === 0) return null;

  const activeIndex = Math.min(currentIndex, flags.length - 1);
  const flag = flags[activeIndex] || flags[0];
  const isHigh = flag.priority === "HIGH";
  const flagId = flag.id || `${flag.label}-${activeIndex}`;
  const ackData = acknowledged[flagId];
  const allAcknowledged = flags.every((f, i) => acknowledged[f.id || `${f.label}-${i}`]);

  function handleAck(e) {
    e?.stopPropagation();
    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const updated = {
      ...acknowledged,
      [flagId]: { time: now, acknowledged: true },
    };
    setAcknowledged(updated);
    if (onAcknowledge) onAcknowledge(flagId, updated);
  }

  return (
    <aside
      aria-label="Clinical Priority Alert"
      role="alert"
      className={`sticky top-0 z-50 w-full transition-all duration-300 shadow-lg border-b ${
        allAcknowledged
          ? "bg-slate-900 border-slate-700 text-slate-100"
          : isHigh
          ? "bg-gradient-to-r from-red-700 via-red-600 to-rose-700 border-red-800 text-white animate-pulse-subtle"
          : "bg-gradient-to-r from-amber-600 via-amber-500 to-yellow-600 border-amber-700 text-white"
      }`}
    >
      <div className="max-w-5xl mx-auto px-4 py-3 sm:px-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Left: Icon + Alert Details */}
          <div className="flex items-start gap-3.5 flex-1 min-w-0">
            <div
              className={`p-2 rounded-xl flex-shrink-0 flex items-center justify-center ${
                allAcknowledged
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                  : isHigh
                  ? "bg-white/20 text-white shadow-inner animate-bounce-gentle"
                  : "bg-black/20 text-white"
              }`}
            >
              {allAcknowledged ? (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : isHigh ? (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-0.5">
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-black tracking-wider uppercase ${
                    allAcknowledged
                      ? "bg-emerald-400 text-emerald-950"
                      : isHigh
                      ? "bg-white text-red-700 shadow-sm"
                      : "bg-amber-950 text-amber-200"
                  }`}
                >
                  {isHigh ? "🚨 " : "⚠️ "}
                  {t(lang, "redFlag")} · {flag.priority || "HIGH"}
                </span>

                {flags.length > 1 && (
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-black/25 text-white">
                    {activeIndex + 1} / {flags.length}
                  </span>
                )}

                {ackData ? (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-300 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded-md">
                    ✓ {t(lang, "acknowledgedByDoctor")} ({ackData.time})
                  </span>
                ) : (
                  <span className="text-xs text-white/90 underline font-medium">
                    {t(lang, "criticalActionNeeded")}
                  </span>
                )}
              </div>

              <div className="font-bold text-base md:text-lg leading-snug break-words">
                {flag.label}
              </div>

              <div className="mt-1 text-xs md:text-sm bg-black/20 rounded-lg px-3 py-1.5 inline-block font-medium border border-white/10">
                <span className="text-white/80 uppercase font-semibold text-[10px] mr-1.5 tracking-wider">ACTION:</span>
                <span className="text-white font-bold">{flag.action}</span>
              </div>
            </div>
          </div>

          {/* Right: Controls & Acknowledge Action */}
          <div className="flex items-center gap-2 self-end md:self-center flex-shrink-0">
            {flags.length > 1 && (
              <div className="flex items-center gap-1 bg-black/25 rounded-lg p-1">
                <button
                  type="button"
                  onClick={() => setCurrentIndex((prev) => (prev > 0 ? prev - 1 : flags.length - 1))}
                  className="p-1 hover:bg-white/20 rounded text-white text-xs font-bold"
                  title="Previous flag"
                >
                  ◀
                </button>
                <button
                  type="button"
                  onClick={() => setCurrentIndex((prev) => (prev < flags.length - 1 ? prev + 1 : 0))}
                  className="p-1 hover:bg-white/20 rounded text-white text-xs font-bold"
                  title="Next flag"
                >
                  ▶
                </button>
              </div>
            )}

            {ackData ? (
              <button
                type="button"
                onClick={handleAck}
                className="text-xs px-3 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg shadow-sm transition flex items-center gap-1.5"
              >
                <span>✓</span>
                <span>{t(lang, "acknowledged")}</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={handleAck}
                className={`text-sm px-4 py-2 font-bold rounded-lg shadow-md transition transform active:scale-95 flex items-center gap-1.5 ${
                  isHigh
                    ? "bg-white text-red-700 hover:bg-red-50 hover:shadow-lg ring-2 ring-white/50"
                    : "bg-slate-900 text-white hover:bg-slate-800"
                }`}
              >
                <svg className="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                {t(lang, "acknowledgeAlert")}
              </button>
            )}

            {flags.length > 1 && (
              <button
                type="button"
                onClick={() => setExpanded(!expanded)}
                className="text-xs bg-white/10 hover:bg-white/20 text-white px-2.5 py-2 rounded-lg font-medium"
              >
                {expanded ? "▲ Hide all" : `▼ All (${flags.length})`}
              </button>
            )}
          </div>
        </div>

        {/* Expandable multi-flags list */}
        {expanded && flags.length > 1 && (
          <div className="mt-3 pt-3 border-t border-white/20 space-y-2">
            <div className="text-xs font-bold uppercase tracking-wider text-white/80">
              All Active Priority Flags ({flags.length}):
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {flags.map((f, idx) => {
                const fId = f.id || `${f.label}-${idx}`;
                const isAck = acknowledged[fId];
                return (
                  <div
                    key={idx}
                    onClick={() => setCurrentIndex(idx)}
                    className={`p-2.5 rounded-lg border text-xs cursor-pointer transition ${
                      idx === activeIndex
                        ? "bg-white/20 border-white font-medium shadow-sm"
                        : "bg-black/20 border-white/10 hover:bg-white/10"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-1 mb-1">
                      <span className="font-bold uppercase tracking-wide">
                        [{f.priority}] {f.label}
                      </span>
                      {isAck ? (
                        <span className="text-emerald-300 font-bold">✓ Ack</span>
                      ) : (
                        <span className="text-amber-200">Pending</span>
                      )}
                    </div>
                    <div className="text-white/90 text-[11px] truncate">
                      Action: {f.action}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
