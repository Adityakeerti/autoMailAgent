import { useState, useEffect } from 'react';
import { api, setToken } from './api';
import { LandingPage } from './components/LandingPage';
import { Sidebar } from './components/Sidebar';
import { DashboardView } from './components/DashboardView';
import { ResumeContextView } from './components/ResumeContextView';
import { ScraperView } from './components/ScraperView';
import { ContactsQueueView } from './components/ContactsQueueView';
import { TemplatesView } from './components/TemplatesView';
import { SettingsView } from './components/SettingsView';
import { TopLoadingBar } from './components/Skeleton';

export function App() {
  const [authenticated, setAuthenticated] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [pageLoading, setPageLoading] = useState<boolean>(false);

  const [contacts, setContacts] = useState<any[]>([]);
  const [queue, setQueue] = useState<any[]>([]);
  const [settings, setSettings] = useState<any>({});
  const [metrics, setMetrics] = useState<any[]>([]);
  const [userEmail, setUserEmail] = useState<string>('');

  // Verify cookie session on mount (also handles ?token= from Google OAuth redirect)
  useEffect(() => {
    const verifySession = async () => {
      setPageLoading(true);

      // Extract token from URL if redirected from Google OAuth callback
      const urlParams = new URLSearchParams(window.location.search);
      const urlToken = urlParams.get('token');
      if (urlToken) {
        setToken(urlToken);
        // Clean up URL so token doesn't linger in the address bar
        window.history.replaceState({}, '', window.location.pathname);
      }

      try {
        const me = await api.getMe();
        setUserEmail(me.email);
        setAuthenticated(true);
      } catch (err) {
        setAuthenticated(false);
      } finally {
        setPageLoading(false);
      }
    };
    verifySession();
  }, []);

  const loadAllData = async () => {
    setPageLoading(true);
    try {
      const [cList, qList, stData, mList] = await Promise.all([
        api.listContacts(),
        api.listQueue(),
        api.getSettings(),
        api.listContactsMetrics().catch(() => []),
      ]);
      setContacts(cList);
      setQueue(qList);
      setSettings(stData);
      setMetrics(mList);
      setUserEmail(stData?.smtp_user || 'Active User');
    } catch (err) {
      console.error('Data loading error:', err);
    } finally {
      setPageLoading(false);
    }
  };

  useEffect(() => {
    if (authenticated) {
      loadAllData();
    }
  }, [authenticated, activeTab]);

  if (!authenticated) {
    return <LandingPage onSuccess={() => setAuthenticated(true)} />;
  }

  return (
    <div className="app-container">
      <TopLoadingBar active={pageLoading} />
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
            metrics={metrics}
            loading={pageLoading}
            onRefresh={loadAllData}
          />
        )}
        {activeTab === 'resume' && <ResumeContextView onLoadingChange={setPageLoading} />}
        {activeTab === 'scrapers' && <ScraperView onLoadingChange={setPageLoading} onRefresh={loadAllData} />}

        {activeTab === 'contacts' && <ContactsQueueView onLoadingChange={setPageLoading} />}
        {activeTab === 'templates' && <TemplatesView onLoadingChange={setPageLoading} />}
        {activeTab === 'settings' && <SettingsView onLoadingChange={setPageLoading} />}
      </main>
    </div>
  );
}

export default App;
