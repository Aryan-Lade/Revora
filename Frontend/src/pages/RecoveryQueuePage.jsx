import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi, usePost } from '../hooks/useApi';

const RISK_STYLE = {
  CRITICAL: { background: 'rgba(239,68,68,0.15)',  color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' },
  HIGH:     { background: 'rgba(249,115,22,0.15)', color: '#fb923c', border: '1px solid rgba(249,115,22,0.3)' },
  MEDIUM:   { background: 'rgba(245,158,11,0.15)', color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)' },
  LOW:      { background: 'rgba(16,185,129,0.15)', color: '#34d399', border: '1px solid rgba(16,185,129,0.3)' },
};

const STATUS_STYLE = {
  RECOVERED:     { background: 'rgba(16,185,129,0.15)',  color: '#34d399', border: '1px solid rgba(16,185,129,0.3)' },
  ESCALATED:     { background: 'rgba(239,68,68,0.15)',   color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' },
  PROMISE_TO_PAY:{ background: 'rgba(99,102,241,0.15)',  color: '#a5b4fc', border: '1px solid rgba(99,102,241,0.3)' },
  STOPPED:       { background: 'rgba(100,116,139,0.15)', color: '#64748b', border: '1px solid rgba(100,116,139,0.3)' },
  WAITING:       { background: 'rgba(245,158,11,0.15)',  color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)' },
  DETECTED:      { background: 'rgba(96,165,250,0.15)',  color: '#60a5fa', border: '1px solid rgba(96,165,250,0.3)' },
};

const Badge = ({ label, styleMap }) => {
  const s = styleMap[label] || { background: 'rgba(100,116,139,0.15)', color: '#94a3b8', border: '1px solid rgba(100,116,139,0.3)' };
  return (
    <span style={{
      ...s, padding: '0.2rem 0.6rem', borderRadius: '2rem',
      fontSize: '0.7rem', fontWeight: 600, whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  );
};

const RecoveryQueuePage = () => {
  const [refetchKey, setRefetchKey] = useState(0);
  const { data: cases, loading, error } = useApi('/api/recovery/', refetchKey);
  const { post: runBatch, loading: batchLoading, data: batchResult } = usePost('/api/recovery/run');
  const [sortConfig, setSortConfig] = useState({ key: 'expected_recovery', direction: 'descending' });

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{
          width: 44, height: 44, border: '3px solid rgba(99,102,241,0.15)',
          borderTopColor: '#818cf8', borderRadius: '50%',
          animation: 'spin 0.8s linear infinite', margin: '0 auto 1rem',
        }} />
        <p style={{ color: '#475569', fontSize: '0.875rem' }}>Loading recovery queue...</p>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  if (error) return (
    <div style={{ padding: '1.5rem', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: '0.875rem', color: '#f87171' }}>
      Error: {error}
    </div>
  );

  const caseList = Array.isArray(cases) ? cases : [];
  const sortedCases = [...caseList].sort((a, b) => {
    const av = a[sortConfig.key] ?? 0, bv = b[sortConfig.key] ?? 0;
    return sortConfig.direction === 'ascending' ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
  });

  const handleSort = (key) => {
    setSortConfig(prev =>
      prev.key === key
        ? { key, direction: prev.direction === 'ascending' ? 'descending' : 'ascending' }
        : { key, direction: 'descending' }
    );
  };

  const handleRunBatch = async () => { await runBatch(); setRefetchKey(k => k + 1); };

  const th = { padding: '0.75rem 1rem', fontSize: '0.7rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap' };

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.02em', marginBottom: '0.2rem' }}>
            Recovery Queue
          </h1>
          <p style={{ fontSize: '0.825rem', color: '#475569' }}>
            {caseList.length} active case{caseList.length !== 1 ? 's' : ''} · sorted by {sortConfig.key.replace(/_/g, ' ')}
          </p>
        </div>
        <button
          onClick={handleRunBatch}
          disabled={batchLoading}
          style={{
            padding: '0.5rem 1.2rem',
            background: batchLoading ? 'rgba(99,102,241,0.3)' : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            color: '#fff', border: 'none', borderRadius: '0.625rem',
            fontSize: '0.825rem', fontWeight: 600, cursor: batchLoading ? 'not-allowed' : 'pointer',
            boxShadow: '0 4px 16px rgba(99,102,241,0.3)', opacity: batchLoading ? 0.6 : 1,
          }}
        >
          {batchLoading ? '⏳ Running...' : '⚡ Run Batch Recovery'}
        </button>
      </div>

      {batchResult && (
        <div style={{
          marginBottom: '1rem', padding: '0.75rem 1rem',
          background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.25)',
          borderRadius: '0.75rem', fontSize: '0.825rem', color: '#a5b4fc',
        }}>
          ✓ Batch complete: {batchResult.result?.detected ?? 0} cases detected,
          ₹{Number(batchResult.result?.amount_at_risk ?? 0).toLocaleString('en-IN')} at risk.
        </div>
      )}

      {sortedCases.length === 0 ? (
        <div style={{
          background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.15)',
          borderRadius: '1rem', padding: '3rem', textAlign: 'center', color: '#475569',
        }}>
          <p style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>📭</p>
          <p>No recovery cases found. Click "Run Batch Recovery" to scan for failed payments.</p>
        </div>
      ) : (
        <div style={{
          background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.15)',
          borderRadius: '1rem', overflow: 'hidden',
        }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(99,102,241,0.15)' }}>
                  {[
                    { key: 'reference',           label: 'Reference' },
                    { key: 'customer_name',        label: 'Customer' },
                    { key: 'amount_at_risk',       label: 'Amount at Risk' },
                    { key: 'recovery_probability', label: 'Prob.' },
                    { key: 'expected_recovery',    label: 'Expected' },
                    { key: 'risk_level',           label: 'Risk' },
                    { key: 'recommended_action',   label: 'Action' },
                    { key: 'status',               label: 'Status' },
                  ].map(col => (
                    <th key={col.key} style={th} onClick={() => handleSort(col.key)}>
                      {col.label}
                      {sortConfig.key === col.key && (
                        <span style={{ marginLeft: 4, color: '#818cf8' }}>
                          {sortConfig.direction === 'ascending' ? '↑' : '↓'}
                        </span>
                      )}
                    </th>
                  ))}
                  <th style={{ ...th, cursor: 'default' }} />
                </tr>
              </thead>
              <tbody>
                {sortedCases.map((c, idx) => (
                  <tr key={c.id ?? idx} style={{
                    borderBottom: '1px solid rgba(99,102,241,0.08)',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(99,102,241,0.06)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.775rem', fontFamily: 'monospace', color: '#64748b' }}>
                      {c.reference}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', fontWeight: 600, color: '#e2e8f0' }}>
                      {c.customer?.name ?? `Customer #${c.customer_id}`}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#f87171', fontWeight: 600 }}>
                      ₹{Number(c.amount_at_risk).toLocaleString('en-IN')}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <div style={{
                          width: 36, height: 5, borderRadius: 3,
                          background: 'rgba(100,116,139,0.25)', overflow: 'hidden',
                        }}>
                          <div style={{
                            width: `${((c.recovery_probability ?? 0) * 100).toFixed(0)}%`,
                            height: '100%', background: '#818cf8', borderRadius: 3,
                          }} />
                        </div>
                        <span style={{ color: '#94a3b8', fontSize: '0.775rem' }}>
                          {((c.recovery_probability ?? 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#34d399', fontWeight: 600 }}>
                      ₹{Number(c.expected_recovery ?? 0).toLocaleString('en-IN')}
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <Badge label={c.risk_level ?? '—'} styleMap={RISK_STYLE} />
                    </td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.775rem', color: '#94a3b8' }}>
                      {c.recommended_action ?? '—'}
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <Badge label={c.status} styleMap={STATUS_STYLE} />
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <Link to={`/recovery-case/${c.id}`} style={{
                        fontSize: '0.775rem', fontWeight: 600, color: '#818cf8',
                        textDecoration: 'none', padding: '0.3rem 0.75rem',
                        background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.25)',
                        borderRadius: '0.5rem', transition: 'background 0.15s',
                      }}>
                        View →
                      </Link>
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

export default RecoveryQueuePage;
