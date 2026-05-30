import React from 'react';
import { RefreshCw, Layers } from 'lucide-react';
import StatsGrid from '../components/StatsGrid';
import MapVisualization from '../components/MapVisualization';
import Filters from '../components/Filters';
import ProjectCard from '../components/ProjectCard';
import ProjectDetailsModal from '../components/ProjectDetailsModal';

export default function Dashboard({ 
  projects, 
  filteredProjects, 
  searchQuery, 
  setSearchQuery, 
  selectedCounty, 
  setSelectedCounty, 
  selectedSector, 
  setSelectedSector, 
  selectedOpinion, 
  setSelectedOpinion, 
  selectedStatus, 
  setSelectedStatus, 
  handleResetFilters, 
  selectedProject, 
  setSelectedProject, 
  handleAddCitizenReport 
}) {
  return (
    <>
      {/* Stats Cards Row */}
      <section>
        <StatsGrid projects={filteredProjects} />
      </section>

      {/* Main interactive directory workspace */}
      <main style={styles.mainGrid}>

        {/* Left: Filters + Project List */}
        <section style={styles.leftCol}>

          <Filters
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
            onReset={handleResetFilters}
          />

          {/* Results count */}
          <div style={styles.resultsHeader}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={16} style={{ color: 'var(--accent-secondary)' }} />
              <span style={styles.resultsCount}>
                Showing {filteredProjects.length} of {projects.length} Audited Projects
              </span>
            </div>
            {selectedCounty && (
              <span className="badge badge-clean" style={{ textTransform: 'capitalize' }}>
                Filtered: {selectedCounty} County
              </span>
            )}
          </div>

          {filteredProjects.length > 0 ? (
            <div style={styles.projectGrid}>
              {filteredProjects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onSelect={setSelectedProject}
                />
              ))}
            </div>
          ) : (
            <div className="glass-panel" style={styles.emptyState}>
              <RefreshCw size={44} style={styles.emptyIcon} />
              <h3 style={styles.emptyTitle}>No matching audit profiles found</h3>
              <p style={styles.emptyDesc}>Try expanding your filter parameters or search terms to find public projects.</p>
              <button className="btn-primary" style={{ marginTop: '12px' }} onClick={handleResetFilters}>
                Reset Search Directory
              </button>
            </div>
          )}

        </section>

        {/* Right: Interactive Map */}
        <section style={styles.rightCol}>
          <MapVisualization
            activeCounty={selectedCounty}
            onSelectCounty={setSelectedCounty}
            projects={projects}
          />
        </section>

      </main>

      {/* Modal overlay */}
      {selectedProject && (
        <ProjectDetailsModal
          project={selectedProject}
          onClose={() => setSelectedProject(null)}
          onAddCitizenReport={handleAddCitizenReport}
        />
      )}
    </>
  );
}

const styles = {
  mainGrid: {
    display: 'grid',
    gridTemplateColumns: '1.25fr 0.75fr',
    gap: '24px',
    alignItems: 'start',
    width: '100%',
  },
  leftCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  rightCol: {
    position: 'sticky',
    top: '24px',
  },
  resultsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0 4px',
  },
  resultsCount: {
    fontSize: '0.85rem',
    fontWeight: '600',
    color: 'var(--text-secondary)',
  },
  projectGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))',
    gap: '20px',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 40px',
    textAlign: 'center',
  },
  emptyIcon: {
    color: 'var(--text-muted)',
    marginBottom: '16px',
  },
  emptyTitle: {
    fontFamily: 'var(--font-display)',
    fontWeight: '700',
    fontSize: '1.1rem',
    color: 'var(--text-title)',
  },
  emptyDesc: {
    fontSize: '0.82rem',
    color: 'var(--text-secondary)',
    maxWidth: '300px',
    marginTop: '6px',
    lineHeight: '1.4',
  },
};
