import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import RecoveryQueuePage from './pages/RecoveryQueuePage';
import RecoveryCasePage from './pages/RecoveryCasePage';
import PromisesPage from './pages/PromisesPage';
import AnalyticsPage from './pages/AnalyticsPage';
import VoicePage from './pages/VoicePage';
import GatewaysPage from './pages/GatewaysPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="navbar-brand">
            <h1>Revora</h1>
          </div>
          <ul className="navbar-menu">
            <li><a href="/dashboard">Dashboard</a></li>
            <li><a href="/recovery-queue">Recovery Queue</a></li>
            <li><a href="/promises">Promises to Pay</a></li>
            <li><a href="/analytics">Analytics</a></li>
            <li><a href="/voice">Voice AI</a></li>
            <li><a href="/gateways">Gateways</a></li>
          </ul>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/recovery-queue" element={<RecoveryQueuePage />} />
            <Route path="/recovery-case/:id" element={<RecoveryCasePage />} />
            <Route path="/promises" element={<PromisesPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/voice" element={<VoicePage />} />
            <Route path="/gateways" element={<GatewaysPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;