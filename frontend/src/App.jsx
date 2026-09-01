import React from 'react'

export default function App() {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-slate-900 text-white p-6">
      <div className="max-w-md w-full bg-slate-800 rounded-xl p-8 border border-slate-700 shadow-2xl text-center">
        <h1 className="text-3xl font-bold tracking-tight text-blue-400 mb-2">ChargebackGuard</h1>
        <p className="text-slate-400 text-sm mb-6">Explainable AI Risk & Fraud Detection Agent</p>
        
        <div className="inline-block px-4 py-2 bg-slate-700/50 rounded-lg border border-slate-600 text-xs font-mono text-slate-300 mb-4">
          API URL: <span className="text-emerald-400">{apiUrl}</span>
        </div>
        
        <div className="mt-4 text-xs text-slate-500">
          Phase 0: Setup & Scaffolding Complete
        </div>
      </div>
    </div>
  )
}
