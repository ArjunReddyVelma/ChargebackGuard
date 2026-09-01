import React, { useEffect } from 'react';
import { CheckCircle2, AlertTriangle, XCircle, X } from 'lucide-react';

export default function Toast({ message, type = 'success', onClose }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const styles = {
    success: 'bg-emerald-950/90 border-emerald-500/40 text-emerald-200',
    error: 'bg-rose-950/90 border-rose-500/40 text-rose-200',
    warning: 'bg-amber-950/90 border-amber-500/40 text-amber-200',
  }[type] || 'bg-slate-800 border-slate-700 text-white';

  const Icon = {
    success: CheckCircle2,
    error: XCircle,
    warning: AlertTriangle,
  }[type] || CheckCircle2;

  return (
    <div className={`fixed bottom-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-lg border shadow-xl backdrop-blur-md transition-all duration-300 ${styles}`}>
      <Icon className="w-5 h-5 flex-shrink-0" />
      <span className="text-sm font-medium">{message}</span>
      <button onClick={onClose} className="p-1 hover:opacity-80 rounded ml-2">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
