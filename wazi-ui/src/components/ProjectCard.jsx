import React from 'react';
import { 
  HeartPulse, 
  Wrench, 
  Droplets, 
  GraduationCap, 
  Sprout, 
  MapPin, 
  Building2, 
  MessageSquare,
  AlertTriangle,
  ChevronRight
} from 'lucide-react';

export default function ProjectCard({ project, onSelect }) {
  const getSectorIcon = (sector) => {
    switch (sector.toLowerCase()) {
      case 'health':
        return <HeartPulse size={16} />;
      case 'infrastructure':
        return <Wrench size={16} />;
      case 'water & sanitation':
        return <Droplets size={16} />;
      case 'education':
        return <GraduationCap size={16} />;
      case 'agriculture':
        return <Sprout size={16} />;
      default:
        return <Building2 size={16} />;
    }
  };

  const getStatusColor = (status) => {
    switch (status.toLowerCase()) {
      case 'complete':
        return { color: 'var(--color-clean)', bg: 'var(--color-clean-glow)', border: 'rgba(46, 125, 50, 0.2)' };
      case 'in progress':
        return { color: 'var(--accent-blue)', bg: 'rgba(26, 115, 232, 0.08)', border: 'rgba(26, 115, 232, 0.15)' };
      case 'suspended':
        return { color: 'var(--color-adverse)', bg: 'var(--color-adverse-glow)', border: 'rgba(211, 47, 47, 0.2)' };
      case 'planning':
      default:
        return { color: 'var(--color-qualified)', bg: 'var(--color-qualified-glow)', border: 'rgba(245, 124, 0, 0.2)' };
    }
  };

  const getOpinionBadgeClass = (op) => {
    switch (op.toLowerCase()) {
      case 'clean':
        return 'badge-clean';
      case 'qualified':
        return 'badge-qualified';
      case 'adverse':
        return 'badge-adverse';
      case 'disclaimer':
        return 'badge-disclaimer';
      default:
        return '';
    }
  };

  const getProgressColor = (status) => {
    if (status.toLowerCase() === 'complete') return 'var(--color-clean)';
    if (status.toLowerCase() === 'suspended') return 'var(--color-adverse)';
    return 'var(--accent-secondary)';
  };

  const formatCurrency = (value) => {
    if (value >= 1.0e9) return `KES ${(value / 1.0e9).toFixed(2)}B`;
    if (value >= 1.0e6) return `KES ${(value / 1.0e6).toFixed(1)}M`;
    return `KES ${value.toLocaleString()}`;
  };

  const statusStyle = getStatusColor(project.status);

  return (
    <div 
      className="material-card" 
      style={{
        ...styles.card,
        borderLeft: project.oagOpinion === 'Adverse' 
          ? '4px solid var(--color-adverse)' 
          : project.oagOpinion === 'Disclaimer'
            ? '4px solid var(--color-disclaimer)'
            : '1px solid var(--border-light)'
      }}
      onClick={() => onSelect(project)}
    >
      <div style={styles.cardHeader}>
        <div style={styles.sectorBadge}>
          {getSectorIcon(project.sector)}
          <span>{project.sector}</span>
        </div>
        <span 
          className="badge" 
          style={{
            color: statusStyle.color,
            background: statusStyle.bg,
            borderColor: statusStyle.border,
          }}
        >
          {project.status}
        </span>
      </div>

      <h3 style={styles.title}>{project.title}</h3>

      <div style={styles.location}>
        <MapPin size={12} style={{ color: 'var(--text-secondary)', marginRight: '4px' }} />
        <span>{project.county} County · {project.ward} Ward</span>
      </div>

      <div style={styles.agency}>
        <Building2 size={12} style={{ color: 'var(--text-secondary)', marginRight: '4px' }} />
        <span>{project.implementationAgency}</span>
      </div>

      <div style={styles.ledgerRow}>
        <div style={styles.ledgerCol}>
          <span style={styles.ledgerLabel}>Budgeted</span>
          <span style={styles.ledgerVal}>{formatCurrency(project.budget)}</span>
        </div>
        <div style={styles.ledgerCol}>
          <span style={styles.ledgerLabel}>Spent</span>
          <span style={{ 
            ...styles.ledgerVal, 
            color: project.spent > project.budget ? 'var(--color-adverse)' : 'var(--text-title)' 
          }}>
            {formatCurrency(project.spent)}
          </span>
        </div>
      </div>

      <div style={styles.progressRow}>
        <div style={styles.progressLabels}>
          <span style={styles.progressLabel}>Completion Progress</span>
          <span style={styles.progressVal}>{project.progress}%</span>
        </div>
        <div className="progress-bar-container">
          <div 
            className="progress-bar-fill"
            style={{ 
              width: `${project.progress}%`,
              background: getProgressColor(project.status)
            }}
          />
        </div>
      </div>

      <div style={styles.footerRow}>
        <div style={styles.auditBlock}>
          <span style={styles.footerLabel}>OAG Opinion</span>
          <span className={`badge ${getOpinionBadgeClass(project.oagOpinion)}`} style={{ fontSize: '0.65rem', padding: '2px 8px' }}>
            {project.oagOpinion}
          </span>
        </div>

        <div style={styles.citizenBlock}>
          {project.citizenReports.length > 0 && (
            <div style={styles.feedBadge}>
              <MessageSquare size={12} style={{ color: 'var(--accent-secondary)' }} />
              <span>{project.citizenReports.length} Ground Reports</span>
            </div>
          )}
          {project.spent > project.budget && (
            <div style={{ ...styles.feedBadge, color: 'var(--color-adverse)' }}>
              <AlertTriangle size={12} />
              <span>Overspent</span>
            </div>
          )}
        </div>
      </div>

      <div style={styles.actionPrompt}>
        <span>Inspect Financials & Audits</span>
        <ChevronRight size={13} />
      </div>
    </div>
  );
}

const styles = {
  card: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    cursor: 'pointer',
    textAlign: 'left',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectorBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '0.72rem',
    color: 'var(--ke-green)',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  },
  title: {
    fontFamily: 'var(--font-display)',
    fontWeight: '700',
    fontSize: '1rem',
    color: 'var(--text-title)',
    lineHeight: '1.4',
    minHeight: '44px',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  location: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '0.78rem',
    color: 'var(--text-secondary)',
  },
  agency: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '0.75rem',
    color: 'var(--text-secondary)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  ledgerRow: {
    display: 'flex',
    gap: '12px',
    background: 'var(--bg-main)',
    border: '1px solid var(--border-light)',
    borderRadius: '8px',
    padding: '8px 12px',
    marginTop: '2px',
  },
  ledgerCol: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  ledgerLabel: {
    fontSize: '0.62rem',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.03em',
  },
  ledgerVal: {
    fontFamily: 'var(--font-display)',
    fontSize: '0.88rem',
    fontWeight: '700',
  },
  progressRow: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  progressLabels: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.7rem',
  },
  progressLabel: {
    color: 'var(--text-secondary)',
  },
  progressVal: {
    fontWeight: '700',
    color: 'var(--text-title)',
  },
  footerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTop: '1px solid var(--border-light)',
    paddingTop: '10px',
    marginTop: '4px',
  },
  auditBlock: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  footerLabel: {
    fontSize: '0.58rem',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.02em',
  },
  citizenBlock: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: '2px',
  },
  feedBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '0.68rem',
    color: 'var(--text-secondary)',
  },
  actionPrompt: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: '4px',
    fontSize: '0.72rem',
    color: 'var(--accent-primary)',
    fontWeight: '700',
    marginTop: '2px',
    opacity: 0.8,
  }
};
