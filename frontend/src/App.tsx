/**
 * App root — routing, layout shell, Dark/Light theme toggle, and Lucide icons.
 */

import React from 'react';
import { BrowserRouter, Routes, Route, NavLink, Link } from 'react-router-dom';
import {
  Server,
  LayoutDashboard,
  LineChart,
  AlertTriangle,
  ExternalLink,
  Sun,
  Moon,
} from 'lucide-react';
import { Dashboard } from './pages/Dashboard';
import { Metrics } from './pages/Metrics';
import { Incidents } from './pages/Incidents';
import { IncidentDetail } from './pages/IncidentDetail';
import { ThemeProvider, useTheme } from './context/ThemeContext';

const Nav: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <nav className="sidebar" role="navigation" aria-label="Main navigation">
      <div className="sidebar-brand">
        <Link to="/" className="brand-link" id="brand-logo">
          <Server className="brand-icon" size={22} color="var(--color-brand)" />
          <div className="brand-text">
            <span className="brand-name">EC2 Monitor</span>
            <span className="brand-tagline">Incident Analysis</span>
          </div>
        </Link>
      </div>

      <ul className="nav-list">
        <li>
          <NavLink
            to="/"
            end
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            id="nav-dashboard"
          >
            <LayoutDashboard size={17} className="nav-icon" />
            Dashboard
          </NavLink>
        </li>
        <li>
          <NavLink
            to="/metrics"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            id="nav-metrics"
          >
            <LineChart size={17} className="nav-icon" />
            Metrics
          </NavLink>
        </li>
        <li>
          <NavLink
            to="/incidents"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            id="nav-incidents"
          >
            <AlertTriangle size={17} className="nav-icon" />
            Incidents
          </NavLink>
        </li>
      </ul>

      <div className="sidebar-footer">
        <button
          type="button"
          className="theme-toggle-btn"
          id="theme-toggle-btn"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
        >
          {theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}
          <span>{theme === 'light' ? 'Dark Mode' : 'Light Mode'}</span>
        </button>

        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="sidebar-footer-link"
          id="api-docs-link"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
        >
          <span>API Docs</span>
          <ExternalLink size={12} />
        </a>
      </div>
    </nav>
  );
};

const App: React.FC = () => (
  <ThemeProvider>
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
  </ThemeProvider>
);

export default App;
