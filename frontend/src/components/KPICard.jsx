import React from 'react';

export default function KPICard({ title, value, subtitle, icon: Icon, color = 'blue' }) {
  const colorStyles = {
    blue: 'border-blue-500/20 bg-blue-500/5 text-blue-400',
    emerald: 'border-emerald-500/20 bg-emerald-500/5 text-emerald-400',
    purple: 'border-purple-500/20 bg-purple-500/5 text-purple-400',
    amber: 'border-amber-500/20 bg-amber-500/5 text-amber-400',
    rose: 'border-rose-500/20 bg-rose-500/5 text-rose-400',
  }[color] || 'border-slate-700 bg-slate-800 text-slate-300';

  return (
    <div className="bg-slate-800/90 border border-slate-700/80 rounded-xl p-5 shadow-lg backdrop-blur-sm">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{title}</span>
        {Icon && (
          <div className={`p-2 rounded-lg ${colorStyles}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
      <div className="mt-3">
        <span className="text-3xl font-bold tracking-tight text-white">{value}</span>
      </div>
      {subtitle && (
        <p className="mt-1 text-xs text-slate-400 font-normal">{subtitle}</p>
      )}
    </div>
  );
}
