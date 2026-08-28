import React, { useState, useEffect } from 'react';
import { Search, Share2, CheckCircle, Loader2, MailSearch } from 'lucide-react';
import { api } from '../api';
import { SkeletonTable } from './Skeleton';

interface ScraperViewProps {
  onLoadingChange?: (loading: boolean) => void;
  onRefresh?: () => void;
}


export const ScraperView: React.FC<ScraperViewProps> = ({ onLoadingChange, onRefresh }) => {
  const [activeChannel, setActiveChannel] = useState<'auto_discover' | 'career' | 'github' | 'job_portal' | 'linkedin' | 'enrichment'>('linkedin');
  const [inputVal, setInputVal] = useState('');
  const [enrichDomain, setEnrichDomain] = useState('');
  const [enrichFirstName, setEnrichFirstName] = useState('');
  const [enrichLastName, setEnrichLastName] = useState('');

  const [queue, setQueue] = useState<any[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [normalizing, setNormalizing] = useState(false);
  const [msg, setMsg] = useState('');

  const loadQueue = async () => {
    onLoadingChange?.(true);
    try {
      const items = await api.listScrapeQueue();
      setQueue(items);
    } catch (e: any) {
      console.error(e);
    } finally {
      setInitialLoading(false);
      onLoadingChange?.(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  /*
  const handleAutoDiscover = async () => {
    setAutoDiscovering(true);
    onLoadingChange?.(true);
    setMsg('');
    try {
      const res = await api.autoDiscoverJobs();

      // Handle no-new-leads case (backend skipped DB write)
      if (res.status === 'no_new_leads') {
        setMsg('✅ Auto-Discover ran successfully — no NEW leads found this time. All discovered companies are already in your contacts or queue.');
        return;
      }

      const count = res.raw_data?.total_unique_emails || 0;
      const roles = res.raw_data?.roles_searched?.join(', ') || '';
      const leads: any[] = res.raw_data?.found_leads || [];
      const companies = [...new Set(leads.map((l: any) => l.company).filter(Boolean))].slice(0, 6).join(', ');
      const newAdded = res.new_contacts_added ?? count;
      setMsg(
        `✅ Quality Auto-Discover complete for [${roles}]! Found ${count} new verified leads from: ${companies || 'multiple companies'}. ${newAdded} contacts added to your pipeline.`
      );

      await loadQueue();
      onRefresh?.();
    } catch (err: any) {
      setMsg('Auto-Discover error: ' + err.message);
    } finally {
      setAutoDiscovering(false);
      onLoadingChange?.(false);
    }
  };
  */


  const handleRunScraper = async (e: React.FormEvent) => {
    e.preventDefault();
    if (activeChannel === 'enrichment') {
      return handleRunEnrichment(e);
    }
    if (!inputVal) return;
    setLoading(true);
    onLoadingChange?.(true);
    setMsg('');

    try {
      if (activeChannel === 'career') {
        await api.scrapeCareerPage(inputVal);
      } else if (activeChannel === 'github') {
        await api.scrapeGithub(inputVal);
      } else if (activeChannel === 'job_portal') {
        await api.scrapeJobPortal(inputVal);
      } else if (activeChannel === 'linkedin') {
        await api.scrapeLinkedin(inputVal);
      }
      setMsg(`Lead search succeeded for ${activeChannel}! Items landed in Lead Queue.`);
      setInputVal('');
      await loadQueue();
    } catch (err: any) {
      setMsg('Lead discovery error: ' + err.message);
    } finally {
      setLoading(false);
      onLoadingChange?.(false);
    }
  };

  const handleRunEnrichment = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    onLoadingChange?.(true);
    setMsg('');

    try {
      await api.enrichApollo(enrichFirstName, enrichLastName, enrichDomain);
      setMsg(`Email enrichment completed via Apollo! Result added to Lead Queue.`);
      await loadQueue();
    } catch (err: any) {
      setMsg('Enrichment error: ' + err.message);
    } finally {
      setLoading(false);
      onLoadingChange?.(false);
    }
  };

  const handleNormalize = async () => {
    setNormalizing(true);
    onLoadingChange?.(true);
    try {
      const res = await api.runNormalizer();
      setMsg(res.message);
      await loadQueue();
      onRefresh?.();
    } catch (err: any) {
      setMsg('Normalizer error: ' + err.message);
    } finally {
      setNormalizing(false);
      onLoadingChange?.(false);
    }
  };


  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Lead Discovery & Enrichment Hub</h1>
          <p className="page-subtitle">Search and discover leads via LinkedIn</p>
        </div>
      </div>

      {msg && <div className="alert alert-info">{msg}</div>}

      {/* Auto-Discover card removed as scraper layer is deactivated */}

      {/* Lead Discovery Source Tabs */}
      <div className="card">
        <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', borderBottom: '1px solid var(--border)', paddingBottom: '12px', flexWrap: 'wrap' }}>
          {/*
          <button className={`btn ${activeChannel === 'auto_discover' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveChannel('auto_discover')}>
            <Sparkles size={16} /> Auto-Discover Info
          </button>
          <button className={`btn ${activeChannel === 'enrichment' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveChannel('enrichment')}>
            <MailSearch size={16} /> Apollo Email Lookup
          </button>
          <button className={`btn ${activeChannel === 'career' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveChannel('career')}>
            <Globe size={16} /> Company Webpage
          </button>
          <button className={`btn ${activeChannel === 'github' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveChannel('github')}>
            <Code size={16} /> GitHub Context
          </button>
          <button className={`btn ${activeChannel === 'job_portal' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveChannel('job_portal')}>
            <Search size={16} /> Job Search results
          </button>
          */}
          <button className={`btn ${activeChannel === 'linkedin' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveChannel('linkedin')}>
            <Share2 size={16} /> LinkedIn Listing
          </button>
        </div>

        {/*
        {activeChannel === 'auto_discover' && (
          <div style={{ padding: '12px', background: 'var(--surface-container-low)', borderRadius: '8px', fontSize: '14px' }}>
            <p><strong>Keyword Auto-Discover:</strong> Uses your saved target roles in <em>Resume & Context</em> to search for live job openings on LinkedIn Jobs, Naukri, and Indeed.</p>
            <button className="btn btn-primary btn-sm" onClick={handleAutoDiscover} disabled={autoDiscovering} style={{ marginTop: '8px' }}>
              {autoDiscovering ? <><Loader2 size={14} className="spin-icon" /> Running...</> : <><Sparkles size={14} /> Start Auto-Discover Search</>}
            </button>
          </div>
        )}
        */}

        {activeChannel === 'enrichment' && (
          <form onSubmit={handleRunEnrichment} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
            <input type="text" className="form-input" placeholder="First Name (e.g. Satya)" value={enrichFirstName} onChange={(e) => setEnrichFirstName(e.target.value)} required />
            <input type="text" className="form-input" placeholder="Last Name (e.g. Nadella)" value={enrichLastName} onChange={(e) => setEnrichLastName(e.target.value)} required />
            <input type="text" className="form-input" placeholder="Company Domain (e.g. microsoft.com)" value={enrichDomain} onChange={(e) => setEnrichDomain(e.target.value)} required />
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ gridColumn: '1 / -1' }}>
              {loading ? <><Loader2 size={16} className="spin-icon" /> Finding Email...</> : <><MailSearch size={16} /> Run Apollo Email Finder</>}
            </button>
          </form>
        )}

        {activeChannel !== 'auto_discover' && activeChannel !== 'enrichment' && (
          <form onSubmit={handleRunScraper} style={{ display: 'flex', gap: '12px' }}>
            <input
              type="text"
              className="form-input"
              style={{ flex: 1 }}
              placeholder={
                activeChannel === 'github'
                  ? 'Enter GitHub username or repo (e.g. torvalds)'
                  : 'Enter target URL (e.g. https://company.com/careers)'
              }
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              required
            />
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? (
                <><Loader2 size={16} className="spin-icon" /> Searching Source...</>
              ) : (
                <><Search size={16} /> Find Leads</>
              )}
            </button>
          </form>
        )}

        {loading && (
          <div style={{ marginTop: '16px', padding: '12px', background: 'var(--surface-container-low)', borderRadius: '6px', fontSize: '13px', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
            <Loader2 size={16} className="spin-icon" />
            <span>Searching and validating target leads with human-pace delay...</span>
          </div>
        )}
      </div>

      {/* Lead Queue Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Lead Queue ({queue.length} raw entries)</h3>
          <button className="btn btn-primary btn-sm" onClick={handleNormalize} disabled={normalizing || queue.length === 0}>
            {normalizing ? (
              <><Loader2 size={14} className="spin-icon" /> Importing...</>
            ) : (
              <><CheckCircle size={14} /> Import & Validate Leads</>
            )}
          </button>
        </div>

        {initialLoading ? (
          <SkeletonTable rows={4} columns={4} />
        ) : queue.length === 0 ? (
          <p style={{ color: 'var(--on-surface-variant)', fontSize: '14px', textAlign: 'center', padding: '24px 0' }}>
            Lead queue is empty. Use the search tabs above or click Auto-Discover to find leads.
          </p>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Discovered Emails / Leads</th>
                  <th>Discovered Date</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((item) => {
                  const emails = item.raw_data?.found_emails || [];
                  const companies = item.raw_data?.companies_found || [];
                  return (
                    <tr key={item.id}>
                      <td style={{ fontWeight: 600 }}>
                        <span className="chip chip-new">{item.source}</span>
                      </td>
                      <td>
                        {emails.length > 0 ? (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', maxWidth: '480px' }}>
                            {emails.map((e: string, idx: number) => (
                              <span key={idx} className="chip chip-personalized" style={{ fontSize: '11px', padding: '2px 8px' }}>
                                {e}
                              </span>
                            ))}
                          </div>
                        ) : companies.length > 0 ? (

                          <div style={{ fontSize: '12px', color: 'var(--on-surface-variant)' }}>
                            Discovered companies: {companies.slice(0, 4).join(', ')}
                          </div>
                        ) : (
                          <span style={{ color: 'var(--outline)', fontSize: '12px' }}>No public email found</span>
                        )}
                      </td>
                      <td style={{ fontSize: '13px', color: 'var(--on-surface-variant)' }}>
                        {new Date(item.discovered_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}
                      </td>
                      <td><span className={`chip chip-${item.status === 'processed' ? 'sent' : 'queued'}`}>{item.status}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
