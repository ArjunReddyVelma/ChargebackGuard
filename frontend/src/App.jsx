import React, { useState, useEffect } from 'react';
import LoginView from './views/LoginView';
import AppShell from './views/AppShell';
import DashboardView from './views/DashboardView';
import UploadView from './views/UploadView';
import ReviewQueueView from './views/ReviewQueueView';
import AuditLogView from './views/AuditLogView';
import SettingsView from './views/SettingsView';

export default function App() {
  const [user, setUser] = useState(null);
  const [activeView, setActiveView] = useState('dashboard');
  const [selectedTxId, setSelectedTxId] = useState(null);

  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    const savedToken = localStorage.getItem('token');
    if (savedUser && savedToken) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        localStorage.removeItem('user');
        localStorage.removeItem('token');
      }
    }
  }, []);

  const handleLoginSuccess = (data) => {
    setUser({ email: data.email, role: data.role });
    setActiveView('dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  };

  if (!user) {
    return <LoginView onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <AppShell activeView={activeView} setActiveView={setActiveView} user={user} onLogout={handleLogout}>
      {activeView === 'dashboard' && (
        <DashboardView
          onSelectTransaction={(id) => {
            setSelectedTxId(id);
            setActiveView('queue');
          }}
          onUploadClick={() => setActiveView('upload')}
        />
      )}

      {activeView === 'upload' && (
        <UploadView
          onUploadComplete={() => setActiveView('dashboard')}
          onGoToQueue={() => setActiveView('queue')}
        />
      )}

      {activeView === 'queue' && (
        <ReviewQueueView
          initialSelectedId={selectedTxId}
          onClearSelectedId={() => setSelectedTxId(null)}
        />
      )}

      {activeView === 'audit' && <AuditLogView />}

      {activeView === 'settings' && <SettingsView />}
    </AppShell>
  );
}
