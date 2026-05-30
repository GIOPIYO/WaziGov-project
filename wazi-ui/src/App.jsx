import React, { useState } from 'react';
import { ShieldCheck, Database, FileSpreadsheet } from 'lucide-react';
import { mockProjects } from './data/mockProjects';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import Reports from './pages/Reports';
import Settings from './pages/Settings';

export default function App() {
  const [projects, setProjects] = useState(mockProjects);
  
  // Filtering States
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCounty, setSelectedCounty] = useState('');
  const [selectedSector, setSelectedSector] = useState('');
  const [selectedOpinion, setSelectedOpinion] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  
  // Selected project for modal deep-dive
  const [selectedProject, setSelectedProject] = useState(null);
  const [activeSection, setActiveSection] = useState('dashboard');

  // Reset all filters
  const handleResetFilters = () => {
    setSearchQuery('');
    setSelectedCounty('');
    setSelectedSector('');
    setSelectedOpinion('');
    setSelectedStatus('');
  };

  // Add a new citizen report to a specific project dynamically
  const handleAddCitizenReport = (projectId, newReport) => {
    setProjects(prevProjects => {
      const updated = prevProjects.map(p => {
        if (p.id === projectId) {
          const updatedReports = [newReport, ...p.citizenReports];
          return {
            ...p,
            citizenReports: updatedReports
          };
        }
        return p;
      });

      const matched = updated.find(p => p.id === projectId);
      if (matched && selectedProject && selectedProject.id === projectId) {
        setSelectedProject(matched);
      }

      return updated;
    });
  };

  // Filter project database dynamically
  const filteredProjects = projects.filter(p => {
    const matchesSearch = 
      p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.implementationAgency.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.ward.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCounty = selectedCounty === '' || p.county.toLowerCase() === selectedCounty.toLowerCase();
    const matchesSector = selectedSector === '' || p.sector.toLowerCase() === selectedSector.toLowerCase();
    const matchesOpinion = selectedOpinion === '' || p.oagOpinion.toLowerCase() === selectedOpinion.toLowerCase();
    const matchesStatus = selectedStatus === '' || p.status.toLowerCase() === selectedStatus.toLowerCase();

    return matchesSearch && matchesCounty && matchesSector && matchesOpinion && matchesStatus;
  });

  const renderSection = () => {
    switch (activeSection) {
      case 'dashboard':
        return <Dashboard 
          projects={projects}
          filteredProjects={filteredProjects}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          selectedCounty={selectedCounty}
          setSelectedCounty={setSelectedCounty}
          selectedSector={selectedSector}
          setSelectedSector={setSelectedSector}
          selectedOpinion={selectedOpinion}
          setSelectedOpinion={setSelectedOpinion}
          selectedStatus={selectedStatus}
          setSelectedStatus={setSelectedStatus}
          handleResetFilters={handleResetFilters}
          selectedProject={selectedProject}
          setSelectedProject={setSelectedProject}
          handleAddCitizenReport={handleAddCitizenReport}
        />;
      case 'projects':
        return <Projects />;
      case 'reports':
        return <Reports />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard 
          projects={projects}
          filteredProjects={filteredProjects}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          selectedCounty={selectedCounty}
          setSelectedCounty={setSelectedCounty}
          selectedSector={selectedSector}
          setSelectedSector={setSelectedSector}
          selectedOpinion={selectedOpinion}
          setSelectedOpinion={setSelectedOpinion}
          selectedStatus={selectedStatus}
          setSelectedStatus={setSelectedStatus}
          handleResetFilters={handleResetFilters}
          selectedProject={selectedProject}
          setSelectedProject={setSelectedProject}
          handleAddCitizenReport={handleAddCitizenReport}
        />;
    }
  };

  return (
    <div className="dashboard-container">
      <Sidebar activeSection={activeSection} onSelect={setActiveSection} />

      <div className="material-main-panel">
        {/* Top Bar */}
        <header className="topbar">
          <div className="topbar-left">
            <div className="topbar-icon">
              <ShieldCheck size={22} />
            </div>
            <div>
              <h1 className="topbar-brand-title">WaziGov</h1>
              <p className="topbar-brand-sub">Public Finance Transparency &amp; Accountability</p>
            </div>
          </div>

          <div className="topbar-right">
            <div className="status-pill">
              <span className="status-dot" />
              <Database size={13} />
              <span>System Active</span>
            </div>
            <a
              href="/WaziGov Final Proposal (7).pdf"
              target="_blank"
              className="btn-proposal"
            >
              <FileSpreadsheet size={14} />
              View Proposal
            </a>
          </div>
        </header>

        {renderSection()}

        {/* Footer */}
        <footer className="app-footer">
          <div className="footer-brand">WaziGov Dashboard v1.0.0</div>
          <div className="footer-motto">
            "Transforming Read-Only government data into Read-Write accountability."
          </div>
          <div className="footer-credits">
            Designed for Public Audit Integration by Joseph Kariuki, Daniel Mwangi, Giovanni Opiyo (Group 0147)
          </div>
        </footer>
      </div>
    </div>
  );
}
