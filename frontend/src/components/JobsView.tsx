import React, { useState, useEffect, useCallback } from 'react';
import {
  Search, CheckCircle, XCircle, AlertTriangle, ExternalLink,
  Loader2, RefreshCw, Wifi, WifiOff, Clock,
  ThumbsUp, ThumbsDown, List, History, AlertCircle, Zap, Monitor,
  Copy, Settings, ShieldAlert,
} from 'lucide-react';
import { api } from '../api';
import { SkeletonTable } from './Skeleton';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────
interface JobListing {
  id: number;
  portal: string;
  job_title: string;
  company?: string;
  location?: string;
  job_url: string;
  match_score?: number;
  match_reason?: string;
  recommended_angle?: string;
  status: string;
  discovered_at?: string;
  applied_at?: string;
}

interface BrowserStatus {
  cdp_reachable: boolean;
  browser_type?: string;
  browser_name?: string;
  port?: number;
  detected_path?: string;
  supported_browsers?: Array<{ id: string; name: string; icon: string; detected: boolean }>;
  portals: Record<string, boolean>;
  launch_commands?: {
    browser_name: string;
    port: number;
    detected_path: string;
    powershell: string;
    cmd: string;
    bash: string;
  };
  message: string;
}

interface Props {
  onLoadingChange?: (loading: boolean) => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────
const PORTAL_LABELS: Record<string, string> = {
  linkedin: 'LinkedIn',
  indeed: 'Indeed / Remotive',
  naukri: 'Naukri',
  wellfound: 'Wellfound',
  arbeitnow: 'Arbeitnow',
  general: 'General / ATS',
};

function ScoreChip({ score }: { score?: number }) {
  if (score == null) return <span className="chip" style={{ background: '#f0f4f8' }}>—</span>;
  const color = score >= 90 ? '#16a34a' : score >= 70 ? '#ca8a04' : '#dc2626';
  const bg = score >= 90 ? '#dcfce7' : score >= 70 ? '#fef9c3' : '#fee2e2';
  return (
    <span className="chip" style={{ background: bg, color, fontWeight: 700 }}>
      {Math.round(score)}
    </span>
  );
}

function StatusChip({ status }: { status: string }) {
  const map: Record<string, { bg: string; color: string; label: string }> = {
    submitted: { bg: '#dcfce7', color: '#15803d', label: 'Submitted' },
    failed: { bg: '#fee2e2', color: '#dc2626', label: 'Failed' },
    manual_needed: { bg: '#fef9c3', color: '#92400e', label: 'Manual Needed' },
    already_applied: { bg: '#e0f2fe', color: '#0369a1', label: 'Already Applied' },
    new: { bg: '#f0f4f8', color: '#475569', label: 'New' },
    scored: { bg: '#ede9fe', color: '#6d28d9', label: 'Scored' },
    approved: { bg: '#dcfce7', color: '#15803d', label: 'Approved' },
    applied: { bg: '#e0f2fe', color: '#0369a1', label: 'Applied' },
    skipped: { bg: '#f1f5f9', color: '#64748b', label: 'Skipped' },
  };
  const s = map[status] || { bg: '#f1f5f9', color: '#64748b', label: status };
  return <span className="chip" style={{ background: s.bg, color: s.color }}>{s.label}</span>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

interface PortalStatusPanelProps {
  status: BrowserStatus | null;
  loading: boolean;
  onRefresh: () => void;
  onConfigUpdate: (data: { browser_type: string; browser_cdp_port?: number; browser_custom_path?: string }) => Promise<void>;
  onLaunch: () => Promise<void>;
  launchLoading: boolean;
}

function PortalStatusPanel({ status, loading, onRefresh, onConfigUpdate, onLaunch, launchLoading }: PortalStatusPanelProps) {
  const [showConfig, setShowConfig] = useState(false);
  const [activeCliTab, setActiveCliTab] = useState<'powershell' | 'cmd' | 'bash'>('powershell');
  const [customPathInput, setCustomPathInput] = useState(status?.detected_path || '');
  const [portInput, setPortInput] = useState(status?.port || 9222);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (status) {
      if (status.detected_path) setCustomPathInput(status.detected_path);
      if (status.port) setPortInput(status.port);
    }
  }, [status]);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleBrowserChange = async (type: string) => {
    await onConfigUpdate({
      browser_type: type,
      browser_cdp_port: portInput,
      browser_custom_path: customPathInput || undefined,
    });
  };

  const handlePortBlur = async () => {
    if (status && portInput !== status.port) {
      await onConfigUpdate({
        browser_type: status.browser_type || 'brave',
        browser_cdp_port: portInput,
        browser_custom_path: customPathInput || undefined,
      });
    }
  };

  const handlePathBlur = async () => {
    if (status && customPathInput !== status.detected_path) {
      await onConfigUpdate({
        browser_type: status.browser_type || 'brave',
        browser_cdp_port: portInput,
        browser_custom_path: customPathInput || undefined,
      });
    }
  };

  const currentBrowser = status?.browser_type || 'brave';
  const cdpReachable = status?.cdp_reachable || false;
  const launchCommands = status?.launch_commands;

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
        <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Monitor size={18} /> Automation Browser &amp; Portal Connection
        </h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className={`btn btn-secondary btn-sm ${showConfig ? 'btn-primary' : ''}`}
            onClick={() => setShowConfig(!showConfig)}
          >
            <Settings size={14} /> Configure Browser
          </button>
          <button className="btn btn-secondary btn-sm" onClick={onRefresh} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {/* Browser Connection Status Badge */}
      <div style={{
        marginBottom: 16, padding: '10px 14px', borderRadius: 8,
        background: cdpReachable ? '#d0f8db' : '#fee2e2',
        border: `1px solid ${cdpReachable ? '#a7f3d0' : '#fca5a5'}`,
        display: 'flex', alignItems: 'center', justifySelf: 'stretch', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {cdpReachable ? (
            <>
              <Wifi size={18} color="#15803d" />
              <span style={{ color: '#15803d', fontSize: 13, fontWeight: 600 }}>
                Connected to {status?.browser_name || 'Browser'} on port {status?.port || 9222}
              </span>
            </>
          ) : (
            <>
              <WifiOff size={18} color="#dc2626" />
              <span style={{ color: '#dc2626', fontSize: 13, fontWeight: 600 }}>
                {status?.browser_name || 'Browser'} (port {status?.port || 9222}) not connected
              </span>
            </>
          )}
        </div>

        {/* Action Button: Auto launch or guide */}
        {!cdpReachable && (
          <button
            className="btn btn-primary btn-sm"
            onClick={onLaunch}
            disabled={launchLoading || loading}
            style={{ padding: '4px 12px', fontSize: 12 }}
          >
            {launchLoading ? (
              <><Loader2 size={12} className="spin" /> Launching...</>
            ) : (
              `🚀 Launch ${status?.browser_name || 'Browser'}`
            )}
          </button>
        )}
      </div>

      {/* Configuration Section (Expandable) */}
      {showConfig && (
        <div style={{ padding: '14px', border: '1px solid var(--border)', borderRadius: 8, background: 'var(--surface-container-low)', marginBottom: 16 }}>
          <h4 style={{ margin: '0 0 12px 0', fontSize: 14, fontWeight: 600 }}>Select Automation Browser</h4>
          
          {/* Radio Browser Selector */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 10, marginBottom: 16 }}>
            {[
              { id: 'brave', name: '🦁 Brave', desc: 'Brave Browser' },
              { id: 'chrome', name: '🌐 Chrome', desc: 'Google Chrome' },
              { id: 'edge', name: '🌊 Edge', desc: 'Microsoft Edge' },
              { id: 'custom', name: '⚙️ Custom', desc: 'Custom Path' }
            ].map(b => (
              <label key={b.id} style={{
                display: 'flex', flexDirection: 'column', padding: '10px', borderRadius: 8,
                border: `2px solid ${currentBrowser === b.id ? 'var(--primary)' : 'var(--border)'}`,
                background: currentBrowser === b.id ? 'var(--surface-container-high)' : 'var(--surface)',
                cursor: 'pointer', textAlign: 'center'
              }}>
                <input
                  type="radio"
                  name="browser_select"
                  value={b.id}
                  checked={currentBrowser === b.id}
                  onChange={() => handleBrowserChange(b.id)}
                  style={{ display: 'none' }}
                />
                <span style={{ fontWeight: 600, fontSize: 13 }}>{b.name}</span>
                <span style={{ fontSize: 11, color: 'var(--outline)', marginTop: 2 }}>{b.desc}</span>
              </label>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
            {/* CDP Port Input */}
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" style={{ fontSize: 12 }}>CDP Debugging Port</label>
              <input
                type="number"
                className="form-input"
                value={portInput}
                onChange={e => setPortInput(parseInt(e.target.value) || 9222)}
                onBlur={handlePortBlur}
                style={{ padding: '6px 10px', fontSize: 13 }}
              />
            </div>

            {/* Custom Binary Path Input */}
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label" style={{ fontSize: 12 }}>
                Custom Executable Path {currentBrowser !== 'custom' ? '(Optional Override)' : '(Required)'}
              </label>
              <input
                type="text"
                className="form-input"
                placeholder={
                  currentBrowser === 'brave' ? "e.g. C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe" :
                  currentBrowser === 'chrome' ? "e.g. C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" :
                  currentBrowser === 'edge' ? "e.g. C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" :
                  "e.g. C:\\Program Files\\Vivaldi\\Application\\vivaldi.exe"
                }
                value={customPathInput}
                onChange={e => setCustomPathInput(e.target.value)}
                onBlur={handlePathBlur}
                style={{ padding: '6px 10px', fontSize: 13 }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Manual Launch Commands Panel (Guide when not reachable) */}
      {!cdpReachable && launchCommands && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ padding: '10px 12px', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 8, fontSize: 12.5, marginBottom: 10, display: 'flex', gap: 8, alignItems: 'flex-start' }}>
            <ShieldAlert size={16} color="#c2410c" style={{ flexShrink: 0, marginTop: 1 }} />
            <div>
              <strong>Live Browser Connection Required:</strong> Make sure all existing instances of {status?.browser_name} are fully closed, then launch it with remote debugging enabled.
            </div>
          </div>

          {/* CLI Tab bar */}
          <div style={{ display: 'flex', background: 'var(--surface-container-high)', borderRadius: '6px 6px 0 0', border: '1px solid var(--border)', borderBottom: 'none', padding: '2px 4px 0' }}>
            {(['powershell', 'cmd', 'bash'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveCliTab(tab)}
                style={{
                  padding: '6px 12px', fontSize: 11, fontWeight: 600, border: 'none', background: activeCliTab === tab ? 'var(--surface)' : 'none',
                  borderBottom: activeCliTab === tab ? '2px solid var(--primary)' : 'none', borderRadius: '4px 4px 0 0', cursor: 'pointer',
                  color: activeCliTab === tab ? 'var(--primary)' : 'var(--outline)'
                }}
              >
                {tab === 'powershell' ? 'PowerShell (Windows)' : tab === 'cmd' ? 'CMD (Windows)' : 'Terminal (macOS/Linux)'}
              </button>
            ))}
          </div>

          {/* CLI Code Block */}
          <div style={{
            position: 'relative', background: '#1e293b', color: '#f8fafc', padding: '12px 14px',
            borderRadius: '0 0 6px 6px', fontFamily: 'monospace', fontSize: 12, border: '1px solid var(--border)',
            overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all'
          }}>
            <code>{launchCommands[activeCliTab]}</code>
            <button
              onClick={() => handleCopy(launchCommands[activeCliTab])}
              style={{
                position: 'absolute', right: 8, top: 8, background: '#334155', color: '#f8fafc',
                border: 'none', borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11,
                display: 'flex', alignItems: 'center', gap: 4
              }}
            >
              <Copy size={12} /> {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
        </div>
      )}

      {/* Portals List */}
      <h4 style={{ margin: '0 0 10px 0', fontSize: 13, color: 'var(--outline)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.05em' }}>Logged-in Portals</h4>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8 }}>
        {Object.entries(status?.portals || {}).map(([portal, loggedIn]) => (
          <div key={portal} style={{
            padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', gap: 8,
            background: loggedIn ? '#f0fdf4' : 'var(--surface)',
          }}>
            {loggedIn
              ? <CheckCircle size={15} color="#16a34a" />
              : <XCircle size={15} color="#94a3b8" />
            }
            <span style={{ fontSize: 13, fontWeight: 500 }}>{PORTAL_LABELS[portal] || portal}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatsPanel({ stats }: { stats: any }) {
  if (!stats) return null;
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10, marginBottom: 16 }}>
      {[
        { label: 'Total Applied', value: stats.total_applied ?? 0, icon: CheckCircle, color: '#16a34a' },
        { label: 'This Week', value: stats.applied_this_week ?? 0, icon: Clock, color: '#0369a1' },
        { label: 'Pending Review', value: stats.queued_for_review ?? 0, icon: AlertTriangle, color: '#ca8a04' },
      ].map(({ label, value, icon: Icon, color }) => (
        <div key={label} className="card" style={{ padding: '12px 16px', margin: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <Icon size={15} color={color} />
            <span style={{ fontSize: 12, color: 'var(--outline)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.05em' }}>{label}</span>
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: 'var(--on-surface)' }}>{value}</div>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────

export const JobsView: React.FC<Props> = ({ onLoadingChange }) => {
  const [tab, setTab] = useState<'queue' | 'listings' | 'history' | 'errors'>('queue');
  const [browserStatus, setBrowserStatus] = useState<BrowserStatus | null>(null);
  const [browserLoading, setBrowserLoading] = useState(false);

  const [queue, setQueue] = useState<JobListing[]>([]);
  const [listings, setListings] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [errors, setErrors] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const [runResult, setRunResult] = useState<any>(null);
  const [runLoading, setRunLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [launchLoading, setLaunchLoading] = useState(false);

  const [statusFilter, setStatusFilter] = useState('');
  const [rejectReason, setRejectReason] = useState<Record<number, string>>({});

  const setL = (v: boolean) => { setLoading(v); onLoadingChange?.(v); };

  // ── Fetchers ──────────────────────────────────────────────────────────────

  const loadBrowserStatus = useCallback(async () => {
    setBrowserLoading(true);
    try { setBrowserStatus(await api.getBrowserStatus()); }
    catch (e) { console.error(e); }
    finally { setBrowserLoading(false); }
  }, []);

  const loadStats = useCallback(async () => {
    try { setStats(await api.getJobStats()); } catch (e) { console.error(e); }
  }, []);

  const loadQueue = useCallback(async () => {
    setL(true);
    try { setQueue(await api.getJobQueue()); } catch (e) { console.error(e); }
    finally { setL(false); }
  }, []);

  const loadListings = useCallback(async () => {
    setL(true);
    try {
      const res = await api.getJobListings({ status: statusFilter || undefined });
      setListings(res.listings || []);
    } catch (e) { console.error(e); }
    finally { setL(false); }
  }, [statusFilter]);

  const loadHistory = useCallback(async () => {
    setL(true);
    try {
      const res = await api.getJobHistory();
      setHistory(res.items || []);
    } catch (e) { console.error(e); }
    finally { setL(false); }
  }, []);

  const loadErrors = useCallback(async () => {
    setL(true);
    try { setErrors(await api.getJobErrors()); } catch (e) { console.error(e); }
    finally { setL(false); }
  }, []);

  // Initial load
  useEffect(() => {
    loadBrowserStatus();
    loadStats();
  }, []);

  useEffect(() => {
    if (tab === 'queue') loadQueue();
    else if (tab === 'listings') loadListings();
    else if (tab === 'history') loadHistory();
    else if (tab === 'errors') loadErrors();
  }, [tab]);

  // ── Actions ───────────────────────────────────────────────────────────────

  const handleRunPipeline = async () => {
    setRunLoading(true);
    setRunResult(null);
    try {
      const res = await api.runJobPipeline();
      setRunResult(res);
      await Promise.all([loadStats(), loadQueue()]);
    } catch (e: any) {
      setRunResult({ error: e.message });
    } finally {
      setRunLoading(false);
    }
  };

  const handleSearchAndScore = async () => {
    setSearchLoading(true);
    setRunResult(null);
    try {
      const s = await api.searchJobs();
      const sc = await api.scoreJobs();
      setRunResult({ ...s, ...sc, mode: 'search_score_only' });
      await Promise.all([loadStats(), loadQueue(), loadListings()]);
    } catch (e: any) {
      setRunResult({ error: e.message });
    } finally {
      setSearchLoading(false);
    }
  };

  const handleLaunchBrowser = async () => {
    setLaunchLoading(true);
    try {
      const res = await api.launchBrowser();
      if (res && res.message) {
        alert(res.message);
      }
      // Staggered check to wait for browser to spin up
      await new Promise(r => setTimeout(r, 1500));
      await loadBrowserStatus();
    } catch (e: any) {
      alert("Error launching browser: " + e.message);
    } finally {
      setLaunchLoading(false);
    }
  };

  const handleConfigUpdate = async (data: { browser_type: string; browser_cdp_port?: number; browser_custom_path?: string }) => {
    setBrowserLoading(true);
    try {
      const res = await api.updateBrowserConfig(data);
      setBrowserStatus(res);
    } catch (e: any) {
      alert("Error updating browser config: " + e.message);
    } finally {
      setBrowserLoading(false);
    }
  };

  const handleApprove = async (id: number) => {
    try {
      await api.approveJob(id);
      setQueue(q => q.filter(j => j.id !== id));
      await loadStats();
    } catch (e: any) { alert(e.message); }
  };

  const handleReject = async (id: number) => {
    const reason = rejectReason[id] || '';
    try {
      await api.rejectJob(id, reason);
      setQueue(q => q.filter(j => j.id !== id));
      await loadStats();
    } catch (e: any) { alert(e.message); }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  const TabBtn = ({ id, label, icon: Icon }: { id: typeof tab; label: string; icon: any }) => (
    <button
      className={`btn ${tab === id ? 'btn-primary' : 'btn-secondary'} btn-sm`}
      onClick={() => setTab(id)}
    >
      <Icon size={14} /> {label}
    </button>
  );

  return (
    <div style={{ padding: '24px', maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Job Application Agent</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--outline)', fontSize: 14 }}>
            Autonomous search → score → apply pipeline
          </p>
        </div>

        {/* Run Controls */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary btn-sm" onClick={handleSearchAndScore} disabled={searchLoading || runLoading}>
            {searchLoading ? <Loader2 size={14} className="spin" /> : <Search size={14} />}
            Search + Score
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleRunPipeline} disabled={runLoading || searchLoading}>
            {runLoading ? <Loader2 size={14} className="spin" /> : <Zap size={14} />}
            Run Full Pipeline
          </button>
        </div>
      </div>

      {/* Run result banner */}
      {runResult && (
        <div style={{
          padding: '12px 16px', borderRadius: 8, marginBottom: 16,
          background: runResult.error ? '#fee2e2' : '#f0fdf4',
          border: `1px solid ${runResult.error ? '#fca5a5' : '#bbf7d0'}`,
          fontSize: 13,
        }}>
          {runResult.error ? (
            <span style={{ color: '#dc2626' }}>❌ {runResult.error}</span>
          ) : (
            <span style={{ color: '#15803d' }}>
              ✅ {runResult.mode === 'search_score_only'
                ? `Found ${runResult.new ?? 0} new listings • Scored ${runResult.scored ?? 0} • Auto-approved ${runResult.auto_approved ?? 0} • Queued for review ${runResult.queued_for_review ?? 0}`
                : `Searched ${runResult.searched ?? 0} portals • ${runResult.new_listings ?? 0} new • Scored ${runResult.scored ?? 0} • Applied ${runResult.applied ?? 0} • Manual needed ${runResult.manual_needed ?? 0}${runResult.browser_unavailable ? ' • ⚠️ Browser offline (apply skipped)' : ''}${runResult.daily_cap_hit ? ' • 🛑 Daily cap reached' : ''}`
              }
            </span>
          )}
        </div>
      )}

      {/* Portal status + stats */}
      <PortalStatusPanel
        status={browserStatus}
        loading={browserLoading}
        onRefresh={loadBrowserStatus}
        onConfigUpdate={handleConfigUpdate}
        onLaunch={handleLaunchBrowser}
        launchLoading={launchLoading}
      />
      <StatsPanel stats={stats} />

      {/* Tab navigation */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        <TabBtn id="queue" label="Approval Queue" icon={ThumbsUp} />
        <TabBtn id="listings" label="All Listings" icon={List} />
        <TabBtn id="history" label="Applied History" icon={History} />
        <TabBtn id="errors" label="Errors" icon={AlertCircle} />
      </div>

      {/* ── APPROVAL QUEUE ─────────────────────────────────────────────────── */}
      {tab === 'queue' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Semi-Auto Approval Queue ({queue.length})</h3>
            <button className="btn btn-secondary btn-sm" onClick={loadQueue} disabled={loading}>
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
            </button>
          </div>

          {loading ? <SkeletonTable rows={5} columns={6} /> : queue.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--outline)' }}>
              <CheckCircle size={36} color="#94a3b8" />
              <p>No listings awaiting approval. Run the pipeline to discover jobs.</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Company', 'Title', 'Portal', 'Score', 'Reason', 'Location', 'JD', 'Actions'].map(h => (
                      <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--outline)', whiteSpace: 'nowrap' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {queue.map((job) => (
                    <tr key={job.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '10px', fontWeight: 600 }}>{job.company || '—'}</td>
                      <td style={{ padding: '10px', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {job.job_title}
                      </td>
                      <td style={{ padding: '10px' }}>
                        <span className="chip">{PORTAL_LABELS[job.portal] || job.portal}</span>
                      </td>
                      <td style={{ padding: '10px' }}><ScoreChip score={job.match_score} /></td>
                      <td style={{ padding: '10px', maxWidth: 200, color: 'var(--outline)', fontSize: 12 }}>
                        {job.match_reason || '—'}
                      </td>
                      <td style={{ padding: '10px', color: 'var(--outline)', whiteSpace: 'nowrap' }}>{job.location || '—'}</td>
                      <td style={{ padding: '10px' }}>
                        {job.job_url && (
                          <a href={job.job_url} target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm" style={{ padding: '3px 8px' }}>
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </td>
                      <td style={{ padding: '10px' }}>
                        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                          <button
                            className="btn btn-primary btn-sm"
                            style={{ padding: '4px 10px' }}
                            onClick={() => handleApprove(job.id)}
                          >
                            <ThumbsUp size={12} /> Approve
                          </button>
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '4px 10px' }}
                            onClick={() => handleReject(job.id)}
                          >
                            <ThumbsDown size={12} /> Skip
                          </button>
                        </div>
                        <input
                          type="text"
                          placeholder="Reason (optional)"
                          value={rejectReason[job.id] || ''}
                          onChange={e => setRejectReason(r => ({ ...r, [job.id]: e.target.value }))}
                          style={{ marginTop: 4, fontSize: 11, padding: '2px 6px', borderRadius: 4, border: '1px solid var(--border)', width: 140 }}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── ALL LISTINGS ───────────────────────────────────────────────────── */}
      {tab === 'listings' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
            <h3 style={{ margin: 0 }}>All Listings</h3>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                style={{ fontSize: 13, padding: '5px 10px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--surface)' }}
              >
                <option value="">All statuses</option>
                {['new', 'scored', 'approved', 'applied', 'skipped'].map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <button className="btn btn-secondary btn-sm" onClick={loadListings} disabled={loading}>
                <RefreshCw size={14} className={loading ? 'spin' : ''} />
              </button>
            </div>
          </div>

          {loading ? <SkeletonTable rows={8} columns={6} /> : listings.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--outline)' }}>
              <Search size={36} color="#94a3b8" />
              <p>No listings yet. Run the pipeline to start discovering jobs.</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Company', 'Title', 'Portal', 'Score', 'Status', 'Location', 'JD', 'Discovered'].map(h => (
                      <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--outline)', whiteSpace: 'nowrap' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {listings.map((job: JobListing) => (
                    <tr key={job.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '10px', fontWeight: 600 }}>{job.company || '—'}</td>
                      <td style={{ padding: '10px', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{job.job_title}</td>
                      <td style={{ padding: '10px' }}><span className="chip">{PORTAL_LABELS[job.portal] || job.portal}</span></td>
                      <td style={{ padding: '10px' }}><ScoreChip score={job.match_score} /></td>
                      <td style={{ padding: '10px' }}><StatusChip status={job.status} /></td>
                      <td style={{ padding: '10px', color: 'var(--outline)' }}>{job.location || '—'}</td>
                      <td style={{ padding: '10px' }}>
                        {job.job_url && (
                          <a href={job.job_url} target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm" style={{ padding: '3px 8px' }}>
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </td>
                      <td style={{ padding: '10px', color: 'var(--outline)', whiteSpace: 'nowrap', fontSize: 12 }}>
                        {job.discovered_at ? new Date(job.discovered_at).toLocaleDateString() : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── HISTORY ────────────────────────────────────────────────────────── */}
      {tab === 'history' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Application History ({history.length})</h3>
            <button className="btn btn-secondary btn-sm" onClick={loadHistory} disabled={loading}>
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
            </button>
          </div>

          {loading ? <SkeletonTable rows={8} columns={5} /> : history.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--outline)' }}>
              <History size={36} color="#94a3b8" />
              <p>No applications submitted yet.</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Company', 'Title', 'Portal', 'Applied At', 'Status', 'JD'].map(h => (
                      <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: 'var(--outline)', whiteSpace: 'nowrap' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {history.map((app: any) => (
                    <tr key={app.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '10px', fontWeight: 600 }}>{app.company || '—'}</td>
                      <td style={{ padding: '10px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{app.job_title}</td>
                      <td style={{ padding: '10px' }}><span className="chip">{PORTAL_LABELS[app.portal] || app.portal}</span></td>
                      <td style={{ padding: '10px', whiteSpace: 'nowrap', fontSize: 12 }}>
                        {app.applied_at ? new Date(app.applied_at).toLocaleString() : '—'}
                      </td>
                      <td style={{ padding: '10px' }}><StatusChip status={app.application_status} /></td>
                      <td style={{ padding: '10px' }}>
                        {app.job_url && (
                          <a href={app.job_url} target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm" style={{ padding: '3px 8px' }}>
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── ERRORS ─────────────────────────────────────────────────────────── */}
      {tab === 'errors' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Failed & Manual-Needed ({errors.length})</h3>
            <button className="btn btn-secondary btn-sm" onClick={loadErrors} disabled={loading}>
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
            </button>
          </div>

          {loading ? <SkeletonTable rows={5} columns={5} /> : errors.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--outline)' }}>
              <CheckCircle size={36} color="#16a34a" />
              <p>No errors — all applications succeeded!</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {errors.map((err: any) => (
                <div key={err.id} style={{
                  padding: '12px 16px', borderRadius: 8,
                  background: err.application_status === 'manual_needed' ? '#fff7ed' : '#fef2f2',
                  border: `1px solid ${err.application_status === 'manual_needed' ? '#fed7aa' : '#fca5a5'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <strong>{err.job_title}</strong>
                      {err.company && <span style={{ color: 'var(--outline)', marginLeft: 8 }}>@ {err.company}</span>}
                      <div style={{ marginTop: 4 }}>
                        <StatusChip status={err.application_status} />
                        <span className="chip" style={{ marginLeft: 6 }}>{PORTAL_LABELS[err.portal] || err.portal}</span>
                      </div>
                      {err.error_msg && (
                        <p style={{ margin: '6px 0 0', fontSize: 12, color: '#dc2626' }}>
                          Error: {err.error_msg}
                        </p>
                      )}
                      {err.application_status === 'manual_needed' && (
                        <p style={{ margin: '6px 0 0', fontSize: 12, color: '#92400e' }}>
                          ⚠️ CAPTCHA or OTP detected. Please complete manually.
                        </p>
                      )}
                    </div>
                    {err.job_url && (
                      <a href={err.job_url} target="_blank" rel="noreferrer" className="btn btn-secondary btn-sm">
                        <ExternalLink size={12} /> View JD
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default JobsView;
