import { useState, useEffect } from 'react';
import { getToken, api } from './api';
import { AuthModal } from './components/AuthModal';
import { Sidebar } from './components/Sidebar';
import { DashboardView } from './components/DashboardView';
import { ResumeContextView } from './components/ResumeContextView';
import { ScraperView } from './components/ScraperView';
import { ContactsQueueView } from './components/ContactsQueueView';
import { TemplatesView } from './components/TemplatesView';
import { SettingsView } from './components/SettingsView';

export function App() {
  const [authenticated, setAuthenticated] = useState<boolean>(!!getToken());
  const [activeTab, setActiveTab] = useState<string>('dashboard');

  const [contacts, setContacts] = useState<any[]>([]);
  const [queue, setQueue] = useState<any[]>([]);
  const [settings, setSettings] = useState<any>({});
  const [userEmail, setUserEmail] = useState<string>('');

  const loadAllData = async () => {
    if (!getToken()) return;
    try {
      const [cList, qList, stData] = await Promise.all([
        api.listContacts(),
        api.listQueue(),
        api.getSettings(),
      ]);
      setContacts(cList);
      setQueue(qList);
      setSettings(stData);
      setUserEmail(stData?.smtp_user || 'Active User');
    } catch (err) {
      console.error('Data loading error:', err);
    }
  };

  useEffect(() => {
    if (authenticated) {
      loadAllData();
    }
  }, [authenticated, activeTab]);

  if (!authenticated) {
    return <AuthModal onSuccess={() => setAuthenticated(true)} />;
  }

  return (
    <div className="app-container">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        userEmail={userEmail}
        sendMode={settings?.send_mode}
      />
      <main className="main-content">
        {activeTab === 'dashboard' && (
          <DashboardView
            contacts={contacts}
            queue={queue}
            settings={settings}
            onRefresh={loadAllData}
          />
        )}
        {activeTab === 'resume' && <ResumeContextView />}
        {activeTab === 'scrapers' && <ScraperView />}
        {activeTab === 'contacts' && <ContactsQueueView />}
        {activeTab === 'templates' && <TemplatesView />}
        {activeTab === 'settings' && <SettingsView />}
      </main>
    </div>
  );
}

export default App;
