import React, { useState, useEffect } from 'react';
import { getTransactionDetail, submitDecision } from '../services/api';
import ScorePill from './ScorePill';
import Badge from './Badge';
import { X, ShieldCheck, ShieldAlert, CheckCircle2, DollarSign, Clock, FileText, ChevronDown, ChevronUp } from 'lucide-react';

export default function TransactionDetailDrawer({ transactionId, onClose, onDecisionSubmitted }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Decision Form State
  const [decision, setDecision] = useState('confirm-block');
  const [reasonText, setReasonText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  // Raw data toggle state
  const [showRaw, setShowRaw] = useState(false);

  useEffect(() => {
    async function loadDetail() {
      if (!transactionId) return;
      try {
        setLoading(true);
        setError('');
        const data = await getTransactionDetail(transactionId);
        setDetail(data);
      } catch (err) {
        setError(err.message || 'Failed to load transaction details.');
      } finally {
        setLoading(false);
      }
    }
    loadDetail();
  }, [transactionId]);

  const handleDecisionSubmit = async (e) => {
    e.preventDefault();
    setFormError('');

    const trimmed = reasonText.trim();
    // VR-3 check client-side
    if (trimmed.length < 10) {
      setFormError('Reason text must be at least 10 characters long (VR-3).');
      return;
    }

    setSubmitting(true);

    try {
      await submitDecision(transactionId, decision, trimmed);
      if (onDecisionSubmitted) {
        onDecisionSubmitted(transactionId, decision);
      }
      onClose();
    } catch (err) {
      // EC-5 concurrent decision handling
      setFormError(err.message || 'Failed to record decision.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!transactionId) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/60 backdrop-blur-sm flex justify-end">
      <div className="w-full max-w-xl bg-slate-900 border-l border-slate-800 h-full flex flex-col shadow-2xl overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between sticky top-0 bg-slate-900/90 backdrop-blur-md z-10">
          <div>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">Transaction Details</span>
            <h2 className="text-xl font-bold text-white font-mono">{transactionId}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400 text-sm">Loading transaction details...</div>
        ) : error ? (
          <div className="p-8 text-center text-rose-400 text-sm">{error}</div>
        ) : detail ? (
          <div className="p-6 space-y-6 flex-1">
            {/* Top Stat Summary */}
            <div className="grid grid-cols-2 gap-4 bg-slate-950 p-4 rounded-xl border border-slate-800/80">
              <div>
                <span className="text-[11px] font-medium text-slate-400">Amount</span>
                <p className="text-xl font-bold text-white font-sans mt-0.5">₹{detail.amount?.toLocaleString('en-IN')}</p>
              </div>
              <div>
                <span className="text-[11px] font-medium text-slate-400">Risk Score & Outcome</span>
                <div className="mt-1">
                  <ScorePill score={detail.score} outcome={detail.routing_outcome} />
                </div>
              </div>
            </div>

            {/* Decision Engine Origin */}
            <div className="flex items-center justify-between text-xs p-3 bg-slate-950/60 rounded-xl border border-slate-800/60">
              <span className="text-slate-400">Decision Layer Origin:</span>
              <Badge decidedBy={detail.decided_by} ruleName={detail.rule_name} />
            </div>

            {/* Reason Chain Section (FR-4) */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-blue-400" />
                Plain-Language Reason Chain (FR-4)
              </h3>

              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-2 font-sans">
                {detail.reason_bullets && detail.reason_bullets.length > 0 ? (
                  detail.reason_bullets.map((bullet, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-200">
                      <span className="text-blue-400 mt-0.5 font-bold">•</span>
                      <span>{bullet}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-500 italic">No explicit signals flagged for this transaction.</p>
                )}
              </div>
            </div>

            {/* Cost Estimate Comparison Panel (FR-6) */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <DollarSign className="w-4 h-4 text-emerald-400" />
                Financial Error Cost Estimates (FR-6)
              </h3>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3.5 bg-slate-950 border border-amber-500/20 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-amber-400 block">False Positive Cost</span>
                  <span className="text-lg font-bold text-white font-mono mt-0.5 block">
                    ₹{detail.fp_cost_estimate ? detail.fp_cost_estimate.toLocaleString('en-IN') : 'N/A'}
                  </span>
                  <span className="text-[10px] text-slate-400">If legit user is blocked</span>
                </div>

                <div className="p-3.5 bg-slate-950 border border-rose-500/20 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-rose-400 block">False Negative Cost</span>
                  <span className="text-lg font-bold text-white font-mono mt-0.5 block">
                    ₹{detail.fn_cost_estimate ? detail.fn_cost_estimate.toLocaleString('en-IN') : 'N/A'}
                  </span>
                  <span className="text-[10px] text-slate-400">If fraud is missed</span>
                </div>
              </div>
            </div>

            {/* Analyst Decision Panel OR Past Decision Log */}
            {detail.decision ? (
              <div className="bg-slate-950 border border-purple-500/30 rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-purple-400 uppercase tracking-wider">Recorded Analyst Override</span>
                  <span className="text-slate-400 font-mono text-[10px]">
                    {new Date(detail.decision.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                    detail.decision.decision === 'confirm-block' ? 'bg-rose-500/20 text-rose-300' : 'bg-emerald-500/20 text-emerald-300'
                  }`}>
                    {detail.decision.decision}
                  </span>
                  <span className="text-xs text-slate-300 font-mono">by {detail.decision.actor_id}</span>
                </div>
                <p className="text-xs text-slate-300 italic bg-slate-900 p-2.5 rounded border border-slate-800">
                  "{detail.decision.reason_text}"
                </p>
              </div>
            ) : (
              <form onSubmit={handleDecisionSubmit} className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-4">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Record Analyst Decision (FR-9)</h3>

                {/* Decision Radio Choice */}
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setDecision('confirm-block')}
                    className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all flex items-center justify-center gap-1.5 ${
                      decision === 'confirm-block'
                        ? 'bg-rose-600 border-rose-500 text-white shadow-lg shadow-rose-600/20'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
                    }`}
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    Confirm Block
                  </button>

                  <button
                    type="button"
                    onClick={() => setDecision('confirm-clear')}
                    className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all flex items-center justify-center gap-1.5 ${
                      decision === 'confirm-clear'
                        ? 'bg-emerald-600 border-emerald-500 text-white shadow-lg shadow-emerald-600/20'
                        : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
                    }`}
                  >
                    <ShieldCheck className="w-3.5 h-3.5" />
                    Confirm Clear
                  </button>
                </div>

                {/* Reason Input */}
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-[11px] font-semibold text-slate-300">Decision Reason (Required, min 10 chars)</label>
                    <span className={`text-[10px] font-mono ${reasonText.trim().length >= 10 ? 'text-emerald-400' : 'text-slate-500'}`}>
                      {reasonText.trim().length}/10 chars
                    </span>
                  </div>
                  <textarea
                    rows={3}
                    required
                    value={reasonText}
                    onChange={(e) => setReasonText(e.target.value)}
                    placeholder="Enter detailed reason for override decision..."
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                  />
                </div>

                {formError && (
                  <p className="text-xs text-rose-400">{formError}</p>
                )}

                <button
                  type="submit"
                  disabled={submitting || reasonText.trim().length < 10}
                  className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg transition-all shadow-md shadow-blue-600/20 disabled:opacity-50"
                >
                  {submitting ? 'Submitting & Logging Audit Entry...' : 'Submit Final Decision & Log Audit'}
                </button>
              </form>
            )}

            {/* Collapsible Raw Transaction Data Accordion */}
            <div className="border border-slate-800/80 rounded-xl overflow-hidden">
              <button
                onClick={() => setShowRaw(!showRaw)}
                className="w-full px-4 py-2.5 bg-slate-950 text-left text-xs font-semibold text-slate-400 hover:text-white flex items-center justify-between"
              >
                <span>Raw Ingested Fields</span>
                {showRaw ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {showRaw && (
                <div className="p-4 bg-slate-950/50 font-mono text-[11px] text-slate-300 space-y-1.5 border-t border-slate-800">
                  <p><span className="text-slate-500">device_id:</span> {detail.device_id}</p>
                  <p><span className="text-slate-500">is_new_device:</span> {String(detail.is_new_device)}</p>
                  <p><span className="text-slate-500">ip_country:</span> {detail.ip_country}</p>
                  <p><span className="text-slate-500">billing_country:</span> {detail.billing_country}</p>
                  <p><span className="text-slate-500">shipping_country:</span> {detail.shipping_country || 'null (digital)'}</p>
                  <p><span className="text-slate-500">account_age_days:</span> {detail.account_age_days}</p>
                  <p><span className="text-slate-500">velocity_10min:</span> {detail.velocity_10min}</p>
                  <p><span className="text-slate-500">avg_user_amount:</span> ₹{detail.avg_user_amount}</p>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
