/**
 * App root — routing and layout shell.
 */

import React from 'react';
import { BrowserRouter, Routes, Route, NavLink, Link } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { Metrics } from './pages/Metrics';
import { Incidents } from './pages/Incidents';
import { IncidentDetail } from './pages/IncidentDetail';

const Nav: React.FC = () => (
  <nav className="sidebar" role="navigation" aria-label="Main navigation">
    <div className="sidebar-brand">
      <Link to="/" className="brand-link" id="brand-logo">
        <span className="brand-icon">📡</span>
        <div className="brand-text">
          <span className="brand-name">EC2 Monitor</span>
          <span className="brand-tagline">Incident Analysis</span>
        </div>
      </Link>
    </div>

    <ul className="nav-list">
      <li>
        <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} id="nav-dashboard">
          <span className="nav-icon">◉</span>
          Dashboard
        </NavLink>
      </li>
      <li>
        <NavLink to="/metrics" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} id="nav-metrics">
          <span className="nav-icon">📈</span>
          Metrics
        </NavLink>
      </li>
      <li>
        <NavLink to="/incidents" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} id="nav-incidents">
          <span className="nav-icon">⚠</span>
          Incidents
        </NavLink>
      </li>
    </ul>

    <div className="sidebar-footer">
      <a
        href="http://localhost:8000/docs"
        target="_blank"
        rel="noopener noreferrer"
        className="sidebar-footer-link"
        id="api-docs-link"
      >
        API Docs ↗
      </a>
    </div>
  </nav>
);

const App: React.FC = () => (
  <BrowserRouter>
    <div className="app-layout">
      <Nav />
      <div className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/metrics" element={<Metrics />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
        </Routes>
      </div>
    </div>
  </BrowserRouter>
);

export default App;
