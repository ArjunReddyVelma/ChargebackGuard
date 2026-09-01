import React from 'react';
import { LayoutDashboard, UploadCloud, ShieldAlert, LogOut, UserCheck } from 'lucide-react';

export default function AppShell({ activeView, setActiveView, user, onLogout, children }) {
  const isManager = user?.role === 'Risk Manager';

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'upload', label: 'Upload Batch', icon: UploadCloud },
    { id: 'queue', label: 'Review Queue', icon: ShieldAlert },
  ];

  return (
    <div className="min-h-screen flex bg-slate-950 text-slate-100 antialiased font-sans">
      {/* Left Sidebar Navigation */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between p-4 flex-shrink-0">
        <div className="space-y-6">
          {/* Logo / Brand Header */}
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="p-2 rounded-xl bg-blue-600/20 border border-blue-500/30 text-blue-400">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <h2 className="font-bold text-white tracking-tight text-base">ChargebackGuard</h2>
              <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Explainable Risk AI</p>
            </div>
          </div>

          {/* Navigation Items */}
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeView === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveView(item.id)}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* User Info Footer & Logout */}
        <div className="pt-4 border-t border-slate-800 space-y-3">
          <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800/80 flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-slate-800 text-slate-300">
              <UserCheck className="w-4 h-4" />
            </div>
            <div className="overflow-hidden text-left">
              <p className="text-xs font-semibold text-white truncate">{user?.email}</p>
              <span className={`inline-block px-1.5 py-0.2 rounded text-[10px] font-bold uppercase ${
                isManager ? 'bg-purple-500/20 text-purple-300' : 'bg-blue-500/20 text-blue-300'
              }`}>
                {user?.role}
              </span>
            </div>
          </div>

          <button
            onClick={onLogout}
            className="w-full flex items-center justify-center gap-2 py-2 text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded-xl transition-all"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Workspace */}
      <main className="flex-1 overflow-y-auto p-8 bg-slate-950/90">
        {children}
      </main>
    </div>
  );
}
