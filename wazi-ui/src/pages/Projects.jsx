import React from 'react';
import { List, Database, Layers3, FileText } from 'lucide-react';

function formatCount(value) {
  const count = Number(value);
  return Number.isFinite(count) ? count : 0;
}

function formatAmount(value) {
  if (value === null || value === undefined || value === '') {
    return 'Not disclosed';
  }

  if (typeof value === 'number') {
    return value.toLocaleString();
  }

  return String(value);
}

function getSectionData(projectData, key) {
  return projectData?.project_implementation?.[key]?.data || [];
}

function SummaryCard({ label, value, icon: Icon }) {
  return (
    <div className="projects-summary-item">
      <Icon size={18} />
      <div>
        <strong>{value}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

function ProjectsTable({ title, description, rows }) {
  return (
    <section className="projects-table-card material-card">
      <div className="projects-table-header">
        <div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <span className="badge badge-clean">{rows.length} counties</span>
      </div>

      {rows.length > 0 ? (
        <div className="projects-table-wrap">
          <table className="projects-table">
            <thead>
              <tr>
                <th>County</th>
                <th>Projects</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.county}-${row.amount_kshs_raw || row.amount_kshs || row.number_of_projects || 'row'}`}>
                  <td>{row.county || 'Unknown county'}</td>
                  <td>{row.number_of_projects ?? 'Not disclosed'}</td>
                  <td>{formatAmount(row.amount_kshs_raw || row.amount_kshs)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="projects-empty">No rows were found in this section.</div>
      )}
    </section>
  );
}

export default function Projects({ projectData = {} }) {
  const metadata = projectData.metadata || {};
  const summaryStats = metadata.summary_stats || {};

  const delayedProjects = getSectionData(projectData, 'delayed_projects_county_executives');
  const stalledProjects = getSectionData(projectData, 'stalled_abandoned_projects_county_executives');

  const totalMentions = delayedProjects.length + stalledProjects.length;

  return (
    <div className="projects-page">
      <header className="projects-hero material-card">
        <div>
          <p className="projects-kicker">Government project output</p>
          <h1 className="page-title projects-title">Projects</h1>
          <p className="projects-description">
            {metadata.description || 'Extracted project and financial performance data for FY 2023-2024.'}
          </p>
        </div>

        <div className="projects-summary">
          <SummaryCard label="Delayed counties" value={formatCount(summaryStats.counties_with_delayed_projects_exec)} icon={Database} />
          <SummaryCard label="Stalled counties" value={formatCount(summaryStats.counties_with_stalled_projects_exec)} icon={Layers3} />
          <SummaryCard label="Project rows shown" value={totalMentions} icon={FileText} />
        </div>
      </header>

      <section className="projects-table-grid">
        <ProjectsTable
          title="Delayed projects"
          description="County Executives with delayed capital projects from Appendix 26."
          rows={delayedProjects}
        />

        <ProjectsTable
          title="Stalled or abandoned projects"
          description="County Executives with stalled or abandoned projects from Appendix 27."
          rows={stalledProjects}
        />
      </section>

      <section className="projects-note material-card">
        <strong>Source</strong>
        <p>
          {metadata.source?.oag_report || 'OAG report'} and {metadata.source?.cob_report || 'COB report'}
          {' '}for fiscal year {metadata.fiscal_year || '2023-2024'}.
        </p>
      </section>
    </div>
  );
}
