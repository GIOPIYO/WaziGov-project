import { useEffect, useState } from 'react';
import { Maximize2, Minimize2, Map, MapPin } from 'lucide-react';
import MapView from './MapView';

export default function MapVisualization({ activeCounty, projects, onSelectCounty }) {
  const projectCount = Array.isArray(projects) ? projects.length : 0;
  const [hoveredFeature, setHoveredFeature] = useState(null);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const displayedFeature = hoveredFeature || selectedFeature;

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = isExpanded ? 'hidden' : previousOverflow;

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isExpanded]);

  const handleFeatureHover = (feature) => {
    setHoveredFeature(feature);
  };

  const handleFeatureClear = () => {
    setHoveredFeature(null);
  };

  const handleFeatureSelect = (feature) => {
    setSelectedFeature(feature);
  };

  const toggleExpanded = () => {
    setIsExpanded((current) => !current);
  };

  return (
    <div className={`material-card ${isExpanded ? 'map-panel-expanded' : ''}`} style={isExpanded ? { ...styles.container, ...styles.expandedContainer } : styles.container}>
      <div style={styles.header}>
        <div style={styles.headerTitle}>
          <Map size={18} style={{ color: 'var(--accent-secondary)' }} />
          <span style={styles.titleText}>Geospatial Accountability View</span>
        </div>
        <div style={styles.headerMeta}>
          <span style={styles.metaPill}>{projectCount} projects</span>
          <span style={styles.metaPill}>{activeCounty || 'All counties'}</span>
          <button type="button" className="btn-primary" style={styles.expandButton} onClick={toggleExpanded}>
            {isExpanded ? <><Minimize2 size={14} /> Shrink map</> : <><Maximize2 size={14} /> Expand map</>}
          </button>
        </div>
      </div>

      <div style={isExpanded ? { ...styles.mapLayout, ...styles.mapLayoutExpanded } : styles.mapLayout}>
        <MapView
          selectedFeatureKey={selectedFeature?.key}
          onFeatureHover={handleFeatureHover}
          onFeatureSelect={handleFeatureSelect}
          onFeatureClear={handleFeatureClear}
          resizeToken={isExpanded ? 'expanded' : 'collapsed'}
        />

        <div style={styles.overlayCard}>
          <div style={styles.overlayTitleRow}>
            <MapPin size={13} />
            <span style={styles.overlayTitle}>
              {displayedFeature ? displayedFeature.label : 'Kenya Geo Layer'}
            </span>
          </div>
          <p style={styles.overlayText}>
            {displayedFeature ? (
              <>
                {displayedFeature.district || 'Boundary'}
                {displayedFeature.province ? ` • ${displayedFeature.province}` : ''}
              </>
            ) : (
              <>
                Interactive boundary map from the <strong>wazi-geoai</strong> module.
              </>
            )}
          </p>
          <div style={styles.overlayHint}>
            Click a boundary to pin it. Hover to preview.
          </div>
        </div>
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
    position: 'relative',
    zIndex: 1,
  },
  expandedContainer: {
    position: 'fixed',
    top: '16px',
    right: '16px',
    bottom: '16px',
    left: 'calc(var(--sidebar-width) + 16px)',
    zIndex: 1200,
    margin: 0,
    minHeight: 'auto',
    boxShadow: '0 24px 70px rgba(0, 0, 0, 0.28)',
    borderRadius: '20px',
    background: 'var(--bg-card)',
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
  headerMeta: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  metaPill: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '5px 10px',
    borderRadius: '999px',
    background: 'rgba(0, 107, 63, 0.08)',
    color: 'var(--text-secondary)',
    fontSize: '0.72rem',
    fontWeight: '600',
  },
  expandButton: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 12px',
    fontSize: '0.76rem',
    whiteSpace: 'nowrap',
  },
  mapLayout: {
    position: 'relative',
    flex: 1,
    minHeight: '440px',
    overflow: 'hidden',
    borderRadius: '14px',
    border: '1px solid var(--border-light)',
    background: '#dbeafe',
  },
  mapLayoutExpanded: {
    minHeight: 'calc(100vh - 220px)',
  },
  overlayCard: {
    position: 'absolute',
    left: '16px',
    top: '16px',
    zIndex: 400,
    maxWidth: '260px',
    padding: '12px 14px',
    borderRadius: '12px',
    background: 'rgba(255, 255, 255, 0.92)',
    border: '1px solid rgba(0, 0, 0, 0.08)',
    boxShadow: '0 14px 30px rgba(0, 0, 0, 0.12)',
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
  },
  overlayTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontFamily: 'var(--font-display)',
    fontWeight: '700',
    fontSize: '0.85rem',
    color: 'var(--text-title)',
    marginBottom: '6px',
  },
  overlayTitle: {
    lineHeight: 1.2,
  },
  overlayText: {
    margin: 0,
    fontSize: '0.78rem',
    color: 'var(--text-secondary)',
    lineHeight: 1.45,
  },
  overlayHint: {
    marginTop: '8px',
    fontSize: '0.68rem',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    fontWeight: '700',
  },
  footerNote: {
    fontSize: '0.7rem',
    color: 'var(--text-secondary)',
    textAlign: 'center',
    fontStyle: 'italic',
    position: 'relative',
    zIndex: 1,
  }
};