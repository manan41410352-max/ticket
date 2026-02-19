const API_BASE = '/api';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function fetchStats() {
  return request('/tickets/stats/');
}

export function fetchTickets(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, value);
    }
  });

  const suffix = query.toString() ? `?${query.toString()}` : '';
  return request(`/tickets/${suffix}`);
}

export function createTicket(payload) {
  return request('/tickets/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function classifyTicket(description) {
  return request('/tickets/classify/', {
    method: 'POST',
    body: JSON.stringify({ description }),
  });
}

export function updateTicketStatus(ticketId, status) {
  return request(`/tickets/${ticketId}/`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}
