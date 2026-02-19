import React from 'react';

const CATEGORY_OPTIONS = ['billing', 'technical', 'account', 'general'];
const PRIORITY_OPTIONS = ['low', 'medium', 'high', 'critical'];
const STATUS_OPTIONS = ['open', 'in_progress', 'resolved', 'closed'];

function truncate(text, max = 120) {
  if (!text) {
    return '';
  }
  if (text.length <= max) {
    return text;
  }
  return `${text.slice(0, max)}...`;
}

function formatDate(value) {
  if (!value) {
    return '-';
  }
  return new Date(value).toLocaleString();
}

export default function TicketList({
  tickets,
  filters,
  onFilterChange,
  onSearchChange,
  onStatusChange,
  loading,
  error,
}) {
  return (
    <section className="card">
      <h2>Tickets</h2>

      <div className="controls">
        <input
          type="search"
          value={filters.search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search title or description"
        />
        <select
          value={filters.category}
          onChange={(event) => onFilterChange('category', event.target.value)}
        >
          <option value="">All categories</option>
          {CATEGORY_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <select
          value={filters.priority}
          onChange={(event) => onFilterChange('priority', event.target.value)}
        >
          <option value="">All priorities</option>
          {PRIORITY_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <select
          value={filters.status}
          onChange={(event) => onFilterChange('status', event.target.value)}
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      {loading ? <p className="muted">Loading tickets...</p> : null}
      {error ? <p className="inline-error">{error}</p> : null}

      <div className="ticket-list">
        {tickets.map((ticket) => (
          <article key={ticket.id} className="ticket-item">
            <header className="ticket-header">
              <h3>{ticket.title}</h3>
              <time>{formatDate(ticket.created_at)}</time>
            </header>
            <p className="ticket-description">{truncate(ticket.description)}</p>
            <div className="meta-grid">
              <p>
                <span className="muted">Category:</span> <strong>{ticket.category}</strong>
              </p>
              <p>
                <span className="muted">Priority:</span> <strong>{ticket.priority}</strong>
              </p>
              <label className="status-select">
                <span>Status</span>
                <select
                  value={ticket.status}
                  onChange={(event) => onStatusChange(ticket.id, event.target.value)}
                >
                  {STATUS_OPTIONS.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </article>
        ))}

        {!loading && !tickets.length ? (
          <p className="muted">No tickets found for current filters.</p>
        ) : null}
      </div>
    </section>
  );
}
