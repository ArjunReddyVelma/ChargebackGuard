import React from 'react';

export default function ScorePill({ score, outcome }) {
  let styles = 'bg-slate-700 text-slate-300 border-slate-600';
  let label = outcome || 'Scored';

  if (outcome === 'auto-clear' || score < 30) {
    styles = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    label = 'Auto Clear';
  } else if (outcome === 'review-queue' || (score >= 30 && score <= 70)) {
    styles = 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    label = 'Needs Review';
  } else if (outcome === 'auto-block' || score > 70) {
    styles = 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    label = 'Auto Block';
  }

  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold ${styles}`}>
      <span className="font-mono text-sm">{score}</span>
      <span className="text-[10px] uppercase tracking-wider font-medium opacity-80">({label})</span>
    </div>
  );
}
