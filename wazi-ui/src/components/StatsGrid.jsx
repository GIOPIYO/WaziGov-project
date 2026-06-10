import React from 'react';
import { Percent, ShieldAlert, MessageSquare } from 'lucide-react';

export default function StatsGrid({ projects }) {
  // Calculations based on currently filtered projects
  const totalBudget = projects.reduce((acc, p) => acc + p.budget, 0);
  const totalSpent = projects.reduce((acc, p) => acc + p.spent, 0);
  
  const avgProgress = projects.length 
    ? Math.round(projects.reduce((acc, p) => acc + p.progress, 0) / projects.length) 
    : 0;

  const adverseDisclaimerCount = projects.filter(
    p => p.oagOpinion === 'Adverse' || p.oagOpinion === 'Disclaimer'
  ).length;
  
  const queryPercentage = projects.length 
    ? Math.round((adverseDisclaimerCount / projects.length) * 100) 
    : 0;

  const citizenVerifiedCount = projects.reduce((acc, p) => acc + p.citizenReports.length, 0);

  // Formatter for large KES figures
  const formatCurrency = (value) => {
    if (value >= 1.0e9) return `KES ${(value / 1.0e9).toFixed(2)}B`;
    if (value >= 1.0e6) return `KES ${(value / 1.0e6).toFixed(1)}M`;
    return `KES ${value.toLocaleString()}`;
  };

  const budgetPerformance = totalBudget ? Math.round((totalSpent / totalBudget) * 100) : 0;

  return (
    <div style={styles.grid}>
      
      {/* 1. Tracked Budget Card */}
      <div className="material-card" style={styles.card}>
        <div className="floating-icon-box box-orange">
          <span style={styles.currencyIcon}>KES</span>
        </div>
        <div style={styles.content}>
          <span className="stat-title" style={styles.title}>Tracked Budget</span>
          <div className="stat-value" style={styles.value}>{formatCurrency(totalBudget)}</div>
        </div>
        <div style={styles.footer} className="stat-subtext">
          Spent: {formatCurrency(totalSpent)} ({budgetPerformance}% absorption)
        </div>
      </div>

      {/* 2. Average Progress Card */}
      <div className="material-card" style={styles.card}>
        <div className="floating-icon-box box-green">
          <Percent size={24} />
        </div>
        <div style={styles.content}>
          <span className="stat-title" style={styles.title}>Avg Progress</span>
          <div className="stat-value" style={styles.value}>{avgProgress}%</div>
        </div>
        <div style={styles.footer} className="stat-subtext">
          Across {projects.length} public projects
        </div>
      </div>

      {/* 3. Critical Audit Flags Card */}
      <div className="material-card" style={styles.card}>
        <div className="floating-icon-box box-red">
          <ShieldAlert size={24} />
        </div>
        <div style={styles.content}>
          <span className="stat-title" style={styles.title}>Audit Queries</span>
          <div className="stat-value" style={{ ...styles.value, color: queryPercentage > 30 ? 'var(--color-adverse)' : 'inherit' }}>
            {queryPercentage}%
          </div>
        </div>
        <div style={styles.footer} className="stat-subtext">
          {adverseDisclaimerCount} projects with critical flags
        </div>
      </div>

      {/* 4. Citizen Reports Card */}
      <div className="material-card" style={styles.card}>
        <div className="floating-icon-box box-cyan">
          <MessageSquare size={24} />
        </div>
        <div style={styles.content}>
          <span className="stat-title" style={styles.title}>Citizen Audits</span>
          <div className="stat-value" style={styles.value}>{citizenVerifiedCount}</div>
        </div>
        <div style={styles.footer} className="stat-subtext">
          Simulated live ground verifications
        </div>
      </div>

    </div>
  );
}

const styles = {
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: '24px',
    width: '100%',
    paddingTop: '16px', // Extra space for overhanging icons
  },
  card: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    minHeight: '120px',
    textAlign: 'right',
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    marginTop: '4px',
  },
  title: {
    fontSize: '0.82rem',
    color: 'var(--text-secondary)',
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    marginBottom: '2px',
  },
  value: {
    fontFamily: 'var(--font-display)',
    fontSize: '1.65rem',
    fontWeight: '800',
    color: 'var(--text-title)',
  },
  currencyIcon: {
    fontSize: '0.9rem',
    fontWeight: '800',
    letterSpacing: '0.02em',
  },
  footer: {
    borderTop: '1px solid var(--border-light)',
    paddingTop: '10px',
    marginTop: '12px',
    textAlign: 'left',
    fontSize: '0.75rem',
    color: 'var(--text-secondary)',
  }
};
