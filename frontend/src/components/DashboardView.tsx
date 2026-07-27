import React from 'react';
import { Play, Pause, RefreshCw } from 'lucide-react';
import { api } from '../api';

interface DashboardViewProps {
  contacts: any[];
  queue: any[];
  settings: any;
  onRefresh: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ contacts, queue, settings, onRefresh }) => {
  const totalContacts = contacts.length;
  const sentCount = contacts.filter((c) => c.status === 'sent').length;
  const queuedCount = contacts.filter((c) => c.status === 'queued').length;
  const repliedCount = contacts.filter((c) => c.status === 'replied').length;

  const toggleSendMode = async () => {
    const nextMode = settings.send_mode === 'auto' ? 'review' : 'auto';
    await api.updateSettings({ send_mode: nextMode });
    onRefresh();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Executive Dashboard</h1>
          <p className="page-subtitle">Real-time status of your cold outreach automation pipeline</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={onRefresh}>
            <RefreshCw size={16} /> Refresh Stats
          </button>
          <button
            className={`btn ${settings?.send_mode === 'auto' ? 'btn-danger' : 'btn-primary'}`}
            onClick={toggleSendMode}
          >
            {settings?.send_mode === 'auto' ? (
              <><Pause size={16} /> Pause Queue</>
            ) : (
              <><Play size={16} /> Start Auto-Send</>
            )}
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Contacts</div>
          <div className="stat-value">{totalContacts}</div>
          <div className="stat-subtext">Discovered across channels</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Queued for Send</div>
          <div className="stat-value" style={{ color: 'var(--primary)' }}>{queuedCount}</div>
          <div className="stat-subtext">Awaiting schedule slot</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Emails Delivered</div>
          <div className="stat-value" style={{ color: '#16a34a' }}>{sentCount}</div>
          <div className="stat-subtext">Sent via SMTP sender</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Replies Received</div>
          <div className="stat-value" style={{ color: '#0d9488' }}>{repliedCount}</div>
          <div className="stat-subtext">Tracked via IMAP</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Pipeline Engine Status</h3>
          <span className={`chip ${settings?.send_mode === 'auto' ? 'chip-personalized' : 'chip-queued'}`}>
            {settings?.send_mode || 'review'} mode
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', fontSize: '14px' }}>
          <div style={{ padding: '12px', background: 'var(--surface-container-low)', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: 'var(--outline)', fontWeight: 600 }}>SMTP SERVER</span>
            <div style={{ fontWeight: 600, marginTop: '4px' }}>{settings?.smtp_host || 'Not Configured'}</div>
          </div>
          <div style={{ padding: '12px', background: 'var(--surface-container-low)', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: 'var(--outline)', fontWeight: 600 }}>SCHEDULE WINDOW</span>
            <div style={{ fontWeight: 600, marginTop: '4px' }}>{settings?.schedule_window || '08:00-23:00'}</div>
          </div>
          <div style={{ padding: '12px', background: 'var(--surface-container-low)', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: 'var(--outline)', fontWeight: 600 }}>RATE LIMIT</span>
            <div style={{ fontWeight: 600, marginTop: '4px' }}>2 - 3 emails / hour</div>
          </div>
          <div style={{ padding: '12px', background: 'var(--surface-container-low)', borderRadius: '6px' }}>
            <span style={{ fontSize: '12px', color: 'var(--outline)', fontWeight: 600 }}>DAILY TARGET</span>
            <div style={{ fontWeight: 600, marginTop: '4px' }}>{settings?.daily_target || 50} emails / day</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Recent Queued Contacts</h3>
        </div>
        {queue.length === 0 ? (
          <p style={{ color: 'var(--on-surface-variant)', fontSize: '14px', textAlign: 'center', padding: '20px 0' }}>
            No contacts currently queued for send. Use Scrapers or upload contacts to populate the queue.
          </p>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Recipient</th>
                  <th>Company</th>
                  <th>Role</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {queue.slice(0, 5).map((item) => (
                  <tr key={item.id}>
                    <td style={{ fontWeight: 500 }}>{item.name || item.email}</td>
                    <td>{item.company || 'N/A'}</td>
                    <td>{item.role || 'N/A'}</td>
                    <td><span className={`chip chip-${item.status}`}>{item.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
