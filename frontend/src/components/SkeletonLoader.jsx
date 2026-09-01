import React from 'react';

export default function SkeletonLoader({ rows = 4 }) {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-14 bg-slate-800/60 border border-slate-700/50 rounded-xl" />
      ))}
    </div>
  );
}
