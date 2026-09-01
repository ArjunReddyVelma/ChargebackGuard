import React, { useState } from 'react';
import { uploadBatch } from '../services/api';
import { UploadCloud, CheckCircle2, AlertCircle, FileText, ArrowRight } from 'lucide-react';

export default function UploadView({ onUploadComplete, onGoToQueue }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
      setResult(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError('');
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError('');

    try {
      const res = await uploadBatch(file);
      setResult(res);
      if (onUploadComplete) onUploadComplete(res.batch_id);
    } catch (err) {
      setError(err.message || 'Upload failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Upload Transaction Batch</h1>
          <p className="text-slate-400 text-xs mt-1">
            Ingest structured CSV batches for rule engine pre-filtering and Claude LLM risk explainability scoring.
          </p>
        </div>
      </div>

      {/* Drag & Drop Zone */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all bg-slate-900/60 backdrop-blur-sm ${
          file ? 'border-blue-500/50 bg-blue-500/5' : 'border-slate-800 hover:border-slate-700'
        }`}
      >
        <div className="mx-auto w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mb-4">
          <UploadCloud className="w-8 h-8" />
        </div>

        {file ? (
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white font-medium">
              <FileText className="w-4 h-4 text-blue-400" />
              {file.name} ({(file.size / 1024).toFixed(1)} KB)
            </div>
            <div>
              <button
                onClick={() => setFile(null)}
                className="text-xs text-rose-400 hover:underline font-medium"
              >
                Remove File
              </button>
            </div>
          </div>
        ) : (
          <div>
            <p className="text-sm font-semibold text-white">Drag and drop your transaction CSV batch here</p>
            <p className="text-xs text-slate-400 mt-1">or click below to browse from your computer</p>
            <label className="mt-4 inline-block px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-xl border border-slate-700 cursor-pointer transition-colors">
              Browse CSV File
              <input type="file" accept=".csv" onChange={handleFileChange} className="hidden" />
            </label>
          </div>
        )}

        {file && !result && (
          <div className="mt-6">
            <button
              onClick={handleUpload}
              disabled={loading}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-sm rounded-xl transition-all shadow-lg shadow-blue-600/20 inline-flex items-center gap-2 disabled:opacity-50"
            >
              {loading ? 'Processing Batch & Scoring...' : 'Start Batch Scoring Run'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Batch Processing Summary Card */}
      {result && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Batch Scoring Complete</h3>
                <p className="text-xs text-slate-400 font-mono">ID: {result.batch_id}</p>
              </div>
            </div>
            <button
              onClick={onGoToQueue}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-emerald-600/20 transition-all"
            >
              Go to Review Queue
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800/80">
              <span className="text-xs text-slate-400 font-medium">Total Rows</span>
              <p className="text-2xl font-bold text-white mt-1">{result.total_rows}</p>
            </div>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800/80">
              <span className="text-xs text-slate-400 font-medium">Valid Scored</span>
              <p className="text-2xl font-bold text-emerald-400 mt-1">{result.valid_rows_count}</p>
            </div>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800/80">
              <span className="text-xs text-slate-400 font-medium">Rule Decided</span>
              <p className="text-2xl font-bold text-blue-400 mt-1">{result.rule_decided_count}</p>
            </div>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800/80">
              <span className="text-xs text-slate-400 font-medium">LLM Decided</span>
              <p className="text-2xl font-bold text-purple-400 mt-1">{result.llm_decided_count}</p>
            </div>
          </div>

          {/* Quarantined Rows Panel (ER-1 UI) */}
          {result.quarantined_rows_count > 0 && (
            <div className="border border-amber-500/30 bg-amber-500/5 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-bold text-amber-300 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  {result.quarantined_rows_count} Rows Quarantined (ER-1 Ingestion Isolation)
                </span>
                <span className="text-xs text-amber-400/80 font-mono">Valid rows processed normally</span>
              </div>
              <div className="max-h-48 overflow-y-auto space-y-2 text-xs font-mono">
                {result.quarantined_errors.map((err, idx) => (
                  <div key={idx} className="p-2.5 bg-slate-950/80 rounded border border-amber-500/20 text-slate-300">
                    <span className="text-amber-400 font-bold">Row {err.row_number}: </span>
                    <span className="text-slate-400">[{err.error_code}] </span>
                    <span>{err.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
