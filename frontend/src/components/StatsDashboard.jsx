import React from 'react';

function formatBreakdown(breakdown) {
  const entries = Object.entries(breakdown || {});
  if (!entries.length) {
    return '-';
  }
  return entries.map(([key, value]) => `${key}: ${value}`).join(', ');
}

export default function StatsDashboard({ stats, loading, error }) {
  return (
    <section className="card">
      <h2>Stats Dashboard</h2>
      {loading ? <p className="muted">Loading stats...</p> : null}
      {error ? <p className="inline-error">{error}</p> : null}

      <div className="stats-grid">
        <div className="metric">
          <span>Total Tickets</span>
          <strong>{stats?.total_tickets ?? '-'}</strong>
        </div>
        <div className="metric">
          <span>Open Tickets</span>
          <strong>{stats?.open_tickets ?? '-'}</strong>
        </div>
        <div className="metric">
          <span>Avg Tickets/Day</span>
          <strong>{stats?.avg_tickets_per_day ?? '-'}</strong>
        </div>
      </div>

      <p className="muted breakdown-line">
        Priority Breakdown: {formatBreakdown(stats?.priority_breakdown)}
      </p>
      <p className="muted breakdown-line">
        Category Breakdown: {formatBreakdown(stats?.category_breakdown)}
      </p>
    </section>
  );
}
