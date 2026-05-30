import React, { useState } from 'react';
import { 
  X, 
  DollarSign, 
  Percent, 
  FileText, 
  BrainCircuit, 
  Calendar, 
  MessageSquare,
  Camera,
  AlertTriangle,
  CheckCircle2,
  User,
  Star,
  ShieldCheck,
  Send
} from 'lucide-react';

export default function ProjectDetailsModal({ project, onClose, onAddCitizenReport }) {
  const [activeTab, setActiveTab] = useState('audit');
  const [reportToggle, setReportToggle] = useState('ai');
  
  const [citizenName, setCitizenName] = useState('');
  const [citizenComment, setCitizenComment] = useState('');
  const [citizenRating, setCitizenRating] = useState(5);
  const [hasPhoto, setHasPhoto] = useState(false);
  const [simulatedPhotoUrl, setSimulatedPhotoUrl] = useState('');
  const [formSuccess, setFormSuccess] = useState(false);

  const formatCurrency = (value) => {
    return `KES ${value.toLocaleString()}`;
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

  const getSeverityStyle = (severity) => {
    switch (severity.toLowerCase()) {
      case 'high':
        return { color: 'var(--color-adverse)', bg: 'var(--color-adverse-glow)' };
      case 'medium':
        return { color: 'var(--color-qualified)', bg: 'var(--color-qualified-glow)' };
      case 'low':
      default:
        return { color: 'var(--accent-blue)', bg: 'rgba(26, 115, 232, 0.08)' };
    }
  };

  const handleSubmitReport = (e) => {
    e.preventDefault();
    if (!citizenName || !citizenComment) return;

    const newReport = {
      id: `CR-SIM-${Date.now()}`,
      author: citizenName,
      date: new Date().toISOString().split('T')[0],
      rating: citizenRating,
      comment: citizenComment,
      image: hasPhoto 
        ? simulatedPhotoUrl || "https://images.unsplash.com/photo-1590069261209-f8e9b8642343?auto=format&fit=crop&w=600&q=80"
        : null,
      verificationStatus: "Ground Verified"
    };

    onAddCitizenReport(project.id, newReport);
    setFormSuccess(true);
    
    setTimeout(() => {
      setCitizenName('');
      setCitizenComment('');
      setCitizenRating(5);
      setHasPhoto(false);
      setSimulatedPhotoUrl('');
      setFormSuccess(false);
    }, 2000);
  };

  const simulatedPhotos = [
    { name: "Construction Site", url: "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?auto=format&fit=crop&w=600&q=80" },
    { name: "Sewer Pipes", url: "https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=600&q=80" },
    { name: "School Yard", url: "https://images.unsplash.com/photo-1540575467063-178a50c2df87?auto=format&fit=crop&w=600&q=80" },
    { name: "Solar Panels", url: "https://images.unsplash.com/photo-1509391366360-2e959784a276?auto=format&fit=crop&w=600&q=80" }
  ];

  return (
    <div className="modal-overlay" style={styles.overlay}>
      <div className="modal-content" style={styles.modal}>
        
        {/* Modal Header */}
        <div style={styles.header}>
          <div style={styles.headerLeft}>
            <span className="badge badge-clean" style={{ fontSize: '0.7rem' }}>
              {project.sector}
            </span>
            <h2 style={styles.modalTitle}>{project.title}</h2>
            <div style={styles.metaSub}>
              <span>{project.county} County · {project.ward} Ward</span>
              <span style={styles.divider}>|</span>
              <span style={styles.idText}>{project.id}</span>
            </div>
          </div>
          <button style={styles.closeBtn} onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {/* Tab Buttons */}
        <div style={styles.tabsRow}>
          <button 
            style={{ ...styles.tabBtn, ...(activeTab === 'audit' ? styles.activeTab : {}) }}
            onClick={() => setActiveTab('audit')}
          >
            <BrainCircuit size={14} />
            OAG Audit & AI
          </button>
          <button 
            style={{ ...styles.tabBtn, ...(activeTab === 'financials' ? styles.activeTab : {}) }}
            onClick={() => setActiveTab('financials')}
          >
            <DollarSign size={14} />
            Ledger & Queries
          </button>
          <button 
            style={{ ...styles.tabBtn, ...(activeTab === 'timeline' ? styles.activeTab : {}) }}
            onClick={() => setActiveTab('timeline')}
          >
            <Calendar size={14} />
            Milestones
          </button>
          <button 
            style={{ ...styles.tabBtn, ...(activeTab === 'citizen' ? styles.activeTab : {}) }}
            onClick={() => setActiveTab('citizen')}
          >
            <MessageSquare size={14} />
            Citizen Hub ({project.citizenReports.length})
          </button>
        </div>

        {/* Modal Body */}
        <div style={styles.body}>
          
          {/* TAB 1: AUDIT & AI */}
          {activeTab === 'audit' && (
            <div style={styles.tabContent}>
              <div style={styles.auditHeader}>
                <div style={styles.auditHeaderLeft}>
                  <span style={styles.sectionLabel}>Auditor General Review</span>
                  <div style={styles.opinionRow}>
                    <span style={styles.opinionTitle}>Opinion Rating:</span>
                    <span className={`badge ${getOpinionBadgeClass(project.oagOpinion)}`}>
                      {project.oagOpinion} Opinion
                    </span>
                  </div>
                </div>

                <div style={styles.toggleContainer}>
                  <button 
                    style={{ ...styles.toggleBtn, ...(reportToggle === 'ai' ? styles.toggleActive : {}) }}
                    onClick={() => setReportToggle('ai')}
                  >
                    <BrainCircuit size={13} />
                    AI Summary
                  </button>
                  <button 
                    style={{ ...styles.toggleBtn, ...(reportToggle === 'official' ? styles.toggleActive : {}) }}
                    onClick={() => setReportToggle('official')}
                  >
                    <FileText size={13} />
                    Official Report
                  </button>
                </div>
              </div>

              {reportToggle === 'ai' ? (
                <div style={styles.aiPanel}>
                  <div style={styles.aiAvatar}>
                    <BrainCircuit size={24} style={{ color: 'var(--accent-secondary)' }} />
                  </div>
                  <div style={styles.aiBody}>
                    <div style={styles.aiTitle}>WaziGov AI Explainer</div>
                    <div style={styles.aiText}>{project.aiSummary}</div>
                    <div style={styles.aiFooter}>
                      <ShieldCheck size={12} style={{ color: 'var(--color-clean)', marginRight: '4px' }} />
                      Parsed automatically from the official Office of the Auditor General reports.
                    </div>
                  </div>
                </div>
              ) : (
                <div style={styles.officialPanel}>
                  <div style={styles.oagCrest}>
                    <div style={styles.crestText}>OFFICE OF THE AUDITOR GENERAL · KENYA</div>
                  </div>
                  <pre style={styles.reportPre}>{project.oagReportText}</pre>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: LEDGER & QUERIES */}
          {activeTab === 'financials' && (
            <div style={styles.tabContent}>
              <span style={styles.sectionLabel}>Financial Ledger Overview</span>
              
              <div style={styles.ledgerGrid}>
                <div style={styles.ledgerBox}>
                  <span style={styles.ledgerBoxLabel}>Approved Budget</span>
                  <span style={styles.ledgerBoxVal}>{formatCurrency(project.budget)}</span>
                </div>
                <div style={styles.ledgerBox}>
                  <span style={styles.ledgerBoxLabel}>Total Incurred Spent</span>
                  <span style={{ 
                    ...styles.ledgerBoxVal, 
                    color: project.spent > project.budget ? 'var(--color-adverse)' : 'var(--text-title)' 
                  }}>
                    {formatCurrency(project.spent)}
                  </span>
                </div>
                <div style={styles.ledgerBox}>
                  <span style={styles.ledgerBoxLabel}>Budget Variance</span>
                  <span style={{ 
                    ...styles.ledgerBoxVal, 
                    color: project.spent > project.budget ? 'var(--color-adverse)' : 'var(--color-clean)' 
                  }}>
                    {project.spent > project.budget 
                      ? `+ ${formatCurrency(project.spent - project.budget)} (Overspent)` 
                      : `- ${formatCurrency(project.budget - project.spent)} (Under budget)`
                    }
                  </span>
                </div>
              </div>

              <div style={styles.absorptionBarRow}>
                <div style={styles.absorptionText}>
                  <span>Budget Absorption Rate</span>
                  <span style={{ fontWeight: '700' }}>
                    {Math.round((project.spent / project.budget) * 100)}%
                  </span>
                </div>
                <div className="progress-bar-container" style={{ height: '8px' }}>
                  <div 
                    className="progress-bar-fill"
                    style={{ 
                      width: `${Math.min((project.spent / project.budget) * 100, 100)}%`,
                      background: project.spent > project.budget ? 'var(--color-adverse)' : 'var(--accent-blue)'
                    }}
                  />
                </div>
              </div>

              <div style={{ marginTop: '12px' }}>
                <span style={styles.sectionLabel}>Auditor General Discrepancies ({project.auditorGeneralQueries.length})</span>
                {project.auditorGeneralQueries.length > 0 ? (
                  <div style={styles.queriesList}>
                    {project.auditorGeneralQueries.map((q) => {
                      const sev = getSeverityStyle(q.severity);
                      return (
                        <div key={q.id} style={{ ...styles.queryCard, borderLeft: `3px solid ${sev.color}` }}>
                          <div style={styles.queryHeader}>
                            <div style={styles.queryTitleRow}>
                              <span style={styles.queryId}>{q.id}</span>
                              <span style={styles.queryTitle}>{q.issue}</span>
                            </div>
                            <span 
                              className="badge" 
                              style={{ 
                                color: sev.color, 
                                background: sev.bg, 
                                borderColor: 'transparent',
                                fontSize: '0.62rem'
                              }}
                            >
                              {q.severity} Severity
                            </span>
                          </div>
                          <p style={styles.queryDesc}>{q.description}</p>
                          <div style={styles.queryAmount}>
                            <span>Queried Amount: </span>
                            <span style={{ fontWeight: '700', color: sev.color }}>
                              {formatCurrency(q.amount)}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={styles.emptyQueries}>
                    <CheckCircle2 size={32} style={{ color: 'var(--color-clean)', marginBottom: '8px' }} />
                    <span>No financial irregularities or queries flagged by the OAG! Excellent accountability.</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: TIMELINE */}
          {activeTab === 'timeline' && (
            <div style={styles.tabContent}>
              <span style={styles.sectionLabel}>Project Milestone Timeline</span>
              <div style={styles.timelineContainer}>
                {project.milestones.map((m, idx) => (
                  <div key={idx} style={styles.timelineItem}>
                    <div style={styles.timelineMarker}>
                      <div 
                        style={{ 
                          ...styles.timelineDot, 
                          background: m.status === 'completed' ? 'var(--color-clean)' : 'var(--accent-blue)',
                          boxShadow: m.status === 'completed' ? '0 0 8px rgba(46, 125, 50, 0.3)' : 'none'
                        }} 
                      />
                      {idx < project.milestones.length - 1 && <div style={styles.timelineLine} />}
                    </div>
                    <div style={styles.timelineDetails}>
                      <div style={styles.timelineDate}>{m.date}</div>
                      <div style={styles.timelineLabel}>{m.label}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: CITIZEN HUB */}
          {activeTab === 'citizen' && (
            <div style={styles.tabContent}>
              <div style={styles.citizenSplit}>
                
                <div style={styles.citizenFeed}>
                  <span style={styles.sectionLabel}>Ground Observations ({project.citizenReports.length})</span>
                  {project.citizenReports.length > 0 ? (
                    <div style={styles.commentsList}>
                      {project.citizenReports.map((c) => (
                        <div key={c.id} style={styles.commentCard} className="material-card" style={{ ...styles.commentCard, marginTop: 0 }}>
                          <div style={styles.commentHeader}>
                            <div style={styles.commentUser}>
                              <div style={styles.userAvatar}>
                                <User size={12} />
                              </div>
                              <span style={styles.commentAuthor}>{c.author}</span>
                            </div>
                            <div style={styles.commentMeta}>
                              <span style={styles.commentDate}>{c.date}</span>
                              <span className="badge badge-clean" style={{ fontSize: '0.6rem', padding: '1px 6px' }}>
                                {c.verificationStatus}
                              </span>
                            </div>
                          </div>
                          
                          <div style={styles.ratingRow}>
                            {[...Array(5)].map((_, i) => (
                              <Star 
                                key={i} 
                                size={12} 
                                fill={i < c.rating ? 'var(--color-qualified)' : 'none'} 
                                stroke={i < c.rating ? 'var(--color-qualified)' : 'rgba(0,0,0,0.2)'} 
                              />
                            ))}
                          </div>

                          <p style={styles.commentText}>{c.comment}</p>

                          {c.image && (
                            <div style={styles.photoContainer}>
                              <img src={c.image} alt="Ground truth evidence" style={styles.groundPhoto} />
                              <div style={styles.photoTag}>
                                <Camera size={10} style={{ marginRight: '3px' }} />
                                Citizen Ground Evidence Photo
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={styles.emptyQueries}>
                      <MessageSquare size={32} style={{ color: 'rgba(0,0,0,0.1)', marginBottom: '8px' }} />
                      <span>No citizen reports submitted yet. Be the first to verify ground progress!</span>
                    </div>
                  )}
                </div>

                <div style={styles.citizenFormPanel} className="material-card" style={{ ...styles.citizenFormPanel, marginTop: 0 }}>
                  <span style={styles.sectionLabel} style={{ color: 'var(--accent-blue)', fontWeight: '700' }}>Submit Ground Observation</span>
                  
                  {formSuccess ? (
                    <div style={styles.formSuccessBlock}>
                      <CheckCircle2 size={40} style={{ color: 'var(--color-clean)', marginBottom: '12px' }} />
                      <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: '700', color: 'var(--text-title)' }}>Ground Report Saved!</h4>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textAlign: 'center', marginTop: '6px' }}>
                        Your verified ground report has been integrated into the platform ledger.
                      </p>
                    </div>
                  ) : (
                    <form onSubmit={handleSubmitReport} style={styles.form}>
                      <div style={styles.formGroup}>
                        <label style={styles.formLabel}>Citizen Auditor Name / Alias</label>
                        <input 
                          type="text" 
                          className="glass-input" 
                          required
                          style={styles.textInput}
                          placeholder="e.g. Omondi K. / Anon" 
                          value={citizenName}
                          onChange={(e) => setCitizenName(e.target.value)}
                        />
                      </div>

                      <div style={styles.formGroup}>
                        <label style={styles.formLabel}>Ground Verification Stars</label>
                        <div style={styles.starInputRow}>
                          {[1, 2, 3, 4, 5].map((star) => (
                            <button
                              key={star}
                              type="button"
                              style={styles.starInputBtn}
                              onClick={() => setCitizenRating(star)}
                            >
                              <Star 
                                size={18} 
                                fill={star <= citizenRating ? 'var(--color-qualified)' : 'none'} 
                                stroke={star <= citizenRating ? 'var(--color-qualified)' : 'rgba(0,0,0,0.3)'} 
                              />
                            </button>
                          ))}
                          <span style={styles.ratingText}>
                            {citizenRating === 5 ? 'Excellent' : citizenRating === 4 ? 'Good' : citizenRating === 3 ? 'Average' : citizenRating === 2 ? 'Substandard' : 'Defective'}
                          </span>
                        </div>
                      </div>

                      <div style={styles.formGroup}>
                        <label style={styles.formLabel}>Ground Observations</label>
                        <textarea 
                          className="glass-input" 
                          required
                          style={styles.textarea}
                          placeholder="What did you see on site? Are contractors present? Are materials substandard?"
                          value={citizenComment}
                          onChange={(e) => setCitizenComment(e.target.value)}
                        />
                      </div>

                      <div style={styles.formGroup}>
                        <label style={styles.formLabel}>Add Photo Evidence (Simulated)</label>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <button
                            type="button"
                            className="btn-secondary"
                            style={{ justifyContent: 'center', fontSize: '0.8rem', padding: '8px' }}
                            onClick={() => setHasPhoto(!hasPhoto)}
                          >
                            <Camera size={14} />
                            {hasPhoto ? "Remove Photo" : "Upload Site Photograph"}
                          </button>
                          
                          {hasPhoto && (
                            <div style={styles.simulatedPhotosSelector}>
                              <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Select Evidence Type:</span>
                              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '4px' }}>
                                {simulatedPhotos.map((p, idx) => (
                                  <button
                                    key={idx}
                                    type="button"
                                    style={{
                                      ...styles.simPhotoOption,
                                      borderColor: simulatedPhotoUrl === p.url ? 'var(--accent-secondary)' : 'var(--border-light)',
                                      background: simulatedPhotoUrl === p.url ? 'var(--ke-green-light)' : '#ffffff'
                                    }}
                                    onClick={() => setSimulatedPhotoUrl(p.url)}
                                  >
                                    {p.name}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      <button type="submit" className="btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: '8px' }}>
                        <Send size={14} />
                        Publish Observations
                      </button>
                    </form>
                  )}
                </div>

              </div>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}

const styles = {
  overlay: {
    padding: '24px',
  },
  modal: {
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: '24px 28px',
    borderBottom: '1px solid var(--border-light)',
  },
  headerLeft: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: '6px',
    maxWidth: '90%',
  },
  modalTitle: {
    fontFamily: 'var(--font-display)',
    fontWeight: '800',
    fontSize: '1.4rem',
    color: 'var(--text-title)',
    lineHeight: '1.3',
    textAlign: 'left',
  },
  metaSub: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '0.8rem',
    color: 'var(--text-secondary)',
  },
  divider: {
    color: 'rgba(0, 0, 0, 0.1)',
  },
  idText: {
    fontFamily: 'monospace',
    color: 'var(--accent-blue)',
    fontSize: '0.75rem',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    padding: '4px',
  },
  tabsRow: {
    display: 'flex',
    background: 'rgba(240, 242, 245, 0.5)',
    borderBottom: '1px solid var(--border-light)',
    padding: '0 16px',
    overflowX: 'auto',
    whiteSpace: 'nowrap',
  },
  tabBtn: {
    background: 'none',
    border: 'none',
    borderBottom: '2px solid transparent',
    color: 'var(--text-secondary)',
    padding: '14px 20px',
    cursor: 'pointer',
    fontSize: '0.85rem',
    fontWeight: '600',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'var(--transition-smooth)',
  },
  activeTab: {
    color: 'var(--accent-blue)',
    borderBottomColor: 'var(--accent-blue)',
    background: '#ffffff',
  },
  body: {
    padding: '24px 28px',
    maxHeight: '60vh',
    overflowY: 'auto',
    textAlign: 'left',
  },
  tabContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  sectionLabel: {
    fontSize: '0.75rem',
    fontWeight: '700',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    display: 'block',
    marginBottom: '4px',
  },
  auditHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '16px',
    background: 'var(--bg-main)',
    border: '1px solid var(--border-light)',
    padding: '14px 20px',
    borderRadius: '10px',
  },
  auditHeaderLeft: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  opinionRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  opinionTitle: {
    fontSize: '0.85rem',
    color: 'var(--text-main)',
  },
  toggleContainer: {
    display: 'flex',
    background: 'rgba(0, 0, 0, 0.05)',
    border: '1px solid var(--border-light)',
    borderRadius: '8px',
    padding: '2px',
  },
  toggleBtn: {
    background: 'none',
    border: 'none',
    color: 'var(--text-secondary)',
    fontSize: '0.72rem',
    fontWeight: '600',
    padding: '6px 12px',
    borderRadius: '6px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    transition: 'var(--transition-smooth)',
  },
  toggleActive: {
    background: '#ffffff',
    color: 'var(--text-title)',
    boxShadow: '0 2px 6px rgba(0,0,0,0.06)',
  },
  aiPanel: {
    display: 'flex',
    gap: '16px',
    background: 'rgba(0, 188, 212, 0.03)',
    border: '1px solid rgba(0, 188, 212, 0.12)',
    borderRadius: '12px',
    padding: '20px',
  },
  aiAvatar: {
    width: '44px',
    height: '44px',
    borderRadius: '10px',
    background: 'rgba(0, 188, 212, 0.08)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    flexShrink: 0,
    border: '1px solid rgba(0, 188, 212, 0.15)',
  },
  aiBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  aiTitle: {
    fontFamily: 'var(--font-display)',
    fontWeight: '700',
    fontSize: '0.95rem',
    color: 'var(--accent-secondary)',
  },
  aiText: {
    fontSize: '0.92rem',
    color: 'var(--text-main)',
    lineHeight: '1.55',
  },
  aiFooter: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '0.72rem',
    color: 'var(--text-secondary)',
    marginTop: '6px',
  },
  officialPanel: {
    background: '#0d1321',
    border: '1px solid rgba(0, 0, 0, 0.08)',
    borderRadius: '10px',
    padding: '24px',
    fontFamily: 'monospace',
    fontSize: '0.85rem',
    color: '#ccd6f6',
    maxHeight: '400px',
    overflowY: 'auto',
  },
  oagCrest: {
    textAlign: 'center',
    borderBottom: '2px solid rgba(0,0,0,0.15)',
    paddingBottom: '12px',
    marginBottom: '16px',
  },
  crestText: {
    fontWeight: '700',
    letterSpacing: '0.1em',
    color: '#ffffff',
  },
  reportPre: {
    whiteSpace: 'pre-wrap',
    fontFamily: 'Courier New, Courier, monospace',
    lineHeight: '1.5',
  },
  ledgerGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '16px',
  },
  ledgerBox: {
    background: 'var(--bg-main)',
    border: '1px solid var(--border-light)',
    borderRadius: '10px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  ledgerBoxLabel: {
    fontSize: '0.7rem',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  },
  ledgerBoxVal: {
    fontFamily: 'var(--font-display)',
    fontWeight: '800',
    fontSize: '1.2rem',
    color: 'var(--text-title)',
  },
  absorptionBarRow: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    background: 'var(--bg-main)',
    padding: '12px 16px',
    border: '1px solid var(--border-light)',
    borderRadius: '10px',
  },
  absorptionText: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.8rem',
    color: 'var(--text-main)',
  },
  queriesList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  queryCard: {
    background: 'var(--bg-main)',
    border: '1px solid var(--border-light)',
    borderRadius: '8px',
    padding: '14px 18px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  queryHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  queryTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  queryId: {
    fontFamily: 'monospace',
    color: 'var(--accent-blue)',
    fontWeight: '700',
    fontSize: '0.8rem',
  },
  queryTitle: {
    fontWeight: '700',
    color: 'var(--text-title)',
    fontSize: '0.9rem',
  },
  queryDesc: {
    fontSize: '0.82rem',
    color: 'var(--text-main)',
    lineHeight: '1.45',
  },
  queryAmount: {
    fontSize: '0.8rem',
    color: 'var(--text-secondary)',
  },
  emptyQueries: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '30px 20px',
    background: 'var(--color-clean-glow)',
    border: '1px dashed rgba(46, 125, 50, 0.2)',
    borderRadius: '10px',
    textAlign: 'center',
    fontSize: '0.85rem',
    color: 'var(--text-main)',
  },
  timelineContainer: {
    display: 'flex',
    flexDirection: 'column',
    padding: '10px 0',
  },
  timelineItem: {
    display: 'flex',
    gap: '16px',
  },
  timelineMarker: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  timelineDot: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    zIndex: 1,
  },
  timelineLine: {
    width: '2px',
    flex: 1,
    background: 'var(--border-light)',
    margin: '4px 0',
  },
  timelineDetails: {
    paddingBottom: '24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  timelineDate: {
    fontSize: '0.72rem',
    fontFamily: 'monospace',
    color: 'var(--accent-blue)',
    fontWeight: '600',
  },
  timelineLabel: {
    fontWeight: '600',
    fontSize: '0.88rem',
    color: 'var(--text-title)',
  },
  citizenSplit: {
    display: 'grid',
    gridTemplateColumns: '1.2fr 0.8fr',
    gap: '20px',
  },
  citizenFeed: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  commentsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    maxHeight: '420px',
    overflowY: 'auto',
    paddingRight: '6px',
  },
  commentCard: {
    padding: '14px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  commentHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  commentUser: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  userAvatar: {
    width: '20px',
    height: '20px',
    borderRadius: '50%',
    background: 'rgba(0,0,0,0.06)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    color: 'var(--text-secondary)',
  },
  commentAuthor: {
    fontWeight: '600',
    fontSize: '0.8rem',
    color: 'var(--text-title)',
  },
  commentMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  commentDate: {
    fontSize: '0.7rem',
    color: 'var(--text-secondary)',
  },
  ratingRow: {
    display: 'flex',
    gap: '2px',
  },
  commentText: {
    fontSize: '0.82rem',
    color: 'var(--text-main)',
    lineHeight: '1.45',
  },
  photoContainer: {
    position: 'relative',
    borderRadius: '8px',
    overflow: 'hidden',
    marginTop: '4px',
  },
  groundPhoto: {
    width: '100%',
    maxHeight: '160px',
    objectFit: 'cover',
    display: 'block',
  },
  photoTag: {
    position: 'absolute',
    bottom: '8px',
    left: '8px',
    background: 'rgba(0,0,0,0.7)',
    borderRadius: '4px',
    padding: '3px 8px',
    fontSize: '0.62rem',
    color: '#ffffff',
    display: 'flex',
    alignItems: 'center',
  },
  citizenFormPanel: {
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    height: 'fit-content',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  formLabel: {
    fontSize: '0.72rem',
    fontWeight: '600',
    color: 'var(--text-secondary)',
  },
  textInput: {
    border: '1px solid var(--border-light)',
    color: 'var(--text-main)',
    background: 'var(--bg-main)',
    borderRadius: '6px',
    padding: '8px 12px',
  },
  starInputRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  starInputBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '2px',
  },
  ratingText: {
    fontSize: '0.7rem',
    color: 'var(--text-secondary)',
    marginLeft: '6px',
    fontWeight: '600',
  },
  textarea: {
    height: '70px',
    fontSize: '0.82rem',
    resize: 'none',
    border: '1px solid var(--border-light)',
    color: 'var(--text-main)',
    background: 'var(--bg-main)',
    borderRadius: '6px',
    padding: '8px 12px',
  },
  simulatedPhotosSelector: {
    background: 'var(--bg-main)',
    border: '1px solid var(--border-light)',
    borderRadius: '8px',
    padding: '8px 10px',
  },
  simPhotoOption: {
    fontSize: '0.62rem',
    padding: '4px 8px',
    borderRadius: '4px',
    border: '1px solid',
    color: 'var(--text-main)',
    cursor: 'pointer',
    transition: 'var(--transition-smooth)',
  },
  formSuccessBlock: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 20px',
    background: 'var(--color-clean-glow)',
    border: '1px solid rgba(46, 125, 50, 0.2)',
    borderRadius: '10px',
  }
};
