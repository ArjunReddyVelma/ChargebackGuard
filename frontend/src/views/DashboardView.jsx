import React, { useEffect, useState } from 'react';
import { getMetrics, getTransactions } from '../services/api';
import KPICard from '../components/KPICard';
import ScorePill from '../components/ScorePill';
import Badge from '../components/Badge';
import SkeletonLoader from '../components/SkeletonLoader';
import { ShieldCheck, Target, Award, DollarSign, AlertOctagon, TrendingUp, ArrowRight, Cpu, Sparkles } from 'lucide-react';

export default function DashboardView({ onSelectTransaction, onUploadClick }) {
  const [metrics, setMetrics] = useState(null);
  const [recentTx, setRecentTx] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const metricsData = await getMetrics();
        setMetrics(metricsData);

        const txData = await getTransactions({ limit: 5 });
        setRecentTx(txData.items || []);
      } catch (err) {
        console.error('Failed to load dashboard data', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <SkeletonLoader rows={5} />
      </div>
    );
  }

  const hasData = metrics && metrics.total_scored > 0;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Risk & Precision Dashboard</h1>
          <p className="text-slate-400 text-xs mt-1">
            Real-time explainable detection metrics, cost exposure, and decision engine breakdown.
          </p>
        </div>
        <button
          onClick={onUploadClick}
          className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-xl transition-all shadow-lg shadow-blue-600/20 flex items-center gap-2"
        >
          Upload New Batch
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {!hasData ? (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-bold text-white">No Batch Data Scored Yet</h3>
          <p className="text-slate-400 text-xs max-w-md mx-auto">
            Upload your first synthetic or live transaction batch to see real precision, recall, cost exposure estimates, and rule vs LLM decision splits.
          </p>
          <button
            onClick={onUploadClick}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-xl transition-all shadow-lg shadow-blue-600/20 inline-flex items-center gap-2"
          >
            Upload First Batch Now
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <>
          {/* KPI Row (4 cards) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard
              title="Precision"
              value={`${(metrics.precision * 100).toFixed(1)}%`}
              subtitle="Accuracy of flagged transactions"
              icon={Target}
              color="blue"
            />
            <KPICard
              title="Recall"
              value={`${(metrics.recall * 100).toFixed(1)}%`}
              subtitle="Fraction of true fraud caught"
              icon={ShieldCheck}
              color="emerald"
            />
            <KPICard
              title="F1 Score"
              value={metrics.f1_score.toFixed(3)}
              subtitle="Harmonic mean of precision & recall"
              icon={Award}
              color="purple"
            />
            <KPICard
              title="Scored Volume"
              value={metrics.total_scored}
              subtitle="Total batch transactions processed"
              icon={TrendingUp}
              color="amber"
            />
          </div>

          {/* Cost Exposure & Decision Split Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Cost Exposure Summary Panel (2 cols) */}
            <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-bold text-white tracking-wide uppercase flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-emerald-400" />
                  Cost of Errors Exposure (FR-6 / FR-7)
                </h3>
                <span className="text-[10px] font-mono text-slate-500">Configurable Business Assumptions</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-slate-950/80 border border-amber-500/30 rounded-xl p-4">
                  <span className="text-xs font-medium text-amber-400 block mb-1">Estimated False-Positive Exposure</span>
                  <span className="text-2xl font-bold text-white font-mono">
                    ₹{metrics.total_fp_cost_exposure.toLocaleString('en-IN')}
                  </span>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Potential revenue margin lost & customer friction from flagged/reviewed legit transactions.
                  </p>
                </div>

                <div className="bg-slate-950/80 border border-rose-500/30 rounded-xl p-4">
                  <span className="text-xs font-medium text-rose-400 block mb-1">Estimated False-Negative Exposure</span>
                  <span className="text-2xl font-bold text-white font-mono">
                    ₹{metrics.total_fn_cost_exposure.toLocaleString('en-IN')}
                  </span>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Chargeback penalty fees & transaction loss from uncaught missed fraud.
                  </p>
                </div>
              </div>
            </div>

            {/* Rule vs LLM Split (1 col) */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
              <h3 className="text-sm font-bold text-white tracking-wide uppercase flex items-center gap-2 border-b border-slate-800 pb-3">
                <Cpu className="w-4 h-4 text-purple-400" />
                Rule vs LLM Layer Split (FR-13)
              </h3>

              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-xs font-semibold mb-1">
                    <span className="text-blue-400 flex items-center gap-1">
                      <Cpu className="w-3.5 h-3.5" /> Rule Engine
                    </span>
                    <span className="text-white font-mono">{metrics.rule_percent}% ({metrics.rule_decided_count})</span>
                  </div>
                  <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500" style={{ width: `${metrics.rule_percent}%` }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-semibold mb-1">
                    <span className="text-purple-400 flex items-center gap-1">
                      <Sparkles className="w-3.5 h-3.5" /> Claude LLM Reasoning
                    </span>
                    <span className="text-white font-mono">{metrics.llm_percent}% ({metrics.llm_decided_count + metrics.degraded_count})</span>
                  </div>
                  <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden">
                    <div className="h-full bg-purple-500" style={{ width: `${metrics.llm_percent}%` }} />
                  </div>
                </div>

                <p className="text-[11px] text-slate-400 pt-2 border-t border-slate-800/80">
                  Deterministic rules resolve clear-cut pass/block cases instantly; Claude LLM layer handles ambiguous cases with traceable reason chains.
                </p>
              </div>
            </div>
          </div>

          {/* Recent Scored Transactions List */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white tracking-wide uppercase">Recently Scored Transactions</h3>
              <span className="text-xs text-slate-400">Click row to open reason chain</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-slate-400 uppercase tracking-wider border-b border-slate-800 bg-slate-950/50">
                  <tr>
                    <th className="py-3 px-4">Transaction ID</th>
                    <th className="py-3 px-4">Amount</th>
                    <th className="py-3 px-4">Payment</th>
                    <th className="py-3 px-4">Risk Score</th>
                    <th className="py-3 px-4">Decided By</th>
                    <th className="py-3 px-4">FP Cost Est.</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                  {recentTx.map((tx) => (
                    <tr
                      key={tx.transaction_id}
                      onClick={() => onSelectTransaction(tx.transaction_id)}
                      className="hover:bg-slate-800/50 cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-4 font-semibold text-blue-400">{tx.transaction_id}</td>
                      <td className="py-3 px-4 font-sans font-medium text-white">₹{tx.amount.toLocaleString('en-IN')}</td>
                      <td className="py-3 px-4 uppercase text-slate-400 font-sans">{tx.payment_method}</td>
                      <td className="py-3 px-4">
                        <ScorePill score={tx.score} outcome={tx.routing_outcome} />
                      </td>
                      <td className="py-3 px-4 font-sans">
                        <Badge decidedBy={tx.decided_by} />
                      </td>
                      <td className="py-3 px-4 text-amber-400 font-sans">
                        {tx.fp_cost_estimate ? `₹${tx.fp_cost_estimate}` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
