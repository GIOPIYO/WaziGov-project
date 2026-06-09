import * as fs from 'node:fs';
import * as path from 'node:path';

function createFinding(report, bundleYear, kind) {
  const isCob = kind === 'cob';
  const label = isCob ? 'COB' : 'OAG';
  const sourceName = report.source_file || report.title || 'source report';

  return {
    report_id: `${report.report_id || report.id || 'report'}-${kind}`,
    fiscal_year: report.fiscal_year || bundleYear || '2023-2024',
    title: `${label} source extract`,
    summary: `Extracted from ${sourceName}. The source bundle records ${report.page_count || 0} pages and ${report.table_count || 0} tables.`,
    link: report.source_file || null,
    ...(isCob ? { amount: null } : {}),
    ...(isCob ? {} : { recommendation: 'Review the generated bundle for full document context.' }),
  };
}

function createProjectSummary(report, bundle) {
  const cobFinding = createFinding(report, bundle.fiscal_year, 'cob');
  const oagFinding = createFinding(report, bundle.fiscal_year, 'oag');

  return {
    project_id: report.report_id || report.id,
    title: report.title || 'Public accountability report',
    location: {
      label: report.institution || 'COB/OAG',
    },
    last_updated: bundle.generated_at,
    overall_status: 'Partial',
    summary: report.summary || `${report.institution || 'COB/OAG'} report extracted from the 2023-2024 bundle.`,
    cob_findings: [cobFinding],
    oag_findings: [oagFinding],
  };
}

function main() {
  const projectRoot = process.cwd();
  const bundlePath = path.join(projectRoot, 'outputs', 'cob_oag_2023_2024_full.json');
  const outputPath = path.join(projectRoot, 'public', 'data', 'projects.json');

  const bundle = JSON.parse(fs.readFileSync(bundlePath, 'utf8'));
  const reports = Array.isArray(bundle.reports) ? bundle.reports : [];
  const projects = reports.map((report) => createProjectSummary(report, bundle));

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(projects, null, 2) + '\n', 'utf8');

  console.log(`Wrote ${projects.length} schema-based projects to ${outputPath}`);
}

main();