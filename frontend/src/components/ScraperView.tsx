import React, { useState, useEffect } from 'react';
import { Search, Code, Globe, Share2, CheckCircle } from 'lucide-react';
import { api } from '../api';

export const ScraperView: React.FC = () => {
  const [activeChannel, setActiveChannel] = useState<'career' | 'github' | 'job_portal' | 'linkedin'>('career');
  const [inputVal, setInputVal] = useState('');
  const [queue, setQueue] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');

  const loadQueue = async () => {
    try {
      const items = await api.listScrapeQueue();
      setQueue(items);
    } catch (e: any) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const handleRunScraper = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal) return;
    setLoading(true);
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
      setMsg(`Scraper execution succeeded for ${activeChannel}! Items landed in Scrape Queue.`);
      setInputVal('');
      await loadQueue();
    } catch (err: any) {
      setMsg('Scraper error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleNormalize = async () => {
    setLoading(true);
    try {
      const res = await api.runNormalizer();
      setMsg(res.message);
      await loadQueue();
    } catch (err: any) {
      setMsg('Normalizer error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Multi-Channel Scraper Hub</h1>
          <p className="page-subtitle">Scrape publicly listed contact emails across job portals, career pages, GitHub bios & LinkedIn</p>
        </div>
      </div>

      {msg && <div className="alert alert-info">{msg}</div>}

      <div className="card">
        <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
          <button className={`btn ${activeChannel === 'career' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveChannel('career')}>
            <Globe size={16} /> Company Career Page
          </button>
          <button className={`btn ${activeChannel === 'github' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveChannel('github')}>
            <Code size={16} /> GitHub Bio / Repo
          </button>
          <button className={`btn ${activeChannel === 'job_portal' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveChannel('job_portal')}>
            <Search size={16} /> Job Portal Listing
          </button>
          <button className={`btn ${activeChannel === 'linkedin' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveChannel('linkedin')}>
            <Share2 size={16} /> LinkedIn Listing
          </button>
        </div>

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
            <Search size={16} /> {loading ? 'Scraping...' : 'Run Scraper'}
          </button>
        </form>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Scrape Queue ({queue.length} raw entries)</h3>
          <button className="btn btn-primary btn-sm" onClick={handleNormalize} disabled={loading}>
            <CheckCircle size={14} /> Run Email Normalizer
          </button>
        </div>

        {queue.length === 0 ? (
          <p style={{ color: 'var(--on-surface-variant)', fontSize: '14px', textAlign: 'center', padding: '24px 0' }}>
            Scrape queue is empty. Run a scraper above to discover leads.
          </p>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Discovered Emails</th>
                  <th>Discovered Date</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((item) => {
                  const emails = item.raw_data?.found_emails || [];
                  return (
                    <tr key={item.id}>
                      <td style={{ fontWeight: 600 }}>{item.source}</td>
                      <td>
                        {emails.length > 0 ? (
                          emails.map((e: string, idx: number) => (
                            <span key={idx} className="chip chip-personalized" style={{ marginRight: '4px' }}>{e}</span>
                          ))
                        ) : (
                          <span style={{ color: 'var(--outline)', fontSize: '12px' }}>No public email found</span>
                        )}
                      </td>
                      <td style={{ fontSize: '13px', color: 'var(--on-surface-variant)' }}>{new Date(item.discovered_at).toLocaleString()}</td>
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
