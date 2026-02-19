import React from 'react';
import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom';

import AdminPage from './pages/AdminPage';
import UserPage from './pages/UserPage';

export default function App() {
  return (
    <BrowserRouter>
      <main className="app-shell">
        <header className="top-bar">
          <h1>Support Ticket System</h1>
          <nav className="top-nav">
            <Link to="/">User</Link>
            <Link to="/admin">Admin</Link>
          </nav>
        </header>

        <Routes>
          <Route path="/" element={<UserPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
