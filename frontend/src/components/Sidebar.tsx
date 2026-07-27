import React from 'react';
import { LayoutDashboard, FileText, Search, Users, FileCode, Settings, LogOut, Zap } from 'lucide-react';
import { removeToken } from '../api';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  userEmail?: string;
  sendMode?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, userEmail, sendMode }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'resume', label: 'Resume & Context', icon: FileText },
    { id: 'scrapers', label: 'Scraper Hub', icon: Search },
    { id: 'contacts', label: 'Contacts & Queue', icon: Users },
    { id: 'templates', label: 'Email Templates', icon: FileCode },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  const handleSignOut = () => {
    removeToken();
    window.location.reload();
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <Zap size={22} color="var(--primary)" />
        <h2>AutoMail</h2>
      </div>

      <nav className="nav-group">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="user-status">
        <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--outline)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Mode: <span style={{ color: 'var(--primary)', textTransform: 'none' }}>{sendMode || 'review'}</span>
        </div>
        <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--on-surface)', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {userEmail || 'Active User'}
        </div>
        <button
          onClick={handleSignOut}
          className="btn btn-secondary btn-sm"
          style={{ width: '100%', marginTop: '10px', justifyContent: 'center' }}
        >
          <LogOut size={14} /> Sign Out
        </button>
      </div>
    </aside>
  );
};
