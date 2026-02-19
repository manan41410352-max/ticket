import React, { useCallback, useEffect, useMemo, useState } from 'react';

import { fetchStats, fetchTickets, updateTicketStatus } from '../api';
import StatsDashboard from '../components/StatsDashboard';
import TicketList from '../components/TicketList';

const DEFAULT_FILTERS = {
  category: '',
  priority: '',
  status: '',
  search: '',
};

export default function AdminPage() {
  const [stats, setStats] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsError, setStatsError] = useState('');
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [ticketsError, setTicketsError] = useState('');
  const [filters, setFilters] = useState(DEFAULT_FILTERS);

  const queryFilters = useMemo(
    () => ({
      ...filters,
      ordering: '-created_at',
    }),
    [filters]
  );

  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    setStatsError('');
    try {
      const data = await fetchStats();
      setStats(data);
    } catch (error) {
      setStatsError(error.message || 'Unable to load stats.');
    } finally {
      setStatsLoading(false);
    }
  }, []);

  const loadTickets = useCallback(async () => {
    setTicketsLoading(true);
    setTicketsError('');
    try {
      const data = await fetchTickets(queryFilters);
      const items = Array.isArray(data) ? data : data.results || [];
      setTickets(items);
    } catch (error) {
      setTicketsError(error.message || 'Unable to load tickets.');
    } finally {
      setTicketsLoading(false);
    }
  }, [queryFilters]);

  const refreshAdminData = useCallback(async () => {
    await Promise.all([loadTickets(), loadStats()]);
  }, [loadStats, loadTickets]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadTickets();
    }, 250);
    return () => clearTimeout(timer);
  }, [loadTickets]);

  useEffect(() => {
    function handleTicketCreated() {
      refreshAdminData();
    }

    window.addEventListener('ticket-created', handleTicketCreated);
    return () => {
      window.removeEventListener('ticket-created', handleTicketCreated);
    };
  }, [refreshAdminData]);

  const handleFilterChange = useCallback((key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSearchChange = useCallback((value) => {
    setFilters((prev) => ({ ...prev, search: value }));
  }, []);

  const handleStatusChange = useCallback(
    async (ticketId, status) => {
      try {
        await updateTicketStatus(ticketId, status);
        await refreshAdminData();
      } catch (error) {
        setTicketsError(error.message || 'Unable to update ticket status.');
      }
    },
    [refreshAdminData]
  );

  return (
    <section className="admin-page">
      <div className="admin-layout">
        <StatsDashboard stats={stats} loading={statsLoading} error={statsError} />

        <TicketList
          tickets={tickets}
          filters={filters}
          onFilterChange={handleFilterChange}
          onSearchChange={handleSearchChange}
          onStatusChange={handleStatusChange}
          loading={ticketsLoading}
          error={ticketsError}
        />
      </div>
    </section>
  );
}
