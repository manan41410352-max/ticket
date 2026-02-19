import React, { useEffect, useRef, useState } from 'react';

const DEFAULT_CATEGORY = 'general';
const DEFAULT_PRIORITY = 'low';

function normalizeSuggestion(value, fallback) {
  return value || fallback;
}

export default function TicketForm({ onSubmitTicket, onClassify }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState(DEFAULT_CATEGORY);
  const [priority, setPriority] = useState(DEFAULT_PRIORITY);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('muted');
  const debounceRef = useRef(null);

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (!description.trim()) {
      setCategory(DEFAULT_CATEGORY);
      setPriority(DEFAULT_PRIORITY);
      setMessage('');
      setMessageType('muted');
      setIsAnalyzing(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setIsAnalyzing(true);
      setMessage('Analyzing...');
      setMessageType('muted');

      try {
        const suggestion = await onClassify(description.trim());
        const suggestedCategory = normalizeSuggestion(
          suggestion?.suggested_category,
          DEFAULT_CATEGORY
        );
        const suggestedPriority = normalizeSuggestion(
          suggestion?.suggested_priority,
          DEFAULT_PRIORITY
        );

        setCategory(suggestedCategory);
        setPriority(suggestedPriority);

        if (!suggestion?.suggested_category || !suggestion?.suggested_priority) {
          setMessage('AI suggestion unavailable');
          setMessageType('muted');
        } else {
          setMessage('AI Suggested');
          setMessageType('success');
        }
      } catch (_error) {
        setCategory(DEFAULT_CATEGORY);
        setPriority(DEFAULT_PRIORITY);
        setMessage('AI suggestion unavailable');
        setMessageType('muted');
      } finally {
        setIsAnalyzing(false);
      }
    }, 500);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [description, onClassify]);

  async function handleSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);

    try {
      await onSubmitTicket({
        title: title.trim(),
        description: description.trim(),
        category,
        priority,
      });

      setTitle('');
      setDescription('');
      setCategory(DEFAULT_CATEGORY);
      setPriority(DEFAULT_PRIORITY);
      setMessage('Ticket created successfully.');
      setMessageType('success');
    } catch (error) {
      setMessage(error.message || 'Unable to create ticket.');
      setMessageType('error');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="card">
      <h2>Create Ticket</h2>
      <form className="stack" onSubmit={handleSubmit}>
        <label className="field">
          <span>Title</span>
          <input
            type="text"
            maxLength={200}
            required
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Short summary of the issue"
          />
        </label>

        <label className="field">
          <span>Description</span>
          <textarea
            required
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Describe the issue in detail"
          />
        </label>

        <div className="suggestion-header">
          <strong>AI Suggestions</strong>
          <span className={`badge ${messageType}`}>
            {isAnalyzing ? 'Analyzing...' : message || 'Waiting for description'}
          </span>
        </div>

        <div className="ai-output">
          <p>
            <span className="muted">Category:</span> <strong>{category}</strong>
          </p>
          <p>
            <span className="muted">Priority:</span> <strong>{priority}</strong>
          </p>
        </div>

        <button className="btn" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Submitting...' : 'Create Ticket'}
        </button>
      </form>
    </section>
  );
}
