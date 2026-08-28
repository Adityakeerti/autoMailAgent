import React, { useState, useEffect } from 'react';
import { Save, Mail, Clock, Key, CheckCircle, Loader2 } from 'lucide-react';
import { api } from '../api';
import { SkeletonCard } from './Skeleton';

interface SettingsViewProps {
  onLoadingChange?: (loading: boolean) => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ onLoadingChange }) => {
  const [st, setSt] = useState<any>({
    smtp_host: '', smtp_port: 587, smtp_user: '', smtp_password: '',
    imap_host: '', imap_port: 993, imap_user: '', imap_password: '',
    linkedin_cookie: '', send_mode: 'review', schedule_window: '08:00-23:00', daily_target: 50,
    job_agent_enabled: false, browser_type: 'brave', browser_custom_path: '', browser_cdp_port: 9222
  });

  const [initialLoading, setInitialLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');
  const [clearing, setClearing] = useState(false);

  const loadSettings = async () => {
    onLoadingChange?.(true);
    try {
      const data = await api.getSettings();
      setSt((prev: any) => ({ ...prev, ...data }));
    } catch (e: any) {
      console.error(e);
    } finally {
      setInitialLoading(false);
      onLoadingChange?.(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    onLoadingChange?.(true);
    setMsg('');

    try {
      await api.updateSettings(st);
      setMsg('Settings updated! Secrets are encrypted at rest.');
      await loadSettings();
    } catch (err: any) {
      setMsg('Error saving settings: ' + err.message);
    } finally {
      setLoading(false);
      onLoadingChange?.(false);
    }
  };

  const handleClearPipeline = async () => {
    if (!window.confirm("WARNING: This will permanently delete all your cold mail contacts, logs, and scraper records. This action cannot be undone. Are you sure you want to proceed?")) {
      return;
    }
    setClearing(true);
    onLoadingChange?.(true);
    setMsg('');
    try {
      const res = await api.clearPipeline();
      setMsg(res.message || 'Pipeline data cleared successfully!');
    } catch (err: any) {
      setMsg('Error clearing data: ' + err.message);
    } finally {
      setClearing(false);
      onLoadingChange?.(false);
    }
  };



  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">User Settings & Encrypted Secrets</h1>
          <p className="page-subtitle">Configure your personal SMTP, IMAP, rate limits, and sending schedule</p>
        </div>
      </div>

      {msg && <div className="alert alert-success">{msg}</div>}

      {initialLoading ? (
        <>
          <SkeletonCard height="120px" />
          <SkeletonCard height="200px" />
          <SkeletonCard height="180px" />
        </>
      ) : (
        <>
          <form onSubmit={handleSave}>
          {/* Sending Mode & Schedule */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={18} color="var(--primary)" /> Sending Strategy & Pace
              </h3>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
              <div className="form-group">
                <label className="form-label">Send Mode</label>
                <select className="form-select" value={st.send_mode || 'review'} onChange={(e) => setSt({ ...st, send_mode: e.target.value })}>
                  <option value="review">review (Queue requires manual approval before send)</option>
                  <option value="auto">auto (Sends automatically on rate-limited schedule)</option>
                  <option value="auto_pause_on_signal">auto_pause_on_signal (Pauses queue on reply/bounce)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Daily Schedule Window</label>
                <input type="text" className="form-input" value={st.schedule_window || '08:00-23:00'} onChange={(e) => setSt({ ...st, schedule_window: e.target.value })} placeholder="08:00-23:00" />
              </div>

              <div className="form-group">
                <label className="form-label">Daily Target Count</label>
                <input type="number" className="form-input" value={st.daily_target || 50} onChange={(e) => setSt({ ...st, daily_target: parseInt(e.target.value) })} />
              </div>
            </div>
          </div>

          {/* SMTP Configuration */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Mail size={18} color="var(--primary)" /> SMTP Outreach Sender Credentials
              </h3>
            </div>

            <div style={{
              display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px',
              background: 'var(--surface-container-low)', border: '1px solid var(--border)',
              borderRadius: '8px', marginBottom: '16px'
            }}>
              <div style={{ fontSize: '12px', color: 'var(--on-surface-variant)' }}>
                Please configure your SMTP outbound sender. Standard SMTP with an App Password is recommended.
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
              <div className="form-group">
                <label className="form-label">SMTP Host</label>
                <input type="text" className="form-input" placeholder="smtp.gmail.com" value={st.smtp_host || ''} onChange={(e) => setSt({ ...st, smtp_host: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">SMTP Port</label>
                <input type="number" className="form-input" placeholder="587" value={st.smtp_port || 587} onChange={(e) => setSt({ ...st, smtp_port: parseInt(e.target.value) })} />
              </div>
              <div className="form-group">
                <label className="form-label">SMTP Username / Email</label>
                <input type="text" className="form-input" placeholder="you@gmail.com" value={st.smtp_user || ''} onChange={(e) => setSt({ ...st, smtp_user: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">
                  SMTP App Password {st.has_smtp_password ? '(Saved)' : ''}
                </label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="Enter SMTP app password"
                  value={st.smtp_password || ''}
                  onChange={(e) => setSt({ ...st, smtp_password: e.target.value })}
                />
              </div>
            </div>
          </div>

          {/* IMAP Configuration */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Key size={18} color="var(--primary)" /> IMAP Bounce & Reply Tracker Credentials
              </h3>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
              <div className="form-group">
                <label className="form-label">IMAP Host</label>
                <input type="text" className="form-input" placeholder="imap.gmail.com" value={st.imap_host || ''} onChange={(e) => setSt({ ...st, imap_host: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">IMAP Port</label>
                <input type="number" className="form-input" placeholder="993" value={st.imap_port || 993} onChange={(e) => setSt({ ...st, imap_port: parseInt(e.target.value) })} />
              </div>
              <div className="form-group">
                <label className="form-label">IMAP Username</label>
                <input type="text" className="form-input" placeholder="you@gmail.com" value={st.imap_user || ''} onChange={(e) => setSt({ ...st, imap_user: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">IMAP Password {st.has_imap_password ? '(Saved)' : ''}</label>
                <input type="password" className="form-input" placeholder="App password" value={st.imap_password || ''} onChange={(e) => setSt({ ...st, imap_password: e.target.value })} />
              </div>
            </div>
          </div>

          {/* LinkedIn Connection Configuration */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                LinkedIn Connection System
              </h3>
              <span className="chip chip-personalized" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <CheckCircle size={12} /> Connection Active
              </span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)', marginBottom: '12px' }}>
              GetNewJob AI includes a system-level connector for identifying matching roles and positions. Optionally override below with a custom `li_at` account cookie.
            </p>
            <div className="form-group">
              <label className="form-label">Custom Connection Cookie Override (Optional) {st.has_linkedin_cookie ? '(Saved)' : ''}</label>
              <input type="password" className="form-input" placeholder="AQED..." value={st.linkedin_cookie || ''} onChange={(e) => setSt({ ...st, linkedin_cookie: e.target.value })} />
            </div>
          </div>

          {/* Browser & Automation Settings - suppressed from UI
          <div className="card">
            <div className="card-header">
              <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                Browser Automation Settings
              </h3>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)', marginBottom: '12px' }}>
              Configure your preferred browser for autonomous application form filling.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '12px' }}>
              <div className="form-group">
                <label className="form-label">Job Agent Scheduled Auto-Runs</label>
                <select className="form-select" value={st.job_agent_enabled ? 'true' : 'false'} onChange={(e) => setSt({ ...st, job_agent_enabled: e.target.value === 'true' })}>
                  <option value="false">Disabled (Manual trigger only)</option>
                  <option value="true">Enabled (Autonomous run every 6 hours)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Preferred Browser</label>
                <select className="form-select" value={st.browser_type || 'brave'} onChange={(e) => setSt({ ...st, browser_type: e.target.value })}>
                  <option value="brave">Brave Browser (🦁)</option>
                  <option value="chrome">Google Chrome (🌐)</option>
                  <option value="edge">Microsoft Edge (🌊)</option>
                  <option value="custom">Custom / Other Chromium (⚙️)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">CDP Debugging Port</label>
                <input type="number" className="form-input" value={st.browser_cdp_port || 9222} onChange={(e) => setSt({ ...st, browser_cdp_port: parseInt(e.target.value) || 9222 })} />
              </div>
            </div>

            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">
                Custom Executable Path {st.browser_type !== 'custom' ? '(Optional Override)' : '(Required)'}
              </label>
              <input
                type="text"
                className="form-input"
                placeholder={
                  st.browser_type === 'brave' ? "e.g. C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe" :
                  st.browser_type === 'chrome' ? "e.g. C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" :
                  st.browser_type === 'edge' ? "e.g. C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" :
                  "e.g. C:\\Program Files\\Vivaldi\\Application\\vivaldi.exe"
                }
                value={st.browser_custom_path || ''}
                onChange={(e) => setSt({ ...st, browser_custom_path: e.target.value })}
              />
            </div>
          </div>
          */}

          <button type="submit" className="btn btn-primary btn-lg" disabled={loading} style={{ padding: '12px 24px' }}>
            {loading ? (
              <><Loader2 size={18} className="spin-icon" /> Saving Settings...</>
            ) : (
              <><Save size={18} /> Save All Settings</>
            )}
          </button>
        </form>

        {/* Reset & Clear Pipeline Data Card */}
        <div className="card" style={{ marginTop: '24px', border: '1px solid rgba(220, 38, 38, 0.35)', background: 'rgba(220, 38, 38, 0.02)' }}>
          <div className="card-header" style={{ borderBottom: '1px solid rgba(220, 38, 38, 0.15)', paddingBottom: '12px' }}>
            <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#dc2626' }}>
              Reset & Clear Pipeline Data
            </h3>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)', marginTop: '12px', marginBottom: '14px', lineHeight: '1.5' }}>
            Permanently deletes all cold outreach contacts, scraped job listings, raw scraper queue leads, outreach dispatch logs, and application history.
            <br />
            <span style={{ fontWeight: 600 }}>Preserved data:</span> Your profile context (name, experience, projects, achievements, preferences), credentials, resumes, and email templates will remain untouched.
          </p>
          <button
            type="button"
            className="btn"
            style={{ background: '#dc2626', color: '#ffffff', border: 'none', padding: '10px 18px', fontWeight: 600 }}
            onClick={handleClearPipeline}
            disabled={clearing}
          >
            {clearing ? (
              <><Loader2 size={16} className="spin-icon" /> Clearing Data...</>
            ) : (
              "Clear Pipeline Data"
            )}
          </button>
        </div>
      </>)}
    </div>
  );
};
