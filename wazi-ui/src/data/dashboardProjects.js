function normalizeCountyName(name) {
  return String(name || '')
    .replace(/\bCounty\b/gi, '')
    .replace(/\bCity\b/gi, '')
    .replace(/\bSub-?County\b/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function toNumber(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === 'string') {
    const cleaned = value.replace(/[^\d.-]/g, '');
    const parsed = Number(cleaned);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  return 0;
}

function slugify(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'county';
}

function getSectionData(projectData, sectionKey) {
  return projectData?.financial_performance?.[sectionKey]?.data || [];
}

function buildCountyLookup(rows, valueKey, labelKey = 'county') {
  const lookup = new Map();

  rows.forEach((row) => {
    const county = normalizeCountyName(row?.[labelKey]);
    if (!county) {
      return;
    }

    lookup.set(county.toLowerCase(), toNumber(row?.[valueKey]));
  });

  return lookup;
}

function buildIssueSummary(county, delayedCount, stalledCount, budget, spent) {
  const issues = [];

  if (stalledCount > 0) {
    issues.push({
      id: `${slugify(county)}-stalled`,
      issue: 'Stalled project portfolio',
      amount: null,
      severity: 'High',
      description: `${county} County has ${stalledCount} stalled or abandoned projects reported in Appendix 27.`,
    });
  }

  if (delayedCount > 0) {
    issues.push({
      id: `${slugify(county)}-delayed`,
      issue: 'Delayed project portfolio',
      amount: null,
      severity: 'Medium',
      description: `${county} County has ${delayedCount} delayed projects reported in Appendix 26.`,
    });
  }

  if (spent > budget && budget > 0) {
    issues.push({
      id: `${slugify(county)}-overspend`,
      issue: 'Expenditure above budget',
      amount: spent - budget,
      severity: 'High',
      description: `${county} County expenditure exceeds the approved budget by KES ${(spent - budget).toLocaleString()}.`,
    });
  }

  return issues;
}

function buildStatus(progress, delayedCount, stalledCount) {
  if (stalledCount > 0) {
    return 'Suspended';
  }

  if (delayedCount > 0) {
    return 'In Progress';
  }

  if (progress >= 95) {
    return 'Complete';
  }

  return progress >= 70 ? 'In Progress' : 'Planning';
}

function buildOpinion(progress, delayedCount, stalledCount) {
  if (stalledCount > 0) {
    return 'Adverse';
  }

  if (delayedCount > 0) {
    return 'Qualified';
  }

  return progress >= 95 ? 'Clean' : 'Qualified';
}

export function buildDashboardProjects(projectData) {
  const budgetRows = getSectionData(projectData, 'budget_summary');
  const expenditureRows = getSectionData(projectData, 'county_expenditure');
  const revenueRows = getSectionData(projectData, 'actual_revenue');
  const ownSourceRows = getSectionData(projectData, 'own_source_revenue');
  const delayedRows = getSectionData(projectData, 'delayed_projects_county_executives');
  const stalledRows = getSectionData(projectData, 'stalled_abandoned_projects_county_executives');

  const budgetLookup = new Map();
  budgetRows.forEach((row) => {
    const county = normalizeCountyName(row?.county);
    if (!county) return;
    budgetLookup.set(county.toLowerCase(), {
      county,
      budget: toNumber(row?.total_budget_kshs),
    });
  });

  const expenditureLookup = buildCountyLookup(expenditureRows, 'total_expenditure_kshs');
  const revenueLookup = buildCountyLookup(revenueRows, 'total_revenue_kshs');
  const ownSourceLookup = buildCountyLookup(ownSourceRows, 'actual_kshs');

  const delayedLookup = new Map();
  delayedRows.forEach((row) => {
    const county = normalizeCountyName(row?.county);
    if (!county) return;
    const key = county.toLowerCase();
    const current = delayedLookup.get(key) || { delayed: 0, stalled: 0 };
    current.delayed += 1;
    delayedLookup.set(key, current);
  });

  stalledRows.forEach((row) => {
    const county = normalizeCountyName(row?.county);
    if (!county) return;
    const key = county.toLowerCase();
    const current = delayedLookup.get(key) || { delayed: 0, stalled: 0 };
    current.stalled += 1;
    delayedLookup.set(key, current);
  });

  const countyNames = Array.from(
    new Set([
      ...budgetRows.map((row) => normalizeCountyName(row?.county)),
      ...expenditureRows.map((row) => normalizeCountyName(row?.county)),
      ...revenueRows.map((row) => normalizeCountyName(row?.county)),
      ...ownSourceRows.map((row) => normalizeCountyName(row?.county)),
    ].filter(Boolean)),
  ).sort((left, right) => left.localeCompare(right));

  return countyNames.map((county) => {
    const key = county.toLowerCase();
    const budget = budgetLookup.get(key)?.budget || 0;
    const spent = expenditureLookup.get(key) || 0;
    const revenue = revenueLookup.get(key) || 0;
    const ownSource = ownSourceLookup.get(key) || 0;
    const projectFlags = delayedLookup.get(key) || { delayed: 0, stalled: 0 };
    const progress = budget > 0 ? Math.min(100, Math.round((spent / budget) * 100)) : 0;
    const status = buildStatus(progress, projectFlags.delayed, projectFlags.stalled);
    const opinion = buildOpinion(progress, projectFlags.delayed, projectFlags.stalled);

    return {
      id: `county-${slugify(county)}`,
      title: `${county} County Accountability Snapshot`,
      sector: 'Infrastructure',
      county,
      ward: 'Countywide',
      budget,
      spent,
      status,
      progress,
      startDate: '2023-07-01',
      expectedEndDate: '2024-06-30',
      oagOpinion: opinion,
      implementationAgency: `${county} County Government`,
      auditorGeneralQueries: buildIssueSummary(county, projectFlags.delayed, projectFlags.stalled, budget, spent),
      oagReportText: `${county} County summary derived from the FY 2023-2024 COB/OAG bundle.`,
      aiSummary: `${county} County shows ${projectFlags.delayed} delayed and ${projectFlags.stalled} stalled project indicators, with budget absorption at ${progress}%.`,
      milestones: [
        { date: '2023-07-01', label: 'FY 2023-2024 Baseline', status: 'completed' },
        { date: '2024-06-30', label: 'Audit Year End', status: 'completed' },
      ],
      citizenReports: [],
      metadata: {
        revenue,
        ownSource,
        delayedProjects: projectFlags.delayed,
        stalledProjects: projectFlags.stalled,
      },
    };
  });
}

export function buildDashboardFilterOptions(projects) {
  const counties = Array.from(new Set(projects.map((project) => project.county).filter(Boolean))).sort((left, right) => left.localeCompare(right));
  const sectors = Array.from(new Set(projects.map((project) => project.sector).filter(Boolean))).sort((left, right) => left.localeCompare(right));
  const opinions = Array.from(new Set(projects.map((project) => project.oagOpinion).filter(Boolean))).sort((left, right) => left.localeCompare(right));
  const statuses = Array.from(new Set(projects.map((project) => project.status).filter(Boolean))).sort((left, right) => left.localeCompare(right));

  return { counties, sectors, opinions, statuses };
}