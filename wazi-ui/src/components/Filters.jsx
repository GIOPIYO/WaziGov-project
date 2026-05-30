import React from 'react';
import { Search, Filter, RotateCcw } from 'lucide-react';

export default function Filters({
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
  onReset
}) {
  const sectors = ["Infrastructure", "Health", "Water & Sanitation", "Education", "Agriculture"];
  const counties = ["Nairobi", "Mombasa", "Kisumu", "Turkana", "Kiambu"];
  const opinions = [
    { label: "Clean / Unqualified", value: "Clean" },
    { label: "Qualified", value: "Qualified" },
    { label: "Adverse / Alarm", value: "Adverse" },
    { label: "Disclaimer", value: "Disclaimer" }
  ];
  const statuses = ["Complete", "In Progress", "Suspended", "Planning"];

  return (
    <div className="glass-panel" style={styles.container}>
      <div style={styles.searchRow}>
        <div style={styles.searchContainer}>
          <Search size={18} style={styles.searchIcon} />
          <input
            type="text"
            className="glass-input"
            style={styles.searchInput}
            placeholder="Search projects by name, agency, or ward..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <button className="btn-secondary" style={styles.resetBtn} onClick={onReset}>
          <RotateCcw size={15} />
          Reset Filters
        </button>
      </div>

      <div style={styles.filterGrid}>
        {/* County Filter */}
        <div style={styles.filterGroup}>
          <label style={styles.label}>County Region</label>
          <select
            className="glass-input"
            style={styles.select}
            value={selectedCounty}
            onChange={(e) => setSelectedCounty(e.target.value)}
          >
            <option value="">All 47 Counties</option>
            {counties.map((c) => (
              <option key={c} value={c}>{c} County</option>
            ))}
          </select>
        </div>

        {/* Sector Filter */}
        <div style={styles.filterGroup}>
          <label style={styles.label}>Development Sector</label>
          <select
            className="glass-input"
            style={styles.select}
            value={selectedSector}
            onChange={(e) => setSelectedSector(e.target.value)}
          >
            <option value="">All Sectors</option>
            {sectors.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        {/* Audit Opinion Filter */}
        <div style={styles.filterGroup}>
          <label style={styles.label}>OAG Audit Opinion</label>
          <select
            className="glass-input"
            style={styles.select}
            value={selectedOpinion}
            onChange={(e) => setSelectedOpinion(e.target.value)}
          >
            <option value="">All Audit Ratings</option>
            {opinions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Status Filter */}
        <div style={styles.filterGroup}>
          <label style={styles.label}>Project Status</label>
          <select
            className="glass-input"
            style={styles.select}
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
          >
            <option value="">All Statuses</option>
            {statuses.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    padding: '18px 22px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    width: '100%',
  },
  searchRow: {
    display: 'flex',
    gap: '12px',
    width: '100%',
    flexWrap: 'wrap',
  },
  searchContainer: {
    position: 'relative',
    flex: 1,
    minWidth: '280px',
  },
  searchIcon: {
    position: 'absolute',
    left: '14px',
    top: '50%',
    transform: 'translateY(-50%)',
    color: 'var(--text-muted)',
  },
  searchInput: {
    width: '100%',
    paddingLeft: '44px',
    fontSize: '0.9rem',
    borderRadius: '10px',
  },
  resetBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 18px',
    fontSize: '0.85rem',
  },
  filterGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '16px',
    width: '100%',
  },
  filterGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '0.75rem',
    fontWeight: '600',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  },
  select: {
    width: '100%',
    fontSize: '0.85rem',
    borderRadius: '8px',
    cursor: 'pointer',
    backgroundImage: `url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 12px center',
    backgroundSize: '16px',
    appearance: 'none',
    paddingRight: '36px',
  }
};
