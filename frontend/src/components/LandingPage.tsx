import React, { useState, useEffect } from 'react';
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
  Database
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
  const [showGoogleWarning, setShowGoogleWarning] = useState(false);
  const [requestEmail, setRequestEmail] = useState('');
  const [googleUrl, setGoogleUrl] = useState('');

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

  const scrollToAuth = () => {
    const authElem = document.getElementById('auth-section');
    if (authElem) {
      authElem.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    // Pre-fetch the Google OAuth URL so the warning modal can redirect immediately
    fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/auth/google/url`)
      .then((r) => r.json())
      .then((data) => { if (data.url) setGoogleUrl(data.url); })
      .catch(() => {});
  }, []);

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
              <span className="brand-name">GetNewJob AI</span>
              <span className="brand-badge mono">JOB OUTREACH v2.4</span>
            </div>
          </div>

          <nav className="landing-nav-links">
            <a href="#features">Features</a>
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
          <span>AI ACTIVE • SMART JOB OUTREACH ENGINE</span>
        </div>

        <h1 className="hero-headline">
          Land Your Next Job Faster with AI-Powered Outreach
        </h1>

        <p className="hero-subline">
          Automate personalized cold emails to recruiters and hiring managers using your resume as context.
          Human-paced delivery, AES-256 encryption, and zero-spam throttling — all in your private workspace.
        </p>

        <div className="hero-cta-group">
          <button onClick={() => { setIsLogin(false); scrollToAuth(); }} className="btn btn-primary hero-btn">
            <span>Launch Workspace</span>
            <ArrowRight size={16} />
          </button>
        </div>

        {/* Spec Pill Bar */}
        <div className="hero-spec-grid">
          <div className="hero-spec-item">
            <span className="spec-val mono">AI</span>
            <span className="spec-label">Resume-Driven Context</span>
          </div>
          <div className="hero-spec-divider"></div>
          <div className="hero-spec-item">
            <span className="spec-val mono">2-3/hr</span>
            <span className="spec-label">Human-Paced Sending</span>
          </div>
          <div className="hero-spec-divider"></div>
          <div className="hero-spec-item">
            <span className="spec-val mono">SMTP</span>
            <span className="spec-label">Secure Delivery</span>
          </div>
          <div className="hero-spec-divider"></div>
          <div className="hero-spec-item">
            <span className="spec-val mono">100%</span>
            <span className="spec-label">Private & Isolated</span>
          </div>
        </div>
      </section>

      {/* Centered Auth Card Container */}
      <section id="auth-section" style={{ display: 'flex', justifyContent: 'center', margin: '32px auto 80px auto', padding: '0 24px' }}>
        <div className="auth-card-container card" style={{ maxWidth: '420px', width: '100%' }}>
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
                : 'Get started with isolated context tables & outreach queues.'}
            </p>
          </div>

          {error && <div className="alert alert-error">{error}</div>}

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
            <span>Encrypted with AES-256 at rest. Private tenant isolation.</span>
          </div>

          <div style={{ margin: '16px 0 4px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ flex: 1, height: '1px', background: 'var(--outline-variant)' }} />
            <span style={{ fontSize: '12px', color: 'var(--on-surface-variant)' }}>or</span>
            <div style={{ flex: 1, height: '1px', background: 'var(--outline-variant)' }} />
          </div>

          <button
            type="button"
            className="btn btn-secondary auth-submit-btn"
            style={{ marginTop: '12px', gap: '8px' }}
            onClick={() => setShowGoogleWarning(true)}
          >
            <Globe size={16} color="#4285F4" />
            Continue with Google
          </button>
        </div>
      </section>

      {/* Features Grid Section */}
      <section id="features" className="landing-features-section">
        <div className="section-header">
          <span className="chip chip-new mono">CORE CAPABILITIES</span>
          <h2>Designed for Reliable, Zero-Slop Outreach</h2>
          <p className="section-subtitle">
            Every component is built around maximum reliability, strict pacing, and deep context matching.
          </p>
        </div>

        <div className="features-grid">
          <div className="feature-card card">
            <div className="feature-icon">
              <Cpu size={24} color="var(--primary)" />
            </div>
            <h3>Context Matching Engine</h3>
            <p>
              LLM automatically aligns your profile highlights, experiences, and projects with target roles for high-relevance outreach.
            </p>
          </div>

          <div className="feature-card card">
            <div className="feature-icon">
              <Globe size={24} color="var(--primary)" />
            </div>
            <h3>Lead Discovery Hub</h3>
            <p>
              Organize target contacts and look up verified email details based on company domain and recipient parameters.
            </p>
          </div>

          <div className="feature-card card">
            <div className="feature-icon">
              <Zap size={24} color="var(--primary)" />
            </div>
            <h3>Autonomous Send Queue & Pacing</h3>
            <p>
              Protect domain reputation with strict sending rate-limiting (2-3 sends/hour) and custom daily schedule windows.
            </p>
          </div>

          <div className="feature-card card">
            <div className="feature-icon">
              <Database size={24} color="var(--primary)" />
            </div>
            <h3>IMAP Reply & Bounce Tracker</h3>
            <p>
              Keep track of replies or delivery reports via standard IMAP integrations, letting you auto-pause queues instantly.
            </p>
          </div>

          <div className="feature-card card">
            <div className="feature-icon">
              <Shield size={24} color="var(--primary)" />
            </div>
            <h3>Private Data Sandbox</h3>
            <p>
              Complete data isolation per user. SMTP details, resume credentials, contacts, and logs remain strictly private and encrypted.
            </p>
          </div>
        </div>
      </section>

      {/* Security */}
      <section id="security" className="landing-security-section">
        <div className="security-card card">
          <div className="security-content">
            <div className="security-badge mono">
              <Shield size={16} />
              <span>DATA PRIVACY</span>
            </div>
            <h2>Built with Isolation & AES-256 Encryption</h2>
            <p>
              All external credentials—including SMTP passwords, IMAP tokens, and settings—are encrypted using Fernet (AES-256) before reaching disk.
            </p>
            <ul className="security-list">
              <li><CheckCircle2 size={16} color="var(--primary)" /> <span>JWT authentication required on every API endpoint</span></li>
              <li><CheckCircle2 size={16} color="var(--primary)" /> <span>Row-level user isolation preventing cross-account leaks</span></li>
              <li><CheckCircle2 size={16} color="var(--primary)" /> <span>Pacing limits and outreach safety checks</span></li>
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
              <span className="brand-name">GetNewJob AI</span>
            </div>
            <p className="footer-copy">
              AI-Powered Job Outreach Engine
            </p>
          </div>
          <div className="footer-status mono">
            <span className="status-dot"></span>
            <span>ALL SYSTEMS NOMINAL</span>
          </div>
        </div>
      </footer>

      {/* Google Verification Warning Modal */}
      {showGoogleWarning && (
        <div className="modal-overlay" style={{ zIndex: 1100 }}>
          <div className="modal-content" style={{ maxWidth: '450px', padding: '24px', textAlign: 'center' }}>
            <div style={{ fontSize: '32px', marginBottom: '12px' }}>⚠️</div>
            <h3 style={{ marginBottom: '12px', fontSize: '18px', fontWeight: 600 }}>Google Login Verification Pending</h3>
            <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)', lineHeight: '1.6', marginBottom: '16px' }}>
              GetNewJob AI's Google OAuth App is currently undergoing verification. Access is restricted to pre-approved/whitelisted email accounts (up to 100 users).
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
                  onClick={(e) => { if (!requestEmail) e.preventDefault(); }}
                >
                  💬 Request via WhatsApp
                </a>
                <a
                  href={requestEmail ? `https://mail.google.com/mail/?view=cm&fs=1&to=adityacodes404@gmail.com&su=GetNewJob%20AI%20Whitelist%20Request&body=Please%20whitelist%20my%20email%3A%20${encodeURIComponent(requestEmail)}` : '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary btn-sm"
                  style={{
                    justifyContent: 'center',
                    fontSize: '11px',
                    pointerEvents: requestEmail ? 'auto' : 'none',
                    opacity: requestEmail ? 1 : 0.6
                  }}
                  onClick={(e) => { if (!requestEmail) e.preventDefault(); }}
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
                onClick={() => { if (googleUrl) window.location.href = googleUrl; }}
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
