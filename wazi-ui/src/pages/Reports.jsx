import React from 'react';
import { AlertTriangle, BookOpen, ExternalLink, FileText, Loader2, Newspaper } from 'lucide-react';
import { PRIMARY_BUNDLE_URL } from '../data/cobOagBundle';

function formatCount(count, label) {
  return `${count} ${label}${count === 1 ? '' : 's'}`;
}

function StatusBadge({ value }) {
  const status = (value || 'Partial').toLowerCase();
  const palette = {
    compliant: { background: 'rgba(34, 197, 94, 0.12)', color: '#166534', border: 'rgba(34, 197, 94, 0.22)' },
    'non-compliant': { background: 'rgba(220, 38, 38, 0.10)', color: '#991b1b', border: 'rgba(220, 38, 38, 0.20)' },
    partial: { background: 'rgba(234, 179, 8, 0.14)', color: '#854d0e', border: 'rgba(234, 179, 8, 0.22)' },
  };
  const styles = palette[status] || palette.partial;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '6px 12px',
        borderRadius: '999px',
        border: `1px solid ${styles.border}`,
        background: styles.background,
        color: styles.color,
        fontSize: '0.78rem',
        fontWeight: 700,
        letterSpacing: '0.02em',
      }}
    >
      {value || 'Partial'}
    </span>
  );
}

function buildReportSummary(report) {
  const pageCount = Number(report.page_count || 0);
  const tableCount = Number(report.table_count || 0);
  const cobCount = Array.isArray(report.cob_findings) ? report.cob_findings.length : 0;
  const oagCount = Array.isArray(report.oag_findings) ? report.oag_findings.length : 0;

  const coverage = [
    pageCount ? `${pageCount} page${pageCount === 1 ? '' : 's'}` : null,
    tableCount ? `${tableCount} table${tableCount === 1 ? '' : 's'} detected` : null,
  ].filter(Boolean).join(' and ');

  const sourceName = report.source_file ? report.source_file.split(/[\\/]/).pop() : 'the source PDF';

  if (cobCount === 0 && oagCount === 0) {
    return `This report was loaded from ${sourceName}. The bundle currently exposes ${coverage || 'detector metadata'}, but no sentence-level COB or OAG findings have been extracted yet.`;
  }

  return `This report was loaded from ${sourceName} and summarized into ${coverage || 'the available report metadata'}. The citizen view below highlights the public COB and OAG findings extracted from the bundle.`;
}

function buildEmptyFindingMessage(type, report) {
  const sourceLabel = report.institution || 'this report';
  if (type === 'cob') {
    return `No COB highlights were extracted for ${sourceLabel} yet.`;
  }
  return `No OAG findings were extracted for ${sourceLabel} yet.`;
}

function FindingList({ title, items, type, report }) {
  return (
    <section style={styles.sectionCard}>
      <div style={styles.sectionHeader}>
        <div>
          <p style={styles.sectionEyebrow}>{type === 'cob' ? 'COB' : 'OAG'}</p>
          <h3 style={styles.sectionTitle}>{title}</h3>
        </div>
        <span style={styles.sectionCount}>{formatCount(items.length, 'item')}</span>
      </div>

      {items.length > 0 ? (
        <div style={styles.findingList}>
          {items.map((item) => (
            <article key={item.report_id} style={styles.findingItem}>
              <div style={styles.findingBody}>
                <p style={styles.findingTitle}>{item.title}</p>
                <p style={styles.findingSummary}>{item.summary}</p>
                <div style={styles.findingMeta}>
                  {item.fiscal_year ? <span>{item.fiscal_year}</span> : null}
                  {typeof item.amount === 'number' ? <span>KES {item.amount.toLocaleString()}</span> : null}
                </div>
              </div>
              {item.link ? (
                <a href={item.link} target="_blank" rel="noreferrer" style={styles.readLink}>
                  <ExternalLink size={14} />
                  <span>Read report</span>
                </a>
              ) : (
                <span style={styles.mutedLink}>No public link</span>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div style={styles.emptyBlock}>
          <FileText size={18} />
          <span>{buildEmptyFindingMessage(type, report)}</span>
        </div>
      )}
    </section>
  );
}

function ReportCard({ report }) {
  const cobCount = Array.isArray(report.cob_findings) ? report.cob_findings.length : 0;
  const oagCount = Array.isArray(report.oag_findings) ? report.oag_findings.length : 0;
  const hasFindings = cobCount > 0 || oagCount > 0;

  return (
    <article style={styles.reportCard}>
      <div style={styles.reportTopRow}>
        <div>
          <p style={styles.reportEyebrow}>{report.institution || 'COB / OAG'}</p>
          <h2 style={styles.reportTitle}>{report.title}</h2>
        </div>
        <StatusBadge value={report.overall_status} />
      </div>

      <div style={styles.summaryBlock}>
        <p style={styles.reportSummary}>{report.summary || buildReportSummary(report)}</p>
        <p style={styles.reportNarrative}>{buildReportSummary(report)}</p>
      </div>

      <div style={styles.reportMetaRow}>
        <span style={styles.metaChip}>{report.fiscal_year || '2023-2024'}</span>
        <span style={styles.metaChip}>{formatCount(report.table_count || 0, 'table')}</span>
        <span style={styles.metaChip}>{report.page_count || 0} pages</span>
        {report.source_file ? <span style={styles.metaChip}>{report.source_file}</span> : null}
      </div>

      <div style={styles.coverageRow}>
        <div style={styles.coverageCard}>
          <span style={styles.coverageLabel}>COB highlights</span>
          <strong style={styles.coverageValue}>{cobCount}</strong>
        </div>
        <div style={styles.coverageCard}>
          <span style={styles.coverageLabel}>OAG findings</span>
          <strong style={styles.coverageValue}>{oagCount}</strong>
        </div>
        <div style={styles.coverageCard}>
          <span style={styles.coverageLabel}>Reading mode</span>
          <strong style={styles.coverageValue}>{hasFindings ? 'Citizen summary' : 'Document extract'}</strong>
        </div>
      </div>

      <div style={styles.findingGrid}>
        <FindingList title="Citizen-friendly COB highlights" items={report.cob_findings || []} type="cob" report={report} />
        <FindingList title="Citizen-friendly OAG findings" items={report.oag_findings || []} type="oag" report={report} />
      </div>
    </article>
  );
}

export default function Reports({ bundleState }) {
  const status = bundleState?.status || 'loading';
  const bundle = bundleState?.data;
  const reports = bundle?.reports || [];

  return (
    <div style={styles.page}>
      <section style={styles.heroCard}>
        <div style={styles.heroCopy}>
          <p style={styles.heroEyebrow}>COB + OAG prototype</p>
          <h1 className="page-title" style={styles.heroTitle}>Reports for ordinary citizens</h1>
          <p style={styles.heroText}>
            This section reads the compiled 2023-2024 COB/OAG bundle and turns it into a short,
            readable summary with source links back to the official reports.
          </p>
        </div>

        <div style={styles.heroStats}>
          <div style={styles.heroStat}>
            <span style={styles.heroStatValue}>{bundle?.fiscal_year || '2023-2024'}</span>
            <span style={styles.heroStatLabel}>Fiscal year</span>
          </div>
          <div style={styles.heroStat}>
            <span style={styles.heroStatValue}>{bundle?.report_count ?? reports.length ?? 0}</span>
            <span style={styles.heroStatLabel}>Reports loaded</span>
          </div>
          <div style={styles.heroStat}>
            <span style={styles.heroStatValue}>{bundle?.selection_mode || 'auto'}</span>
            <span style={styles.heroStatLabel}>Bundle mode</span>
          </div>
        </div>
      </section>

      {status === 'loading' ? (
        <div style={styles.statusCard}>
          <Loader2 size={18} className="spin" />
          <span>Loading the public bundle from {PRIMARY_BUNDLE_URL}...</span>
        </div>
      ) : null}

      {status === 'error' ? (
        <div style={styles.errorCard}>
          <AlertTriangle size={18} />
          <div>
            <strong>Could not load the public bundle.</strong>
            <p style={styles.errorText}>
              Check that {PRIMARY_BUNDLE_URL} exists in the Vite public folder. The page will fall back to the copied sample if available.
            </p>
          </div>
        </div>
      ) : null}

      {reports.length > 0 ? (
        <div style={styles.reportStack}>
          {reports.map((report) => (
            <ReportCard key={report.report_id} report={report} />
          ))}
        </div>
      ) : status === 'ready' ? (
        <div style={styles.emptyState}>
          <BookOpen size={22} />
          <h3 style={styles.emptyTitle}>No reports found in the bundle</h3>
          <p style={styles.emptyText}>The bundle loaded successfully, but it did not contain any report entries.</p>
        </div>
      ) : null}

      <div style={styles.sourceNote}>
        <Newspaper size={16} />
        <span>Source JSON is served from the Vite public folder, so refresh the page after replacing the file.</span>
      </div>
    </div>
  );
}

const styles = {
  page: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  heroCard: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '24px',
    padding: '24px',
    borderRadius: '20px',
    background: 'linear-gradient(135deg, rgba(14, 70, 40, 0.98), rgba(20, 94, 66, 0.92))',
    color: '#f8fafc',
    boxShadow: '0 18px 50px rgba(7, 37, 22, 0.20)',
    border: '1px solid rgba(255, 255, 255, 0.10)',
  },
  heroCopy: {
    maxWidth: '720px',
  },
  heroEyebrow: {
    margin: 0,
    textTransform: 'uppercase',
    letterSpacing: '0.18em',
    fontSize: '0.72rem',
    opacity: 0.8,
  },
  heroTitle: {
    marginTop: '8px',
    marginBottom: '12px',
    color: '#ffffff',
  },
  heroText: {
    margin: 0,
    fontSize: '0.95rem',
    lineHeight: 1.7,
    color: 'rgba(255, 255, 255, 0.88)',
  },
  heroStats: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
    gap: '12px',
    minWidth: '320px',
  },
  heroStat: {
    padding: '14px',
    borderRadius: '16px',
    background: 'rgba(255, 255, 255, 0.10)',
    border: '1px solid rgba(255, 255, 255, 0.12)',
  },
  heroStatValue: {
    display: 'block',
    fontSize: '1.05rem',
    fontWeight: 800,
    marginBottom: '4px',
  },
  heroStatLabel: {
    display: 'block',
    fontSize: '0.76rem',
    opacity: 0.8,
  },
  statusCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '14px 18px',
    borderRadius: '14px',
    background: 'rgba(59, 130, 246, 0.08)',
    color: 'var(--text-title)',
    border: '1px solid rgba(59, 130, 246, 0.14)',
  },
  errorCard: {
    display: 'flex',
    gap: '12px',
    padding: '16px 18px',
    borderRadius: '14px',
    background: 'rgba(220, 38, 38, 0.08)',
    border: '1px solid rgba(220, 38, 38, 0.16)',
    color: 'var(--text-title)',
  },
  errorText: {
    margin: '4px 0 0',
    color: 'var(--text-secondary)',
    lineHeight: 1.6,
  },
  reportStack: {
    display: 'flex',
    flexDirection: 'column',
    gap: '18px',
  },
  reportCard: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    padding: '22px',
    borderRadius: '20px',
    background: 'var(--card-bg)',
    border: '1px solid var(--border-light)',
    boxShadow: 'var(--shadow-soft)',
  },
  reportTopRow: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '16px',
    alignItems: 'flex-start',
  },
  reportEyebrow: {
    margin: 0,
    fontSize: '0.74rem',
    fontWeight: 800,
    letterSpacing: '0.14em',
    color: 'var(--accent-secondary)',
    textTransform: 'uppercase',
  },
  reportTitle: {
    margin: '6px 0 0',
    color: 'var(--text-title)',
    fontFamily: 'var(--font-display)',
    fontSize: '1.25rem',
    lineHeight: 1.35,
  },
  reportSummary: {
    margin: 0,
    color: 'var(--text-secondary)',
    lineHeight: 1.75,
  },
  summaryBlock: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  reportNarrative: {
    margin: 0,
    color: 'var(--text-title)',
    fontSize: '0.9rem',
    lineHeight: 1.7,
  },
  reportMetaRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  },
  coverageRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
    gap: '12px',
  },
  coverageCard: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    padding: '14px',
    borderRadius: '14px',
    background: 'linear-gradient(180deg, #ffffff, rgba(248, 250, 252, 0.9))',
    border: '1px solid var(--border-light)',
  },
  coverageLabel: {
    fontSize: '0.72rem',
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  coverageValue: {
    fontSize: '0.92rem',
    color: 'var(--text-title)',
  },
  metaChip: {
    padding: '6px 10px',
    borderRadius: '999px',
    background: 'var(--bg-main)',
    border: '1px solid var(--border-light)',
    color: 'var(--text-secondary)',
    fontSize: '0.75rem',
  },
  findingGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
    gap: '16px',
  },
  sectionCard: {
    padding: '16px',
    borderRadius: '16px',
    background: 'var(--bg-main)',
    border: '1px solid var(--border-light)',
  },
  sectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '12px',
    alignItems: 'flex-start',
    marginBottom: '12px',
  },
  sectionEyebrow: {
    margin: 0,
    fontSize: '0.68rem',
    fontWeight: 800,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    color: 'var(--text-muted)',
  },
  sectionTitle: {
    margin: '4px 0 0',
    fontSize: '0.98rem',
    color: 'var(--text-title)',
  },
  sectionCount: {
    fontSize: '0.72rem',
    color: 'var(--text-muted)',
  },
  findingList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  findingItem: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '12px',
    padding: '12px',
    borderRadius: '14px',
    background: '#ffffff',
    border: '1px solid var(--border-light)',
  },
  findingBody: {
    minWidth: 0,
  },
  findingTitle: {
    margin: 0,
    fontSize: '0.92rem',
    fontWeight: 700,
    color: 'var(--text-title)',
  },
  findingSummary: {
    margin: '6px 0 8px',
    color: 'var(--text-secondary)',
    fontSize: '0.82rem',
    lineHeight: 1.55,
  },
  findingMeta: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    color: 'var(--text-muted)',
    fontSize: '0.72rem',
  },
  readLink: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    whiteSpace: 'nowrap',
    alignSelf: 'flex-start',
    color: 'var(--accent-secondary)',
    textDecoration: 'none',
    fontSize: '0.8rem',
    fontWeight: 700,
  },
  mutedLink: {
    color: 'var(--text-muted)',
    fontSize: '0.8rem',
    whiteSpace: 'nowrap',
  },
  emptyBlock: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    color: 'var(--text-muted)',
    fontSize: '0.85rem',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '32px',
    borderRadius: '18px',
    background: 'var(--bg-main)',
    border: '1px dashed var(--border-light)',
    color: 'var(--text-secondary)',
  },
  emptyTitle: {
    margin: 0,
    fontSize: '1rem',
    color: 'var(--text-title)',
  },
  emptyText: {
    margin: 0,
    textAlign: 'center',
    lineHeight: 1.6,
    maxWidth: '420px',
  },
  sourceNote: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    color: 'var(--text-muted)',
    fontSize: '0.8rem',
    padding: '0 2px 4px',
  },
};
