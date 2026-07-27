import React, { useState, useEffect } from 'react';
import { Save, Lock, Mail, Clock, Key } from 'lucide-react';
import { api } from '../api';

export const SettingsView: React.FC = () => {
  const [st, setSt] = useState<any>({
    smtp_host: '', smtp_port: 587, smtp_user: '', smtp_password: '',
    imap_host: '', imap_port: 993, imap_user: '', imap_password: '',
    linkedin_cookie: '', send_mode: 'review', schedule_window: '08:00-23:00', daily_target: 50
  });

  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');

  const loadSettings = async () => {
    try {
      const data = await api.getSettings();
      setSt((prev: any) => ({ ...prev, ...data }));
    } catch (e: any) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMsg('');

    try {
      await api.updateSettings(st);
      setMsg('Settings updated! Secrets are encrypted at rest.');
      await loadSettings();
    } catch (err: any) {
      setMsg('Error saving settings: ' + err.message);
    } finally {
      setLoading(false);
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
            <span style={{ fontSize: '12px', color: 'var(--outline)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Lock size={12} /> Encrypted at rest (Fernet)
            </span>
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
              <label className="form-label">SMTP App Password {st.has_smtp_password ? '(Saved)' : ''}</label>
              <input type="password" className="form-input" placeholder="App password" value={st.smtp_password || ''} onChange={(e) => setSt({ ...st, smtp_password: e.target.value })} />
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

        {/* LinkedIn Cookie */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Dedicated LinkedIn Account Cookie</h3>
          </div>
          <div className="form-group">
            <label className="form-label">li_at Cookie Secret {st.has_linkedin_cookie ? '(Saved)' : ''}</label>
            <input type="password" className="form-input" placeholder="AQED..." value={st.linkedin_cookie || ''} onChange={(e) => setSt({ ...st, linkedin_cookie: e.target.value })} />
          </div>
        </div>

        <button type="submit" className="btn btn-primary btn-lg" disabled={loading} style={{ padding: '12px 24px' }}>
          <Save size={18} /> {loading ? 'Saving...' : 'Save All Settings'}
        </button>
      </form>
    </div>
  );
};
