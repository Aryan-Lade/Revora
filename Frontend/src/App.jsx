import { BrowserRouter as Router, Routes, Route, Navigate, NavLink } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import RecoveryQueuePage from './pages/RecoveryQueuePage';
import RecoveryCasePage from './pages/RecoveryCasePage';
import PromisesPage from './pages/PromisesPage';
import AnalyticsPage from './pages/AnalyticsPage';
import VoicePage from './pages/VoicePage';
import GatewaysPage from './pages/GatewaysPage';
import './App.css';

const NAV_LINKS = [
  { to: '/dashboard',      label: 'Dashboard',       icon: '📊' },
  { to: '/recovery-queue', label: 'Recovery Queue',   icon: '⚡' },
  { to: '/promises',       label: 'Promises',         icon: '🤝' },
  { to: '/analytics',      label: 'Analytics',        icon: '📈' },
  { to: '/voice',          label: 'Voice AI',         icon: '🎙️' },
  { to: '/gateways',       label: 'Gateways',         icon: '🔗' },
];

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="navbar-brand">
            <span>⚡</span> Revora
          </div>
          <ul className="navbar-menu">
            {NAV_LINKS.map(({ to, label, icon }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  className={({ isActive }) =>
                    isActive ? 'nav-link nav-link-active' : 'nav-link'
                  }
                >
                  <span style={{ marginRight: '0.3rem', fontSize: '0.85em' }}>{icon}</span>
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/"                    element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard"           element={<DashboardPage />} />
            <Route path="/recovery-queue"      element={<RecoveryQueuePage />} />
            <Route path="/recovery-case/:id"   element={<RecoveryCasePage />} />
            <Route path="/promises"            element={<PromisesPage />} />
            <Route path="/analytics"           element={<AnalyticsPage />} />
            <Route path="/voice"               element={<VoicePage />} />
            <Route path="/gateways"            element={<GatewaysPage />} />
            <Route path="*"                    element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
