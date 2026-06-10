import React from 'react';
import { User, Bell, Database } from 'lucide-react';

export default function Settings() {
  return (
    <div>
      <h1 className="page-title">Settings</h1>

      {/* -- Profile Settings -- */}
      <div className="settings-section">
        <h2 className="settings-title">
          <User size={20} />
          <span>Profile Settings</span>
        </h2>
        <div className="settings-group">
          <label htmlFor="username">Username</label>
          <input type="text" id="username" defaultValue="citizen_auditor" />
        </div>
        <div className="settings-group">
          <label htmlFor="email">Email Address</label>
          <input type="email" id="email" defaultValue="auditor@example.com" />
        </div>
      </div>

      {/* -- Notification Settings -- */}
      <div className="settings-section">
        <h2 className="settings-title">
          <Bell size={20} />
          <span>Notification Preferences</span>
        </h2>
        <div className="settings-group">
          <label>
            <input type="checkbox" defaultChecked />
            <span>Email me when new projects are added in my county.</span>
          </label>
        </div>
        <div className="settings-group">
          <label>
            <input type="checkbox" />
            <span>Notify me about critical audit findings.</span>
          </label>
        </div>
      </div>

      {/* -- Data Management -- */}
      <div className="settings-section">
        <h2 className="settings-title">
          <Database size={20} />
          <span>Data Management</span>
        </h2>
        <div className="settings-group">
          <button className="btn-secondary">Export My Data</button>
          <button className="btn-danger">Delete My Account</button>
        </div>
      </div>
    </div>
  );
}
