import React from 'react';
import { useApi } from '../hooks/useApi';

const STATUS_STYLE = {
  ACTIVE:    { background: 'rgba(99,102,241,0.15)',  color: '#a5b4fc', border: '1px solid rgba(99,102,241,0.3)' },
  FULFILLED: { background: 'rgba(16,185,129,0.15)',  color: '#34d399', border: '1px solid rgba(16,185,129,0.3)' },
  BROKEN:    { background: 'rgba(239,68,68,0.15)',   color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' },
  EXPIRED:   { background: 'rgba(100,116,139,0.15)', color: '#64748b', border: '1px solid rgba(100,116,139,0.3)' },
  CANCELLED: { background: 'rgba(245,158,11,0.15)',  color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)' },
};

const Badge = ({ label }) => {
  const s = STATUS_STYLE[label] || { background: 'rgba(100,116,139,0.15)', color: '#94a3b8', border: '1px solid rgba(100,116,139,0.3)' };
  return <span style={{ ...s, padding: '0.2rem 0.65rem', borderRadius: '2rem', fontSize: '0.7rem', fontWeight: 600 }}>{label}</span>;
};

const th = { padding: '0.75rem 1rem', fontSize: '0.7rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', whiteSpace: 'nowrap' };

const PromisesPage = () => {
  const { data: promises, loading, error } = useApi('/api/promises');

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ width: 44, height: 44, border: '3px solid rgba(99,102,241,0.15)', borderTopColor: '#818cf8', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 1rem' }} />
        <p style={{ color: '#475569', fontSize: '0.875rem' }}>Loading promises...</p>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  if (error) return (
    <div style={{ padding: '1.5rem', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: '0.875rem', color: '#f87171' }}>
      Error: {error}
    </div>
  );

  const list = Array.isArray(promises) ? promises : [];

  return (
    <div>
      <div style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.02em', marginBottom: '0.2rem' }}>Promises to Pay</h1>
        <p style={{ fontSize: '0.825rem', color: '#475569' }}>{list.length} commitment{list.length !== 1 ? 's' : ''} recorded</p>
      </div>

      {list.length === 0 ? (
        <div style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.15)', borderRadius: '1rem', padding: '3rem', textAlign: 'center', color: '#475569' }}>
          <p style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>🤝</p>
          <p>No promises to pay recorded yet.</p>
        </div>
      ) : (
        <div style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.15)', borderRadius: '1rem', overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(99,102,241,0.15)' }}>
                  {['Customer', 'Amount', 'Promised Date', 'Channel', 'Status', 'Next Eligible Contact'].map(h => (
                    <th key={h} style={th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {list.map((p, i) => (
                  <tr key={p.id ?? i} style={{ borderBottom: '1px solid rgba(99,102,241,0.08)', transition: 'background 0.15s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(99,102,241,0.06)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', fontWeight: 600, color: '#e2e8f0' }}>{p.customer_name || `Customer #${p.customer_id}`}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', fontWeight: 700, color: '#34d399' }}>₹{Number(p.amount).toLocaleString('en-IN')}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#94a3b8' }}>{new Date(p.promised_date).toLocaleDateString('en-IN')}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#94a3b8' }}>{p.channel}</td>
                    <td style={{ padding: '0.75rem 1rem' }}><Badge label={p.status} /></td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#818cf8', fontWeight: 500 }}>
                      {p.next_eligible_contact ? new Date(p.next_eligible_contact).toLocaleDateString('en-IN') : '—'}
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

export default PromisesPage;
