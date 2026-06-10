import React, { useEffect, useState } from 'react';

export default function Analytics() {
  const [ranking, setRanking] = useState([]);
  const [scorecard, setScorecard] = useState([]);
  const [trends, setTrends] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isActive = true;
    async function load() {
      try {
        const r = await fetch('/data/analytics/county_budget_ranking.json');
        const rankingJson = await r.json();
        const s = await fetch('/data/analytics/transparency_scorecard.json');
        const scorecardJson = await s.json();
        const t = await fetch('/data/analytics/county_trends.json');
        const trendsJson = await t.json();

        if (!isActive) return;
        setRanking(rankingJson.budget_ranking || []);
        setScorecard(scorecardJson.documents || []);
        setTrends(trendsJson.county_trends || []);
      } catch (e) {
        console.error('Failed to load analytics', e);
      } finally {
        if (isActive) setLoading(false);
      }
    }
    load();
    return () => { isActive = false; };
  }, []);

  const formatKES = (v) => {
    if (v == null) return '—';
    const n = Number(v);
    return n.toLocaleString('en-KE');
  };

  if (loading) return <div className="material-card"><p>Loading analytics…</p></div>;

  return (
    <div>
      <h2>Budget Analytics</h2>

      <div className="material-card" style={{ padding: 16 }}>
        <h3>County Budget Ranking</h3>
        <p>Top counties by aggregated approved budgets (extracted from CV pipeline)</p>
        <div style={{ display: 'flex', gap: 12 }}>
          <div style={{ flex: 1 }}>
            <table className="simple-table" style={{ width: '100%' }}>
              <thead>
                <tr><th>Rank</th><th>County</th><th style={{ textAlign: 'right' }}>Total (KSh)</th></tr>
              </thead>
              <tbody>
                {ranking.slice(0, 20).map((r) => (
                  <tr key={r.rank}>
                    <td>{r.rank}</td>
                    <td>{r.county}</td>
                    <td style={{ textAlign: 'right' }}>{formatKES(r.total_allocation_kshs)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ width: 360 }}>
            <h4 style={{ marginTop: 0 }}>Bar chart (top 10)</h4>
            <div>
              {ranking.slice(0, 10).map((r) => {
                const max = ranking.length ? ranking[0].total_allocation_kshs : 1;
                const pct = Math.round((r.total_allocation_kshs / (max || 1)) * 100);
                return (
                  <div key={r.rank} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <div style={{ width: 36, textAlign: 'right', fontSize: 12 }}>{r.rank}</div>
                    <div style={{ flex: 1, background: '#f1f3f5', height: 20, borderRadius: 6, overflow: 'hidden' }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg,#2563eb,#06b6d4)' }} />
                    </div>
                    <div style={{ width: 90, textAlign: 'right', fontSize: 12 }}>{formatKES(r.total_allocation_kshs)}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <div className="material-card" style={{ padding: 16, marginTop: 16 }}>
        <h3>Absorption Trends</h3>
        <p>Recent budget absorption performance (Actual / Allocation) by county and fiscal year.</p>
        <div className="projects-table-wrap">
          <table className="simple-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>County</th>
                <th>FY</th>
                <th style={{ textAlign: 'right' }}>Absorption</th>
                <th style={{ textAlign: 'right' }}>Actual (KSh)</th>
              </tr>
            </thead>
            <tbody>
              {trends.slice(0, 20).map((t, idx) => (
                <tr key={idx}>
                  <td>{t.county}</td>
                  <td>{t.fiscal_year}</td>
                  <td style={{ textAlign: 'right' }}>{t.absorption_ratio ? (t.absorption_ratio * 100).toFixed(1) + '%' : 'N/A'}</td>
                  <td style={{ textAlign: 'right' }}>{formatKES(t.actual_kshs)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="material-card" style={{ padding: 16, marginTop: 16 }}>
        <h3>Transparency Scorecard (Documents)</h3>
        <p>Document-level data quality metrics based on extraction warnings.</p>
        {scorecard.slice(0, 20).map((doc, idx) => (
          <div key={idx} style={{ padding: 8, borderBottom: '1px solid var(--border-light)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: 13 }}><strong>{doc.report_id}</strong> ({doc.fiscal_year})</div>
              <div style={{ fontSize: 12, color: doc.warning_table_rate > 0.5 ? '#ef4444' : 'var(--text-secondary)' }}>
                Error Rate: {(doc.warning_table_rate * 100).toFixed(1)}%
              </div>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{doc.source_file}</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>
              Tables: {doc.table_count} | Warnings: {doc.warnings_total}
            </div>
            {doc.warning_type_counts?.length > 0 && (
              <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {doc.warning_type_counts.slice(0, 3).map((w, i) => (
                  <span key={i} className="badge" style={{ fontSize: 10 }}>{w.warning}: {w.count}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 12 }}>
        <a href="/data/analytics/county_budget_ranking.csv" className="btn-proposal" target="_blank">Download ranking CSV</a>
        <a href="/data/analytics/county_trends.json" style={{ marginLeft: 12 }} className="btn-proposal" target="_blank">Download trends JSON</a>
        <a href="/data/analytics/transparency_scorecard.json" style={{ marginLeft: 12 }} className="btn-proposal" target="_blank">Download scorecard</a>
      </div>
    </div>
  );
}
