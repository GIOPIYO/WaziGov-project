import React from 'react';
import { Home, Layers, FileText, Settings, LogOut } from 'lucide-react';
import ThemeToggle from './ThemeToggle';

export default function Sidebar({ activeSection, onSelect }) {
  const sections = [
    { id: 'dashboard', label: 'Dashboard', icon: <Home size={18} /> },
    { id: 'projects', label: 'Projects', icon: <Layers size={18} /> },
    { id: 'reports', label: 'Reports', icon: <FileText size={18} /> },
    { id: 'settings', label: 'Settings', icon: <Settings size={18} /> },
    { id: 'logout', label: 'Logout', icon: <LogOut size={18} /> }
  ];

  return (
    <aside className="material-sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <Layers size={24} />
        </div>
        <div className="sidebar-title">WaziGov</div>
      </div>
      <div className="sidebar-profile">
        <img src="/kenyan-shield.svg" alt="User" className="profile-avatar" />
        <div>
          <div className="profile-name">Citizen Auditor</div>
          <div className="profile-role">Public Guardian</div>
        </div>
      </div>
      <nav className="sidebar-nav">
        {sections.map((s) => (
          <a
            key={s.id}
            className={`nav-link ${activeSection === s.id ? 'nav-link-active' : ''}`}
            href="#"
            onClick={(e) => { e.preventDefault(); onSelect(s.id); }}
          >
            {s.icon}
            <span>{s.label}</span>
          </a>
        ))}
      </nav>

      <div style={{ marginTop: 'auto' }}>
        <ThemeToggle />
      </div>
    </aside>
  );
}
