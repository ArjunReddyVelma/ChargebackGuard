import React from 'react';
import { Cpu, Sparkles, ShieldAlert } from 'lucide-react';

export default function Badge({ decidedBy, ruleName }) {
  if (decidedBy === 'rule') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-blue-500/30 bg-blue-500/10 text-blue-400 text-xs font-medium">
        <Cpu className="w-3 h-3" />
        Rule Engine {ruleName ? `(${ruleName})` : ''}
      </span>
    );
  }
  
  if (decidedBy === 'llm') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-purple-500/30 bg-purple-500/10 text-purple-300 text-xs font-medium">
        <Sparkles className="w-3 h-3" />
        Claude 3.5 LLM
      </span>
    );
  }

  if (decidedBy === 'degraded_reasoning') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-slate-500/30 bg-slate-500/10 text-slate-400 text-xs font-medium">
        <ShieldAlert className="w-3 h-3" />
        Rule Fallback (ER-2)
      </span>
    );
  }

  return <span className="text-xs text-slate-500">{decidedBy || 'Unknown'}</span>;
}
