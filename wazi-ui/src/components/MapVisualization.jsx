import React, { useState } from 'react';
import { Map, MapPin, Info } from 'lucide-react';

export default function MapVisualization({ activeCounty, onSelectCounty, projects }) {
  const [hoveredCounty, setHoveredCounty] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const getCountyStats = (countyName) => {
    const countyProjects = projects.filter(p => p.county.toLowerCase() === countyName.toLowerCase());
    const totalBudget = countyProjects.reduce((acc, p) => acc + p.budget, 0);
    const queryCount = countyProjects.filter(p => p.oagOpinion === 'Adverse' || p.oagOpinion === 'Disclaimer').length;
    const queryRate = countyProjects.length ? Math.round((queryCount / countyProjects.length) * 100) : 0;
    
    return {
      count: countyProjects.length,
      budget: totalBudget,
      queryRate,
      name: countyName
    };
  };

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltipPos({
      x: e.clientX - rect.left + 15,
      y: e.clientY - rect.top + 15
    });
  };

  const formatBudget = (val) => {
    if (val >= 1e9) return `KES ${(val / 1e9).toFixed(2)} Billion`;
    if (val >= 1e6) return `KES ${(val / 1e6).toFixed(1)} Million`;
    return `KES ${val.toLocaleString()}`;
  };

  // A simple list of county names for the new map
  const countyNames = [
    'Mombasa', 'Kwale', 'Kilifi', 'Tana River', 'Lamu', 'Taita-Taveta', 'Garissa', 'Wajir', 
    'Mandera', 'Marsabit', 'Isiolo', 'Meru', 'Tharaka-Nithi', 'Embu', 'Kitui', 'Machakos', 
    'Makueni', 'Nyandarua', 'Nyeri', 'Kirinyaga', 'Muranga', 'Kiambu', 'Turkana', 'West Pokot', 
    'Samburu', 'Trans Nzoia', 'Uasin Gishu', 'Elgeyo-Marakwet', 'Nandi', 'Baringo', 'Laikipia', 
    'Nakuru', 'Narok', 'Kajiado', 'Kericho', 'Bomet', 'Kakamega', 'Vihiga', 'Bungoma', 'Busia', 
    'Siaya', 'Kisumu', 'Homa Bay', 'Migori', 'Kisii', 'Nyamira', 'Nairobi'
  ];

  return (
    <div className="material-card" style={styles.container}>
      <div style={styles.header}>
        <div style={styles.headerTitle}>
          <Map size={18} style={{ color: 'var(--accent-secondary)' }} />
          <span style={styles.titleText}>Geospatial Accountability View</span>
        </div>
        <div style={styles.legend}>
          <div style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: 'var(--color-clean)' }} />
            <span>Clean</span>
          </div>
          <div style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: 'var(--color-qualified)' }} />
            <span>Moderate Flags</span>
          </div>
          <div style={styles.legendItem}>
            <span style={{ ...styles.legendDot, background: 'var(--color-adverse)' }} />
            <span>Critical Queries</span>
          </div>
        </div>
      </div>

      <div style={styles.mapLayout} onMouseMove={handleMouseMove}>
        <img src="/kenya-map.svg" alt="Map of Kenya" 
          style={{ width: '100%', height: '100%', objectFit: 'contain' }} 
        />

        {/* Tooltip card */}
        {hoveredCounty && (
          <div 
            style={{ 
              ...styles.tooltip, 
              left: `${tooltipPos.x}px`, 
              top: `${tooltipPos.y}px` 
            }}
          >
            <div style={styles.tooltipHeader}>
              <MapPin size={13} />
              <span style={styles.tooltipTitle}>{hoveredCounty.name}</span>
            </div>
            <div style={styles.tooltipBody}>
              <div style={styles.tooltipRow}>
                <span style={styles.tooltipLabel}>Projects:</span>
                <span style={styles.tooltipVal}>{hoveredCounty.count} active</span>
              </div>
              <div style={styles.tooltipRow}>
                <span style={styles.tooltipLabel}>Total Tracked:</span>
                <span style={{ ...styles.tooltipVal, color: 'var(--accent-blue)' }}>
                  {formatBudget(hoveredCounty.budget)}
                </span>
              </div>
              <div style={styles.tooltipRow}>
                <span style={styles.tooltipLabel}>Audit Flags:</span>
                <span style={{ 
                  ...styles.tooltipVal, 
                  color: hoveredCounty.queryRate > 40 ? 'var(--color-adverse)' : hoveredCounty.queryRate > 0 ? 'var(--color-qualified)' : 'var(--color-clean)' 
                }}>
                  {hoveredCounty.queryRate}% Rate
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
      <div style={styles.footerNote}>
        Linked to OAG (Office of the Auditor General) Database for Kenya.
      </div>
    </div>
  );
}

const styles = {
  container: {
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    minHeight: '380px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '12px',
    borderBottom: '1px solid var(--border-light)',
    paddingBottom: '12px',
  },
  headerTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  titleText: {
    fontFamily: 'var(--font-display)',
    fontWeight: '700',
    fontSize: '0.95rem',
    color: 'var(--text-title)',
    letterSpacing: '0.01em',
  },
  legend: {
    display: 'flex',
    gap: '10px',
    fontSize: '0.7rem',
    color: 'var(--text-secondary)',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  legendDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    display: 'inline-block',
  },
  mapLayout: {
    position: 'relative',
    flex: 1,
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    background: 'rgba(240, 242, 245, 0.5)',
    borderRadius: '10px',
    border: '1px solid var(--border-light)',
    overflow: 'hidden',
  },
  tooltip: {
    position: 'absolute',
    background: '#ffffff',
    border: '1px solid rgba(0, 0, 0, 0.08)',
    borderRadius: '10px',
    padding: '12px',
    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.12)',
    width: '210px',
    zIndex: 50,
    pointerEvents: 'none',
  },
  tooltipHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    borderBottom: '1px solid var(--border-light)',
    paddingBottom: '6px',
    marginBottom: '6px',
  },
  tooltipTitle: {
    fontFamily: 'var(--font-display)',
    fontWeight: '700',
    fontSize: '0.85rem',
    color: 'var(--text-title)',
  },
  tooltipBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  tooltipRow: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.72rem',
  },
  tooltipLabel: {
    color: 'var(--text-secondary)',
  },
  tooltipVal: {
    fontWeight: '600',
    color: 'var(--text-main)',
  },
  footerNote: {
    fontSize: '0.7rem',
    color: 'var(--text-secondary)',
    textAlign: 'center',
    fontStyle: 'italic',
  }
};