import React, { useState, useEffect } from 'react';
import { Save, Mail, Clock, Key, Globe, CheckCircle, Loader2 } from 'lucide-react';
import { api } from '../api';
import { SkeletonCard } from './Skeleton';

interface SettingsViewProps {
  onLoadingChange?: (loading: boolean) => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ onLoadingChange }) => {
  const [st, setSt] = useState<any>({
    smtp_host: '', smtp_port: 587, smtp_user: '', smtp_password: '',
    imap_host: '', imap_port: 993, imap_user: '', imap_password: '',
    linkedin_cookie: '', send_mode: 'review', schedule_window: '08:00-23:00', daily_target: 50
  });

  const [initialLoading, setInitialLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');

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

  const handleConnectGoogleOAuth = async () => {
    try {
      const res = await api.getGoogleAuthUrl();
      window.location.href = res.url;
    } catch (err: any) {
      setMsg('Failed to launch Google OAuth: ' + err.message);
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
              AutoMail includes a system-level connector for identifying matching roles and positions. Optionally override below with a custom `li_at` account cookie.
            </p>
            <div className="form-group">
              <label className="form-label">Custom Connection Cookie Override (Optional) {st.has_linkedin_cookie ? '(Saved)' : ''}</label>
              <input type="password" className="form-input" placeholder="AQED..." value={st.linkedin_cookie || ''} onChange={(e) => setSt({ ...st, linkedin_cookie: e.target.value })} />
            </div>
          </div>

          <button type="submit" className="btn btn-primary btn-lg" disabled={loading} style={{ padding: '12px 24px' }}>
            {loading ? (
              <><Loader2 size={18} className="spin-icon" /> Saving Settings...</>
            ) : (
              <><Save size={18} /> Save All Settings</>
            )}
          </button>
        </form>
      )}
    </div>
  );
};
