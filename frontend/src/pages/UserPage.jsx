import React, { useCallback } from 'react';

import { classifyTicket, createTicket } from '../api';
import TicketForm from '../components/TicketForm';

export default function UserPage() {
  const handleClassify = useCallback(async (description) => {
    if (!description.trim()) {
      return { suggested_category: 'general', suggested_priority: 'low' };
    }
    return classifyTicket(description);
  }, []);

  const handleSubmitTicket = useCallback(async (payload) => {
    await createTicket(payload);
    window.dispatchEvent(new Event('ticket-created'));
  }, []);

  return (
    <section className="user-page">
      <div className="user-card-wrap">
        <TicketForm onSubmitTicket={handleSubmitTicket} onClassify={handleClassify} />
      </div>
    </section>
  );
}
