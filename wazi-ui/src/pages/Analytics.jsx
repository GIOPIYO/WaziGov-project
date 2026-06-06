import React, { useEffect, useState } from 'react';

export default function Analytics() {
  const [ranking, setRanking] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [rawRowsCount, setRawRowsCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isActive = true;
    async function load() {
      try {
        const r = await fetch('/data/analytics/county_budget_ranking.json');
        const rankingJson = await r.json();
        const a = await fetch('/data/analytics/validation_alerts.json');
        const alertsJson = await a.json();
        const raw = await fetch('/data/analytics/raw_extracted_rows.json');
        const rawJson = await raw.json();

        if (!isActive) return;
        setRanking(rankingJson.ranking || []);
        setAlerts(alertsJson.alerts || []);
        setRawRowsCount((rawJson.rows || []).length || 0);
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
                    <td style={{ textAlign: 'right' }}>{formatKES(r.total_ksh)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ width: 360 }}>
            <h4 style={{ marginTop: 0 }}>Bar chart (top 10)</h4>
            <div>
              {ranking.slice(0, 10).map((r) => {
                const max = ranking.length ? ranking[0].total_ksh : 1;
                const pct = Math.round((r.total_ksh / (max || 1)) * 100);
                return (
                  <div key={r.rank} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <div style={{ width: 36, textAlign: 'right', fontSize: 12 }}>{r.rank}</div>
                    <div style={{ flex: 1, background: '#f1f3f5', height: 20, borderRadius: 6, overflow: 'hidden' }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg,#2563eb,#06b6d4)' }} />
                    </div>
                    <div style={{ width: 90, textAlign: 'right', fontSize: 12 }}>{formatKES(r.total_ksh)}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      <div className="material-card" style={{ padding: 16, marginTop: 16 }}>
        <h3>Validation Alerts</h3>
        <p>Total tables with warnings: <strong>{alerts.length}</strong>. Raw rows inspected: <strong>{rawRowsCount}</strong>.</p>
        {alerts.slice(0, 20).map((a, idx) => (
          <div key={idx} style={{ padding: 8, borderBottom: '1px solid var(--border-light)' }}>
            <div style={{ fontSize: 13 }}><strong>{a.report_id}</strong> — {a.table_id}</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{a.source_file}</div>
            <ul style={{ marginTop: 6 }}>
              {a.warnings.map((w, i) => <li key={i} style={{ fontSize: 13 }}>{w}</li>)}
            </ul>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 12 }}>
        <a href="/data/analytics/county_budget_ranking.csv" className="btn-proposal" target="_blank">Download ranking CSV</a>
        <a href="/data/analytics/raw_extracted_rows.json" style={{ marginLeft: 12 }} className="btn-proposal" target="_blank">Download raw rows</a>
      </div>
    </div>
  );
}
