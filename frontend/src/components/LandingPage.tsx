import React, { useState } from 'react';
import { api, setToken } from '../api';
import {
  Mail,
  Lock,
  LogIn,
  UserPlus,
  Globe,
  Zap,
  Shield,
  Cpu,
  CheckCircle2,
  ArrowRight,
  Terminal,
  FileText,
  Database,
  Send,
  Activity,
  Sparkles
} from 'lucide-react';

interface LandingPageProps {
  onSuccess: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [activePipelineTab, setActivePipelineTab] = useState<number>(0);
  const [showGoogleWarning, setShowGoogleWarning] = useState(false);
  const [googleUrl, setGoogleUrl] = useState('');
  const [requestEmail, setRequestEmail] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        const res = await api.login({ email, password });
        setToken(res.access_token);
      } else {
        const res = await api.signup({ email, password });
        setToken(res.access_token);
      }
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleOAuthConnect = async () => {
    setError('');
    try {
      const res = await api.getGoogleAuthUrl();
      setGoogleUrl(res.url);
      setShowGoogleWarning(true);
    } catch (err: any) {
      setError('Failed to launch Google OAuth: ' + err.message);
    }
  };

  const scrollToAuth = () => {
    const authElem = document.getElementById('auth-section');
    if (authElem) {
      authElem.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const pipelineSteps = [
    {
      id: 0,
      title: 'Resume Context Parser',
      icon: <FileText size={16} />,
      badge: 'PARSED OK',
      content: {
        candidate: 'Alex Rivera',
        skills: ['FastAPI', 'React', 'PostgreSQL', 'Python', 'Docker'],
        experience: 'Senior Backend Engineer at TechCorp (3 yrs)',
        topProject: 'Distributed Task Queue (10k ops/sec)',
        achievement: 'Reduced API p99 latency by 45%'
      }
    },
    {
      id: 1,
      title: 'Multi-Source Scraper',
      icon: <Globe size={16} />,
      badge: 'EXTRACTED',
      content: {
        source: 'Career Page Scraper',
        targetCompany: 'Acme AI Labs',
        prospect: 'Sarah Chen (Head of Talent)',
        email: 'sarah.chen@acme.ai',
        roleMatch: 'Senior Python & Systems Architect'
      }
    },
    {
      id: 2,
      title: 'Context Matcher',
      icon: <Cpu size={16} />,
      badge: '98% MATCH',
      content: {
        score: '0.98 Tag Overlap',
        matchedExperience: 'Distributed Task Queue',
        keyHook: 'Acme AI is scaling high-throughput task pipelines',
        alignmentReason: 'Direct match on FastAPI + Python async workers'
      }
    },
    {
      id: 3,
      title: 'LLM Personalizer',
      icon: <Sparkles size={16} />,
      badge: '114 WORDS',
      content: {
        subject: 'Quick question on Acme AI\'s async worker architecture',
        body: 'Hi Sarah,\n\nI noticed Acme AI is expanding its Python systems architecture team. In my previous role, I built a distributed task queue handling 10k ops/sec with FastAPI and PostgreSQL, cutting p99 latency by 45%.\n\nWould love to share how we solved our queue bottlenecks if you\'re open to a brief chat this week.\n\nBest,\nAlex',
        constraintsPassed: ['~120 Word Limit ✓', 'No Buzzwords ✓', 'Unique Hook ✓']
      }
    },
    {
      id: 4,
      title: 'XOAUTH2 SMTP Delivery',
      icon: <Send size={16} />,
      badge: 'SENT (200 OK)',
      content: {
        mode: 'Auto Pacing (2-3/hr)',
        authMethod: 'Google OAuth2 (XOAUTH2)',
        sendTimestamp: new Date().toLocaleTimeString(),
        status: 'Delivered to Primary Inbox',
        tracking: 'IMAP Reply Polling Active'
      }
    }
  ];

  return (
    <div className="landing-wrapper">
      {/* Top Navigation */}
      <header className="landing-navbar">
        <div className="landing-navbar-container">
          <div className="landing-logo">
            <div className="landing-logo-icon">
              <Mail size={20} />
            </div>
            <div className="landing-logo-text">
              <span className="brand-name">AutoMail</span>
              <span className="brand-badge mono">COLD ENGINE v2.4</span>
            </div>
          </div>

          <nav className="landing-nav-links">
            <a href="#features">Features</a>
            <a href="#pipeline">Pipeline Architecture</a>
            <a href="#security">Security & XOAUTH2</a>
          </nav>

          <div className="landing-nav-actions">
            <button onClick={() => { setIsLogin(true); scrollToAuth(); }} className="btn btn-secondary btn-sm">
              <LogIn size={14} />
              <span>Sign In</span>
            </button>
            <button onClick={() => { setIsLogin(false); scrollToAuth(); }} className="btn btn-primary btn-sm">
              <UserPlus size={14} />
              <span>Get Started</span>
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="landing-hero">
        <div className="hero-badge mono">
          <span className="status-dot"></span>
          <span>SYSTEM OPERATIONAL • XOAUTH2 & SMTP COMPLIANT</span>
        </div>

        <h1 className="hero-headline">
          Precision Cold Outreach Engine for High-Performance Teams
        </h1>

        <p className="hero-subline">
          Automate hyper-personalized email campaigns with LLM context matching, multi-source scraping,
          rate-limited queueing, and native Google OAuth2 delivery—all in an isolated multi-tenant environment.
        </p>

        <div className="hero-cta-group">
          <button onClick={() => { setIsLogin(false); scrollToAuth(); }} className="btn btn-primary hero-btn">
            <span>Launch Workspace</span>
            <ArrowRight size={16} />
          </button>
          <a href="#pipeline" className="btn btn-secondary hero-btn">
            <Terminal size={16} />
            <span>Explore Architecture</span>
          </a>
        </div>

        {/* Spec Pill Bar */}
        <div className="hero-spec-grid">
          <div className="hero-spec-item">
            <span className="spec-val mono">2-3 / hr</span>
            <span className="spec-label">Rate-Limited Pacing</span>
          </div>
          <div className="hero-spec-divider"></div>
          <div className="hero-spec-item">
            <span className="spec-val mono">~120 Wds</span>
            <span className="spec-label">Strict LLM Word Cap</span>
          </div>
          <div className="hero-spec-divider"></div>
          <div className="hero-spec-item">
            <span className="spec-val mono">XOAUTH2</span>
            <span className="spec-label">Google Native Sync</span>
          </div>
          <div className="hero-spec-divider"></div>
          <div className="hero-spec-item">
            <span className="spec-val mono">100%</span>
            <span className="spec-label">Isolated Multi-Tenant</span>
          </div>
        </div>
      </section>

      {/* Split Section: Auth Card + Live Pipeline Simulator */}
      <section id="auth-section" className="landing-split-container">
        {/* Left Card: Auth Form */}
        <div className="auth-card-container card">
          <div className="auth-header">
            <div className="auth-pill-toggle">
              <button
                type="button"
                className={`auth-toggle-btn ${isLogin ? 'active' : ''}`}
                onClick={() => setIsLogin(true)}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`auth-toggle-btn ${!isLogin ? 'active' : ''}`}
                onClick={() => setIsLogin(false)}
              >
                Create Account
              </button>
            </div>
          </div>

          <div style={{ margin: '16px 0 20px 0' }}>
            <h3 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--on-surface)' }}>
              {isLogin ? 'Welcome Back' : 'Create Isolated Account'}
            </h3>
            <p className="page-subtitle">
              {isLogin
                ? 'Sign in to access your cold outreach dashboard & queued sends.'
                : 'Get started with isolated context tables & automated scraping.'}
            </p>
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          {/* Official Google OAuth2 Button */}
          <button
            type="button"
            onClick={handleGoogleOAuthConnect}
            className="btn btn-secondary google-oauth-btn"
          >
            <Globe size={18} color="#4285F4" />
            <span>Connect with Google (Official OAuth2)</span>
          </button>

          <div className="auth-divider">
            <div className="divider-line"></div>
            <span className="divider-text mono">OR EMAIL AUTH</span>
            <div className="divider-line"></div>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Work Email</label>
              <div className="input-with-icon">
                <Mail size={16} className="input-icon" />
                <input
                  type="email"
                  className="form-input icon-padded"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '20px' }}>
              <label className="form-label">Password</label>
              <div className="input-with-icon">
                <Lock size={16} className="input-icon" />
                <input
                  type="password"
                  className="form-input icon-padded"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary auth-submit-btn"
              disabled={loading}
            >
              {loading ? (
                'Processing Request...'
              ) : isLogin ? (
                <><LogIn size={16} /> Sign In to Dashboard</>
              ) : (
                <><UserPlus size={16} /> Create New Account</>
              )}
            </button>
          </form>

          <div className="auth-footer-note">
            <Shield size={14} color="var(--outline)" />
            <span>Encrypted with AES-256 at rest. Zero plaintext logging.</span>
          </div>
        </div>

        {/* Right Card: Interactive Live Pipeline Simulator */}
        <div id="pipeline" className="pipeline-simulator-card card">
          <div className="simulator-header">
            <div className="simulator-title">
              <Activity size={18} color="var(--primary)" />
              <span>Live Pipeline Architecture</span>
            </div>
            <span className="chip chip-personalized mono">INTERACTIVE SIMULATION</span>
          </div>

          <p className="simulator-desc">
            Click through each stage to see how raw resume context is transformed into hyper-personalized, rate-limited email dispatches:
          </p>

          {/* Stepper Tabs */}
          <div className="simulator-tabs">
            {pipelineSteps.map((step) => (
              <button
                key={step.id}
                type="button"
                className={`tab-step-btn ${activePipelineTab === step.id ? 'active' : ''}`}
                onClick={() => setActivePipelineTab(step.id)}
              >
                {step.icon}
                <span className="step-num mono">0{step.id + 1}</span>
              </button>
            ))}
          </div>

          {/* Active Step Panel */}
          <div className="simulator-output-box">
            <div className="output-topbar">
              <div className="output-title">
                <span className="step-tag mono">STAGE 0{activePipelineTab + 1}:</span>
                <strong>{pipelineSteps[activePipelineTab].title}</strong>
              </div>
              <span className="chip chip-new mono">{pipelineSteps[activePipelineTab].badge}</span>
            </div>

            <div className="output-content">
              {activePipelineTab === 0 && (
                <div className="code-display">
                  <div className="json-line"><span className="json-key">"candidate":</span> <span className="json-val">"{pipelineSteps[0].content.candidate}"</span></div>
                  <div className="json-line"><span className="json-key">"skills":</span> <span className="json-val">{JSON.stringify(pipelineSteps[0].content.skills)}</span></div>
                  <div className="json-line"><span className="json-key">"experience":</span> <span className="json-val">"{pipelineSteps[0].content.experience}"</span></div>
                  <div className="json-line"><span className="json-key">"topProject":</span> <span className="json-val">"{pipelineSteps[0].content.topProject}"</span></div>
                  <div className="json-line"><span className="json-key">"achievement":</span> <span className="json-val">"{pipelineSteps[0].content.achievement}"</span></div>
                </div>
              )}

              {activePipelineTab === 1 && (
                <div className="code-display">
                  <div className="json-line"><span className="json-key">"source":</span> <span className="json-val">"{pipelineSteps[1].content.source}"</span></div>
                  <div className="json-line"><span className="json-key">"targetCompany":</span> <span className="json-val">"{pipelineSteps[1].content.targetCompany}"</span></div>
                  <div className="json-line"><span className="json-key">"prospect":</span> <span className="json-val">"{pipelineSteps[1].content.prospect}"</span></div>
                  <div className="json-line"><span className="json-key">"email":</span> <span className="json-val">"{pipelineSteps[1].content.email}"</span></div>
                  <div className="json-line"><span className="json-key">"roleMatch":</span> <span className="json-val">"{pipelineSteps[1].content.roleMatch}"</span></div>
                </div>
              )}

              {activePipelineTab === 2 && (
                <div className="code-display">
                  <div className="json-line"><span className="json-key">"overlapScore":</span> <span className="json-val">"{pipelineSteps[2].content.score}"</span></div>
                  <div className="json-line"><span className="json-key">"matchedExperience":</span> <span className="json-val">"{pipelineSteps[2].content.matchedExperience}"</span></div>
                  <div className="json-line"><span className="json-key">"keyHook":</span> <span className="json-val">"{pipelineSteps[2].content.keyHook}"</span></div>
                  <div className="json-line"><span className="json-key">"alignmentReason":</span> <span className="json-val">"{pipelineSteps[2].content.alignmentReason}"</span></div>
                </div>
              )}

              {activePipelineTab === 3 && (
                <div className="email-preview-box">
                  <div className="preview-subject">
                    <span className="mono" style={{ fontSize: '12px', color: 'var(--outline)' }}>SUBJECT:</span>
                    <strong>{pipelineSteps[3].content.subject}</strong>
                  </div>
                  <div className="preview-body">
                    {pipelineSteps[3].content.body}
                  </div>
                  <div className="preview-chips">
                    {['~120 Word Limit ✓', 'No Buzzwords ✓', 'Unique Hook ✓'].map((c, idx) => (
                      <span key={idx} className="chip chip-replied mono">{c}</span>
                    ))}
                  </div>
                </div>
              )}

              {activePipelineTab === 4 && (
                <div className="code-display">
                  <div className="json-line"><span className="json-key">"sendMode":</span> <span className="json-val">"{pipelineSteps[4].content.mode}"</span></div>
                  <div className="json-line"><span className="json-key">"authMethod":</span> <span className="json-val">"{pipelineSteps[4].content.authMethod}"</span></div>
                  <div className="json-line"><span className="json-key">"timestamp":</span> <span className="json-val">"{pipelineSteps[4].content.sendTimestamp}"</span></div>
                  <div className="json-line"><span className="json-key">"status":</span> <span className="json-val">"{pipelineSteps[4].content.status}"</span></div>
                  <div className="json-line"><span className="json-key">"tracking":</span> <span className="json-val">"{pipelineSteps[4].content.tracking}"</span></div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid Section */}
      <section id="features" className="landing-features-section">
        <div className="section-header">
          <span className="chip chip-new mono">CORE CAPABILITIES</span>
          <h2>Designed for High-Volume, Zero-Slop Outreach</h2>
          <p className="section-subtitle">
            Every component is built around maximum reliability, strict anti-spam pacing, and deep context matching.
          </p>
        </div>

        <div className="features-grid">
          <div className="feature-card card">
            <div className="feature-icon">
              <Cpu size={24} color="var(--primary)" />
            </div>
            <h3>Context Matching Engine</h3>
            <p>
              LLM automatically parses your resume into skills, experiences, and projects, matching them against lead job requirements with high tag overlap.
            </p>
          </div>

          <div className="feature-card card">
            <div className="feature-icon">
              <Globe size={24} color="var(--primary)" />
            </div>
            <h3>Multi-Source Lead Scraping</h3>
            <p>
              Safely extract verified leads from Career Pages, GitHub repositories, AngelList, and LinkedIn with rate-limited, human-paced workers.
            </p>
          </div>

          <div className="feature-card card">
            <div className="feature-icon">
              <Globe size={24} color="#4285F4" />
            </div>
            <h3>Google XOAUTH2 Integration</h3>
            <p>
              Send emails using official Google OAuth2 tokens with automatic refresh token rotation. No raw SMTP passwords stored or logged.
            </p>
          </div>

          <div className="feature-card card">
            <div className="feature-icon">
              <Zap size={24} color="var(--primary)" />
            </div>
            <h3>Autonomous Send Queue & Pacing</h3>
            <p>
              Protect domain reputation with strict rate-limiting (2-3 sends/hour) and custom schedule windows (e.g., 08:00–23:00).
            </p>
          </div>

          <div className="feature-card card">
            <div className="feature-icon">
              <Database size={24} color="var(--primary)" />
            </div>
            <h3>IMAP Reply & Bounce Tracker</h3>
            <p>
              Background workers poll your inbox via IMAP to catch prospect replies or soft bounces, auto-pausing campaigns instantly.
            </p>
          </div>

          <div className="feature-card card">
            <div className="feature-icon">
              <Shield size={24} color="var(--primary)" />
            </div>
            <h3>Multi-Tenant Sandbox</h3>
            <p>
              Complete data isolation per user. Secret keys, resumes, scraped contacts, and send logs remain strictly private and encrypted.
            </p>
          </div>
        </div>
      </section>

      {/* Security & Architecture */}
      <section id="security" className="landing-security-section">
        <div className="security-card card">
          <div className="security-content">
            <div className="security-badge mono">
              <Shield size={16} />
              <span>ENTERPRISE SECURITY</span>
            </div>
            <h2>Built with Zero-Trust Isolation & AES-256 Encryption</h2>
            <p>
              All external credentials—including SMTP passwords, IMAP tokens, and LinkedIn session cookies—are encrypted using Fernet (AES-256) before reaching disk.
            </p>
            <ul className="security-list">
              <li><CheckCircle2 size={16} color="var(--primary)" /> <span>JWT authentication required on every API endpoint</span></li>
              <li><CheckCircle2 size={16} color="var(--primary)" /> <span>Row-level user isolation preventing cross-account leaks</span></li>
              <li><CheckCircle2 size={16} color="var(--primary)" /> <span>Anti-spam hook duplication guard for consecutive sends</span></li>
              <li><CheckCircle2 size={16} color="var(--primary)" /> <span>XOAUTH2 token automatic expiry refresh cycles</span></li>
            </ul>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-container">
          <div className="footer-brand">
            <div className="landing-logo">
              <div className="landing-logo-icon">
                <Mail size={18} />
              </div>
              <span className="brand-name">AutoMail</span>
            </div>
            <p className="footer-copy">
              Precision Cold Email Automation Engine • Premium Utility Architecture
            </p>
          </div>
          <div className="footer-status mono">
            <span className="status-dot"></span>
            <span>ALL SYSTEMS NOMINAL</span>
          </div>
        </div>
      </footer>
      {showGoogleWarning && (
        <div className="modal-overlay" style={{ zIndex: 1100 }}>
          <div className="modal-content" style={{ maxWidth: '450px', padding: '24px', textAlign: 'center' }}>
            <div style={{ fontSize: '32px', marginBottom: '12px' }}>⚠️</div>
            <h3 style={{ marginBottom: '12px', fontSize: '18px', fontWeight: 600 }}>Google Login Verification Pending</h3>
            <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)', lineHeight: '1.6', marginBottom: '16px' }}>
              AutoMail's Google OAuth App is currently undergoing verification. Access is restricted to pre-approved/whitelisted email accounts (up to 100 users).
            </p>

            {/* Request Whitelisting Form */}
            <div style={{ background: 'var(--surface-container-low)', padding: '16px', borderRadius: '8px', marginBottom: '20px', textAlign: 'left' }}>
              <label className="form-label" style={{ marginBottom: '6px', fontSize: '12px' }}>Request Access (Enter your Email)</label>
              <input
                type="email"
                className="form-input"
                style={{ width: '100%', marginBottom: '12px', fontSize: '13px' }}
                placeholder="yourname@gmail.com"
                value={requestEmail}
                onChange={(e) => setRequestEmail(e.target.value)}
              />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <a
                  href={requestEmail ? `https://wa.me/8809691824?text=Please%20whitelist%20my%20email%20address%3A%20${encodeURIComponent(requestEmail)}` : '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary btn-sm"
                  style={{ 
                    justifyContent: 'center', 
                    fontSize: '11px', 
                    pointerEvents: requestEmail ? 'auto' : 'none', 
                    opacity: requestEmail ? 1 : 0.6 
                  }}
                  onClick={(e) => {
                    if (!requestEmail) e.preventDefault();
                  }}
                >
                  💬 Request via WhatsApp
                </a>
                <a
                  href={requestEmail ? `mailto:adityacodes404@gmail.com?subject=AutoMail%20Whitelist%20Request&body=Please%20whitelist%20my%20email%3A%20${encodeURIComponent(requestEmail)}` : '#'}
                  className="btn btn-secondary btn-sm"
                  style={{ 
                    justifyContent: 'center', 
                    fontSize: '11px', 
                    pointerEvents: requestEmail ? 'auto' : 'none', 
                    opacity: requestEmail ? 1 : 0.6 
                  }}
                  onClick={(e) => {
                    if (!requestEmail) e.preventDefault();
                  }}
                >
                  ✉️ Request via Email
                </a>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowGoogleWarning(false)}>
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => {
                  if (googleUrl) window.location.href = googleUrl;
                }}
              >
                Proceed to Google
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
