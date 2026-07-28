import React, { useState } from 'react';
import { api, setToken } from '../api';
import { Mail, Lock, LogIn, UserPlus, Globe } from 'lucide-react';

interface AuthModalProps {
  onSuccess: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ onSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
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

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '420px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{
            width: '48px', height: '48px', borderRadius: '8px',
            backgroundColor: 'var(--on-primary-container)', color: 'var(--primary)',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: '12px'
          }}>
            <Mail size={24} />
          </div>
          <h2>AutoMail Cold Engine</h2>
          <p className="page-subtitle">
            {isLogin ? 'Sign in to access your cold outreach dashboard' : 'Create your isolated user account'}
          </p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {/* Official Google OAuth2 Redirect Button */}
        <button
          type="button"
          onClick={handleGoogleOAuthConnect}
          className="btn btn-secondary"
          style={{ width: '100%', padding: '10px', marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}
        >
          <Globe size={18} color="#4285F4" />
          <span>Connect with Google (Official OAuth2)</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', margin: '16px 0' }}>
          <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
          <span style={{ fontSize: '12px', color: 'var(--outline)' }}>OR EMAIL</span>
          <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <div style={{ position: 'relative' }}>
              <input
                type="email"
                className="form-input"
                style={{ width: '100%', paddingLeft: '36px' }}
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <Mail size={16} style={{ position: 'absolute', left: '12px', top: '10px', color: 'var(--outline)' }} />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: '24px' }}>
            <label className="form-label">Password</label>
            <div style={{ position: 'relative' }}>
              <input
                type="password"
                className="form-input"
                style={{ width: '100%', paddingLeft: '36px' }}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <Lock size={16} style={{ position: 'absolute', left: '12px', top: '10px', color: 'var(--outline)' }} />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '10px' }}
            disabled={loading}
          >
            {loading ? 'Processing...' : isLogin ? (
              <><LogIn size={16} /> Sign In</>
            ) : (
              <><UserPlus size={16} /> Create Account</>
            )}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '13px', color: 'var(--on-surface-variant)' }}>
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button
            type="button"
            onClick={() => setIsLogin(!isLogin)}
            style={{ background: 'none', border: 'none', color: 'var(--primary)', fontWeight: 600, cursor: 'pointer' }}
          >
            {isLogin ? 'Sign up' : 'Log in'}
          </button>
        </div>

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
    </div>
  );
};
