const PRIMARY_BUNDLE_URL = '/outputs/cob_oag_2023_2024_full.json';
const FALLBACK_BUNDLE_URL = '/samples/sample_cob_oag.json';

function normalizeFinding(finding, type) {
  return {
    report_id: finding.report_id || finding.id || `${type}-finding`,
    fiscal_year: finding.fiscal_year || finding.fiscalYear || null,
    title: finding.title || (type === 'cob' ? 'COB finding' : 'OAG finding'),
    summary: finding.summary || '',
    recommendation: finding.recommendation || null,
    amount: typeof finding.amount === 'number' ? finding.amount : null,
    link: finding.link || null,
  };
}

function normalizeReport(report, index, bundleYear) {
  const source = report.document || report;
  const cobFindings = Array.isArray(source.cob_findings)
    ? source.cob_findings.map((finding) => normalizeFinding(finding, 'cob'))
    : [];
  const oagFindings = Array.isArray(source.oag_findings)
    ? source.oag_findings.map((finding) => normalizeFinding(finding, 'oag'))
    : [];

  return {
    report_id: report.report_id || source.project_id || `report-${index + 1}`,
    title: report.title || source.title || 'Public accountability report',
    summary: report.summary || source.summary || '',
    fiscal_year: report.fiscal_year || source.fiscal_year || bundleYear || '2023-2024',
    institution: report.institution || source.institution || 'COB / OAG',
    report_family: report.report_family || source.report_family || 'Citizen summary',
    source_file: report.source_file || null,
    artifact_dir: report.artifact_dir || null,
    cv_output_file: report.cv_output_file || null,
    page_count: Number.isFinite(report.page_count) ? report.page_count : 0,
    table_count: Number.isFinite(report.table_count) ? report.table_count : 0,
    overall_status: report.overall_status || source.overall_status || 'Partial',
    last_updated: report.last_updated || source.last_updated || null,
    document: report.document || null,
    cob_findings: cobFindings,
    oag_findings: oagFindings,
  };
}

function normalizeBundle(rawBundle) {
  const reportsSource = Array.isArray(rawBundle.reports) && rawBundle.reports.length > 0
    ? rawBundle.reports
    : [rawBundle];

  return {
    generated_at: rawBundle.generated_at || rawBundle.last_updated || new Date().toISOString(),
    fiscal_year: rawBundle.fiscal_year || '2023-2024',
    report_count: rawBundle.report_count || reportsSource.length,
    selection_mode: rawBundle.selection_mode || 'auto',
    reports: reportsSource.map((report, index) => normalizeReport(report, index, rawBundle.fiscal_year)),
  };
}

async function fetchBundle(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Failed to load ${url} (${response.status})`);
  }
  return response.json();
}

export async function loadCobOagBundle() {
  try {
    const primaryBundle = await fetchBundle(PRIMARY_BUNDLE_URL);
    return normalizeBundle(primaryBundle);
  } catch (primaryError) {
    try {
      const fallbackBundle = await fetchBundle(FALLBACK_BUNDLE_URL);
      return normalizeBundle({
        fiscal_year: '2023-2024',
        report_count: 1,
        selection_mode: 'fallback-sample',
        reports: [fallbackBundle],
      });
    } catch (fallbackError) {
      throw new Error(`${primaryError.message}; fallback also failed: ${fallbackError.message}`);
    }
  }
}

export { PRIMARY_BUNDLE_URL };