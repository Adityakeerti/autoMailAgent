import React, { useState } from 'react';
import { Play, Pause, RefreshCw, Loader2, ExternalLink } from 'lucide-react';
import { api } from '../api';
import { SkeletonStatCard, SkeletonTable, Skeleton } from './Skeleton';

interface DashboardViewProps {
  contacts: any[];
  queue: any[];
  settings: any;
  metrics: any[];
  loading?: boolean;
  onRefresh: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ contacts, queue, settings, metrics = [], loading, onRefresh }) => {
  const [updatingMode, setUpdatingMode] = useState(false);

  const totalContacts = contacts.length;
  const sentCount = contacts.filter((c) => c.status === 'sent').length;
  const queuedCount = contacts.filter((c) => c.status === 'queued').length;
  const repliedCount = contacts.filter((c) => c.status === 'replied').length;

  const toggleSendMode = async () => {
    setUpdatingMode(true);
    try {
      const nextMode = settings.send_mode === 'auto' ? 'review' : 'auto';
      await api.updateSettings({ send_mode: nextMode });
      onRefresh();
    } finally {
      setUpdatingMode(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Executive Dashboard</h1>
          <p className="page-subtitle">Real-time status of your cold outreach automation pipeline</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={onRefresh} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin-icon' : ''} /> {loading ? 'Refreshing...' : 'Refresh Stats'}
          </button>
          <button
            className={`btn ${settings?.send_mode === 'auto' ? 'btn-danger' : 'btn-primary'}`}
            onClick={toggleSendMode}
            disabled={updatingMode}
          >
            {updatingMode ? (
              <><Loader2 size={16} className="spin-icon" /> Updating...</>
            ) : settings?.send_mode === 'auto' ? (
              <><Pause size={16} /> Pause Queue</>
            ) : (
              <><Play size={16} /> Start Auto-Send</>
            )}
          </button>
        </div>
      </div>

      {loading && contacts.length === 0 ? (
        <>
          <div className="stats-grid">
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
          </div>
          <div className="card" style={{ padding: '24px' }}>
            <Skeleton width="40%" height="20px" style={{ marginBottom: '16px' }} />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              <Skeleton height="60px" borderRadius="6px" />
              <Skeleton height="60px" borderRadius="6px" />
              <Skeleton height="60px" borderRadius="6px" />
              <Skeleton height="60px" borderRadius="6px" />
            </div>
          </div>
          <div className="card">
            <Skeleton width="30%" height="20px" style={{ marginBottom: '16px' }} />
            <SkeletonTable rows={4} columns={4} />
          </div>
        </>
      ) : (
        <>
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
              <h3 className="card-title">Channel Yield &amp; Lead Quality</h3>
            </div>
            {metrics.length === 0 ? (
              <p style={{ color: 'var(--on-surface-variant)', fontSize: '14px', textAlign: 'center', padding: '20px 0' }}>
                No scraper channel metrics available. Run auto-discover or scrape links to see performance.
              </p>
            ) : (
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Source Channel</th>
                      <th>Total Leads</th>
                      <th>Named Contacts</th>
                      <th>Generic Contacts</th>
                      <th>Valid (Non-Bounced)</th>
                      <th>Bounced</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.map((m) => (
                      <tr key={m.source}>
                        <td style={{ fontWeight: 600 }}>{m.source}</td>
                        <td>{m.leads_found}</td>
                        <td style={{ color: '#16a34a', fontWeight: m.real_name_count > 0 ? 600 : 400 }}>{m.real_name_count}</td>
                        <td style={{ color: '#d97706' }}>{m.generic_count}</td>
                        <td>{m.valid_count}</td>
                        <td style={{ color: m.bounced_count > 0 ? '#dc2626' : 'inherit' }}>{m.bounced_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
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
                      <th>JD</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queue.slice(0, 5).map((item) => (
                      <tr key={item.id}>
                        <td style={{ fontWeight: 500 }}>{item.name || item.email}</td>
                        <td>{item.company || 'N/A'}</td>
                        <td>{item.role || 'N/A'}</td>
                        <td>
                          {item.job_posting_url ? (
                            <a
                              href={item.job_posting_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn btn-secondary btn-sm"
                              title="View Job Description"
                            >
                              <ExternalLink size={12} /> JD
                            </a>
                          ) : (
                            <span style={{ color: 'var(--outline)', fontSize: '11px' }}>—</span>
                          )}
                        </td>
                        <td><span className={`chip chip-${item.status}`}>{item.status}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
