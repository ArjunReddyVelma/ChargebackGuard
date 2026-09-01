import React, { useState, useEffect } from 'react';
import { getAuditLog } from '../services/api';
import SkeletonLoader from '../components/SkeletonLoader';
import { FileText, Shield, User, Clock, ChevronDown, ChevronUp } from 'lucide-react';

export default function AuditLogView() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedLogId, setExpandedLogId] = useState(null);
  const [eventTypeFilter, setEventTypeFilter] = useState('');

  useEffect(() => {
    async function loadAudit() {
      try {
        setLoading(true);
        const data = await getAuditLog(eventTypeFilter || null);
        setLogs(data.items || []);
      } catch (err) {
        console.error('Failed to load audit log', err);
      } finally {
        setLoading(false);
      }
    }
    loadAudit();
  }, [eventTypeFilter]);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <FileText className="w-6 h-6 text-purple-400" />
            Immutable Audit Trail Log (BR-1 / FR-10)
          </h1>
          <p className="text-slate-400 text-xs mt-1">
            Append-only, immutable record of all transaction scores, analyst overrides, and risk threshold configuration changes.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-900 p-1 border border-slate-800 rounded-xl text-xs">
          <button
            onClick={() => setEventTypeFilter('')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
              eventTypeFilter === '' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            All Events
          </button>
          <button
            onClick={() => setEventTypeFilter('override')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
              eventTypeFilter === 'override' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Overrides Only
          </button>
          <button
            onClick={() => setEventTypeFilter('config_change')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
              eventTypeFilter === 'config_change' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Config Changes
          </button>
        </div>
      </div>

      {loading ? (
        <SkeletonLoader rows={6} />
      ) : logs.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 text-sm">
          No audit log events found for this filter.
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-slate-400 uppercase tracking-wider border-b border-slate-800 bg-slate-950/60">
                <tr>
                  <th className="py-3.5 px-4">Timestamp (UTC)</th>
                  <th className="py-3.5 px-4">Event Type</th>
                  <th className="py-3.5 px-4">Actor</th>
                  <th className="py-3.5 px-4">Target ID</th>
                  <th className="py-3.5 px-4">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {logs.map((item) => {
                  const isExpanded = expandedLogId === item.log_id;
                  return (
                    <React.Fragment key={item.log_id}>
                      <tr
                        onClick={() => setExpandedLogId(isExpanded ? null : item.log_id)}
                        className="hover:bg-slate-800/60 cursor-pointer transition-colors"
                      >
                        <td className="py-3.5 px-4 font-sans text-slate-400 text-[11px]">
                          {new Date(item.timestamp).toLocaleString()}
                        </td>
                        <td className="py-3.5 px-4 font-sans">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            item.event_type === 'override'
                              ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                              : item.event_type === 'config_change'
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                          }`}>
                            {item.event_type}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-sans text-white font-medium">
                          {item.actor_id} ({item.actor_role})
                        </td>
                        <td className="py-3.5 px-4 text-blue-400">
                          {item.transaction_id || '-'}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button className="text-slate-400 hover:text-white">
                            {isExpanded ? <ChevronUp className="w-4 h-4 inline" /> : <ChevronDown className="w-4 h-4 inline" />}
                          </button>
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr>
                          <td colSpan={5} className="bg-slate-950 p-4 font-mono text-xs text-slate-300 border-t border-b border-slate-800">
                            <div className="bg-slate-900 p-3 rounded-xl border border-slate-800/80 overflow-x-auto">
                              <pre className="text-emerald-400 text-[11px]">
                                {JSON.stringify(item.details, null, 2)}
                              </pre>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
