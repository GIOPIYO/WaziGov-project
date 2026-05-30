import React from 'react';
import { Sliders, List, Search } from 'lucide-react';

export default function Projects() {
  return (
    <div>
      <h1 className="page-title">Projects Directory</h1>
      
      <div className="grid-container">
        {/* -- Left Sidebar: Filters -- */}
        <aside className="sidebar-left">
          <div className="filter-section">
            <h3 className="filter-title">
              <Sliders size={16} />
              <span>Filters</span>
            </h3>
            <div className="filter-group">
              <label htmlFor="search">Search</label>
              <div className="input-with-icon">
                <Search size={16} />
                <input type="text" id="search" placeholder="Project name, keyword..." />
              </div>
            </div>
            <div className="filter-group">
              <label htmlFor="county">County</label>
              <select id="county">
                <option value="">All Counties</option>
                {/* Populate with counties */}
              </select>
            </div>
            <div className="filter-group">
              <label htmlFor="sector">Sector</label>
              <select id="sector">
                <option value="">All Sectors</option>
                {/* Populate with sectors */}
              </select>
            </div>
            <div className="filter-group">
              <label htmlFor="status">Status</label>
              <select id="status">
                <option value="">All Statuses</option>
                {/* Populate with statuses */}
              </select>
            </div>
          </div>
        </aside>

        {/* -- Main Content: Project List -- */}
        <main className="main-content">
          <div className="list-header">
            <h2 className="list-title">
              <List size={20} />
              <span>All Projects</span>
            </h2>
            <div className="list-summary">
              <p>Showing 1-10 of 150 projects</p>
            </div>
          </div>
          <div className="project-list">
            {/* Placeholder for project items */}
            {[...Array(5)].map((_, i) => (
              <div key={i} className="project-item-placeholder" />
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
