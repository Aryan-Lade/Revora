import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

const STATUS_STYLE = {
  HEALTHY:     { background: 'rgba(16,185,129,0.15)',  color: '#34d399', border: '1px solid rgba(16,185,129,0.3)' },
  DEGRADED:    { background: 'rgba(245,158,11,0.15)',  color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)' },
  UNAVAILABLE: { background: 'rgba(239,68,68,0.15)',   color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' },
};

const Badge = ({ label }) => {
  const s = STATUS_STYLE[label] || { background: 'rgba(100,116,139,0.15)', color: '#94a3b8', border: '1px solid rgba(100,116,139,0.3)' };
  return <span style={{ ...s, padding: '0.2rem 0.65rem', borderRadius: '2rem', fontSize: '0.7rem', fontWeight: 600 }}>{label}</span>;
};

const th = { padding: '0.75rem 1rem', fontSize: '0.7rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', whiteSpace: 'nowrap' };

const StatCard = ({ label, value, color }) => (
  <div style={{
    background: 'rgba(15,23,42,0.7)', border: `1px solid ${color}33`,
    borderRadius: '0.875rem', padding: '1rem', textAlign: 'center',
  }}>
    <div style={{ fontSize: '0.68rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '0.4rem' }}>{label}</div>
    <div style={{ fontSize: '2rem', fontWeight: 800, color }}>{value}</div>
  </div>
);

const GatewaysPage = () => {
  const [refetchKey, setRefetchKey] = useState(0);
  const { data: gateways, loading, error } = useApi('/api/gateways/', refetchKey);
  const [toggling, setToggling] = useState(null);
  const [toggleMsg, setToggleMsg] = useState(null);

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ width: 44, height: 44, border: '3px solid rgba(99,102,241,0.15)', borderTopColor: '#818cf8', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 1rem' }} />
        <p style={{ color: '#475569', fontSize: '0.875rem' }}>Loading gateways...</p>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  if (error) return (
    <div style={{ padding: '1.5rem', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: '0.875rem', color: '#f87171' }}>
      Error: {error}
    </div>
  );

  const list = Array.isArray(gateways) ? gateways : [];
  const healthy  = list.filter(g => g.status === 'HEALTHY').length;
  const degraded = list.filter(g => g.status === 'DEGRADED').length;
  const unavail  = list.filter(g => g.status === 'UNAVAILABLE').length;

  const handleToggle = async (gateway) => {
    setToggling(gateway.id); setToggleMsg(null);
    try {
      const res = await fetch(`${API_BASE}/api/gateways/${gateway.id}/toggle`, { method: 'POST' });
      const data = await res.json();
      setToggleMsg(`${data.name} is now ${data.status}`);
      setRefetchKey(k => k + 1);
    } catch (e) {
      setToggleMsg('Toggle failed: ' + e.message);
    } finally { setToggling(null); }
  };

  return (
    <div>
      <div style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.02em', marginBottom: '0.2rem' }}>Gateway Providers</h1>
        <p style={{ fontSize: '0.825rem', color: '#475569' }}>Payment gateway health & adaptive failover management</p>
      </div>

      {toggleMsg && (
        <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.25)', borderRadius: '0.75rem', fontSize: '0.825rem', color: '#a5b4fc' }}>
          ✓ {toggleMsg}
        </div>
      )}

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.875rem', marginBottom: '1.5rem' }}>
        <StatCard label="Total Gateways" value={list.length}  color="#94a3b8" />
        <StatCard label="Healthy"        value={healthy}       color="#34d399" />
        <StatCard label="Degraded"       value={degraded}      color="#fbbf24" />
        <StatCard label="Unavailable"    value={unavail}       color="#f87171" />
      </div>

      {unavail > 0 && healthy > 0 && (
        <div style={{ marginBottom: '1rem', padding: '0.875rem 1rem', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: '0.75rem', fontSize: '0.825rem', color: '#fbbf24' }}>
          ⚠️ Adaptive failover active: {unavail} gateway(s) unavailable. Traffic routed to {healthy} healthy gateway(s).
        </div>
      )}

      {list.length === 0 ? (
        <div style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.15)', borderRadius: '1rem', padding: '3rem', textAlign: 'center', color: '#475569' }}>
          <p style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>🔗</p>
          <p>No gateway providers configured.</p>
        </div>
      ) : (
        <div style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.15)', borderRadius: '1rem', overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(99,102,241,0.15)' }}>
                  {['Name', 'Label', 'Status', 'Priority', 'Latency', 'Successes', 'Failures', 'Capacity', 'Action'].map(h => (
                    <th key={h} style={th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {list.map((g, i) => (
                  <tr key={g.id ?? i} style={{ borderBottom: '1px solid rgba(99,102,241,0.08)', transition: 'background 0.15s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(99,102,241,0.06)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.775rem', fontFamily: 'monospace', color: '#a5b4fc', fontWeight: 600 }}>{g.name}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#e2e8f0' }}>{g.label}</td>
                    <td style={{ padding: '0.75rem 1rem' }}><Badge label={g.status} /></td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#94a3b8' }}>{g.priority}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#94a3b8' }}>{g.latency_ms} ms</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', fontWeight: 600, color: '#34d399' }}>{g.success_count}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', fontWeight: 600, color: '#f87171' }}>{g.failure_count}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#94a3b8' }}>{g.capacity}%</td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <button
                        onClick={() => handleToggle(g)}
                        disabled={toggling === g.id}
                        style={{
                          padding: '0.3rem 0.7rem', fontSize: '0.72rem', fontWeight: 600,
                          borderRadius: '0.5rem', border: 'none', cursor: toggling === g.id ? 'not-allowed' : 'pointer',
                          background: g.status === 'HEALTHY' ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)',
                          color: g.status === 'HEALTHY' ? '#f87171' : '#34d399',
                          opacity: toggling === g.id ? 0.5 : 1,
                          transition: 'opacity 0.2s',
                        }}
                      >
                        {toggling === g.id ? '...' : g.status === 'HEALTHY' ? 'Disable' : 'Enable'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default GatewaysPage;
