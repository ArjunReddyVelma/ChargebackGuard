import React, { useState, useEffect } from 'react';
import { getConfig, updateConfig } from '../services/api';
import Toast from '../components/Toast';
import { Sliders, DollarSign, Save, AlertCircle } from 'lucide-react';

export default function SettingsView() {
  const [lowThreshold, setLowThreshold] = useState(30);
  const [highThreshold, setHighThreshold] = useState(70);
  const [fpCostBase, setFpCostBase] = useState(500);
  const [fnCostFee, setFnCostFee] = useState(1500);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [toastMsg, setToastMsg] = useState('');

  useEffect(() => {
    async function loadConfig() {
      try {
        setLoading(true);
        const data = await getConfig();
        setLowThreshold(data.low_threshold);
        setHighThreshold(data.high_threshold);
        setFpCostBase(data.fp_cost_base);
        setFnCostFee(data.fn_cost_fee);
      } catch (err) {
        setError('Failed to load system configuration.');
      } finally {
        setLoading(false);
      }
    }
    loadConfig();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setError('');

    // VR-5 / BR-6 validation
    if (lowThreshold >= highThreshold) {
      setError('Low threshold must be strictly less than high threshold (VR-5 / BR-6).');
      return;
    }

    // BR-5 validation
    if (fpCostBase <= 0 || fnCostFee <= 0) {
      setError('Cost assumptions must be strictly greater than zero (BR-5).');
      return;
    }

    setSaving(true);

    try {
      await updateConfig({
        low_threshold: Number(lowThreshold),
        high_threshold: Number(highThreshold),
        fp_cost_base: Number(fpCostBase),
        fn_cost_fee: Number(fnCostFee)
      });
      setToastMsg('Risk configuration updated successfully and logged to audit trail (FR-15).');
    } catch (err) {
      setError(err.message || 'Failed to update configuration.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-400 text-sm">Loading risk settings...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {toastMsg && <Toast message={toastMsg} type="success" onClose={() => setToastMsg('')} />}

      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <Sliders className="w-6 h-6 text-blue-400" />
          Risk Engine & Cost Settings (FR-14 / FR-15)
        </h1>
        <p className="text-slate-400 text-xs mt-1">
          Adjust risk score routing bands and financial cost exposure assumptions (Risk Manager role only).
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Risk Score Routing Thresholds Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          <h3 className="text-sm font-bold text-white uppercase tracking-wide border-b border-slate-800 pb-3">
            Risk Threshold Bands (FR-5 / FR-14)
          </h3>

          {/* Visual Band Preview */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-300">Live Threshold Band Preview:</span>
            <div className="h-6 w-full rounded-xl overflow-hidden flex font-mono text-[10px] font-bold text-center leading-6">
              <div className="bg-emerald-500/20 text-emerald-300 border-r border-emerald-500/40" style={{ width: `${lowThreshold}%` }}>
                Auto Clear (0 - {lowThreshold - 1})
              </div>
              <div className="bg-amber-500/20 text-amber-300 border-r border-amber-500/40" style={{ width: `${highThreshold - lowThreshold + 1}%` }}>
                Review Queue ({lowThreshold} - {highThreshold})
              </div>
              <div className="bg-rose-500/20 text-rose-300" style={{ width: `${100 - highThreshold}%` }}>
                Auto Block ({highThreshold + 1} - 100)
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Low Risk Threshold (Auto Clear boundary): <span className="text-emerald-400 font-mono">{lowThreshold}</span>
              </label>
              <input
                type="range"
                min="5"
                max="50"
                value={lowThreshold}
                onChange={(e) => setLowThreshold(Number(e.target.value))}
                className="w-full accent-blue-500 bg-slate-950"
              />
              <span className="text-[11px] text-slate-500 block mt-1">Scores below this are auto-cleared.</span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                High Risk Threshold (Auto Block boundary): <span className="text-rose-400 font-mono">{highThreshold}</span>
              </label>
              <input
                type="range"
                min="51"
                max="95"
                value={highThreshold}
                onChange={(e) => setHighThreshold(Number(e.target.value))}
                className="w-full accent-blue-500 bg-slate-950"
              />
              <span className="text-[11px] text-slate-500 block mt-1">Scores above this are auto-blocked.</span>
            </div>
          </div>
        </div>

        {/* Cost Assumptions Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          <h3 className="text-sm font-bold text-white uppercase tracking-wide border-b border-slate-800 pb-3 flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-emerald-400" />
            Financial Cost Assumptions (FR-6 / BR-5)
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                False Positive Base Friction Cost (₹):
              </label>
              <input
                type="number"
                min="1"
                step="50"
                value={fpCostBase}
                onChange={(e) => setFpCostBase(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white font-mono text-sm focus:outline-none focus:border-blue-500"
              />
              <span className="text-[11px] text-slate-500 block mt-1">Estimated customer friction & lost margin per false block.</span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                False Negative Chargeback Fee (₹):
              </label>
              <input
                type="number"
                min="1"
                step="100"
                value={fnCostFee}
                onChange={(e) => setFnCostFee(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white font-mono text-sm focus:outline-none focus:border-blue-500"
              />
              <span className="text-[11px] text-slate-500 block mt-1">Fixed penalty fee charged per missed fraud chargeback.</span>
            </div>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={saving}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-blue-600/20 inline-flex items-center gap-2 disabled:opacity-50 transition-all"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Saving & Logging Audit Entry...' : 'Save Configuration Changes'}
        </button>
      </form>
    </div>
  );
}
