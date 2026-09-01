import React, { useState, useEffect } from 'react';
import { getTransactions } from '../services/api';
import ScorePill from '../components/ScorePill';
import Badge from '../components/Badge';
import SkeletonLoader from '../components/SkeletonLoader';
import TransactionDetailDrawer from '../components/TransactionDetailDrawer';
import Toast from '../components/Toast';
import { ShieldAlert, Filter, CheckCircle2, RefreshCw } from 'lucide-react';

export default function ReviewQueueView({ initialSelectedId, onClearSelectedId }) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterOutcome, setFilterOutcome] = useState('review-queue');
  const [selectedTxId, setSelectedTxId] = useState(initialSelectedId || null);
  const [toastMessage, setToastMessage] = useState('');

  const loadQueue = async () => {
    try {
      setLoading(true);
      const data = await getTransactions({
        routing_outcome: filterOutcome || undefined,
        limit: 100
      });
      setTransactions(data.items || []);
    } catch (err) {
      console.error('Failed to fetch review queue', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, [filterOutcome]);

  useEffect(() => {
    if (initialSelectedId) {
      setSelectedTxId(initialSelectedId);
    }
  }, [initialSelectedId]);

  const handleDecisionSubmitted = (txId, decision) => {
    setToastMessage(`Decision '${decision}' recorded successfully for transaction ${txId}.`);
    // Optimistic row update (UI/UX Section 11)
    setTransactions((prev) => prev.filter((item) => item.transaction_id !== txId));
    if (onClearSelectedId) onClearSelectedId();
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Toast Notification */}
      {toastMessage && (
        <Toast
          message={toastMessage}
          type="success"
          onClose={() => setToastMessage('')}
        />
      )}

      {/* Header & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-amber-400" />
            Human-in-the-Loop Review Queue (FR-8)
          </h1>
          <p className="text-slate-400 text-xs mt-1">
            Borderline and high-risk transactions routed for human analyst override and audit trail logging.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Outcome Filter */}
          <div className="flex items-center gap-2 bg-slate-900 p-1 border border-slate-800 rounded-xl text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400 ml-2" />
            <button
              onClick={() => setFilterOutcome('review-queue')}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                filterOutcome === 'review-queue'
                  ? 'bg-amber-500/20 border border-amber-500/40 text-amber-300'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Needs Review
            </button>
            <button
              onClick={() => setFilterOutcome('')}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                filterOutcome === ''
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              All Scored
            </button>
          </div>

          <button
            onClick={loadQueue}
            className="p-2 bg-slate-900 border border-slate-800 text-slate-400 hover:text-white rounded-xl transition-colors"
            title="Refresh Queue"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Queue Table View */}
      {loading ? (
        <SkeletonLoader rows={6} />
      ) : transactions.length === 0 ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
          <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
          <h3 className="text-lg font-bold text-white">Review Queue is Clear!</h3>
          <p className="text-slate-400 text-xs max-w-sm mx-auto">
            No transactions currently require analyst decision in this filter view.
          </p>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-slate-400 uppercase tracking-wider border-b border-slate-800 bg-slate-950/60">
                <tr>
                  <th className="py-3.5 px-4">Transaction ID</th>
                  <th className="py-3.5 px-4">Amount</th>
                  <th className="py-3.5 px-4">Payment</th>
                  <th className="py-3.5 px-4">Risk Score</th>
                  <th className="py-3.5 px-4">Decision Origin</th>
                  <th className="py-3.5 px-4">FP Cost Est.</th>
                  <th className="py-3.5 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {transactions.map((tx) => (
                  <tr
                    key={tx.transaction_id}
                    onClick={() => setSelectedTxId(tx.transaction_id)}
                    className="hover:bg-slate-800/60 cursor-pointer transition-colors"
                  >
                    <td className="py-3.5 px-4 font-semibold text-blue-400">{tx.transaction_id}</td>
                    <td className="py-3.5 px-4 font-sans font-semibold text-white">₹{tx.amount?.toLocaleString('en-IN')}</td>
                    <td className="py-3.5 px-4 uppercase text-slate-400 font-sans">{tx.payment_method}</td>
                    <td className="py-3.5 px-4">
                      <ScorePill score={tx.score} outcome={tx.routing_outcome} />
                    </td>
                    <td className="py-3.5 px-4 font-sans">
                      <Badge decidedBy={tx.decided_by} />
                    </td>
                    <td className="py-3.5 px-4 text-amber-400 font-sans">
                      {tx.fp_cost_estimate ? `₹${tx.fp_cost_estimate}` : '-'}
                    </td>
                    <td className="py-3.5 px-4 font-sans">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase ${
                        tx.final_status === 'confirm-block'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : tx.final_status === 'confirm-clear'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      }`}>
                        {tx.final_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Transaction Detail Slide-Over Drawer */}
      {selectedTxId && (
        <TransactionDetailDrawer
          transactionId={selectedTxId}
          onClose={() => {
            setSelectedTxId(null);
            if (onClearSelectedId) onClearSelectedId();
          }}
          onDecisionSubmitted={handleDecisionSubmitted}
        />
      )}
    </div>
  );
}
