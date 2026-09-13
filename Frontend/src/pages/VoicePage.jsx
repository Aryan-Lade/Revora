import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

const InfoBox = ({ label, value }) => (
  <div style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(99,102,241,0.18)', borderRadius: '0.75rem', padding: '0.875rem 1rem', textAlign: 'center' }}>
    <div style={{ fontSize: '0.68rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '0.3rem' }}>{label}</div>
    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#e2e8f0' }}>{value}</div>
  </div>
);

const VoicePage = () => {
  const [refetchKey, setRefetchKey]   = useState(0);
  const { data: voiceSessions, loading }        = useApi('/api/voice/sessions', refetchKey);
  const { data: voiceHealth,   loading: hLoad } = useApi('/api/voice/health', refetchKey);
  const [callResult, setCallResult]   = useState(null);
  const [callLoading, setCallLoading] = useState(false);
  const [caseIdInput, setCaseIdInput] = useState('');

  if (loading || hLoad) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ width: 44, height: 44, border: '3px solid rgba(99,102,241,0.15)', borderTopColor: '#818cf8', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 1rem' }} />
        <p style={{ color: '#475569', fontSize: '0.875rem' }}>Loading voice data...</p>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  const sessions = Array.isArray(voiceSessions) ? voiceSessions : [];

  const handleDemoCall = async () => {
    const cid = parseInt(caseIdInput, 10);
    if (!cid) return alert('Enter a valid Case ID');
    setCallLoading(true); setCallResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/voice/start?customer_id=1&recovery_case_id=${cid}`, { method: 'POST' });
      const data = await res.json();
      setCallResult(data); setRefetchKey(k => k + 1);
    } catch (e) { setCallResult({ error: e.message }); }
    finally { setCallLoading(false); }
  };

  const card = { background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.18)', borderRadius: '1rem', padding: '1.25rem 1.5rem', marginBottom: '1rem' };
  const th   = { padding: '0.75rem 1rem', fontSize: '0.7rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em' };

  return (
    <div>
      <div style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.02em', marginBottom: '0.2rem' }}>Voice AI</h1>
        <p style={{ fontSize: '0.825rem', color: '#475569' }}>AI-powered voice recovery calls & session logs</p>
      </div>

      {/* Provider Health */}
      <div style={card}>
        <h2 style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '1rem' }}>Provider Health</h2>
        {voiceHealth ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem' }}>
            <InfoBox label="Status"        value={voiceHealth.status ?? 'HEALTHY'} />
            <InfoBox label="Latency"       value={`${voiceHealth.latency_ms ?? 0} ms`} />
            <InfoBox label="Success Count" value={voiceHealth.success_count ?? 0} />
            <InfoBox label="Failure Count" value={voiceHealth.failure_count ?? 0} />
          </div>
        ) : (
          <p style={{ color: '#475569', fontSize: '0.875rem' }}>No health data available.</p>
        )}
      </div>

      {/* Demo Call */}
      <div style={card}>
        <h2 style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.6rem' }}>Demo Voice Call</h2>
        <p style={{ fontSize: '0.825rem', color: '#475569', marginBottom: '1rem' }}>
          Enter a recovery case ID to simulate an AI voice call. The agent will attempt to recover payment and may record a promise-to-pay.
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <input
            type="number"
            value={caseIdInput}
            onChange={e => setCaseIdInput(e.target.value)}
            placeholder="Case ID (e.g. 1)"
            style={{
              background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.3)',
              borderRadius: '0.625rem', padding: '0.5rem 0.875rem',
              fontSize: '0.825rem', color: '#e2e8f0', width: 160, outline: 'none',
            }}
          />
          <button
            onClick={handleDemoCall}
            disabled={callLoading}
            style={{
              padding: '0.5rem 1.2rem',
              background: callLoading ? 'rgba(99,102,241,0.3)' : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              color: '#fff', border: 'none', borderRadius: '0.625rem',
              fontSize: '0.825rem', fontWeight: 600, cursor: callLoading ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 16px rgba(99,102,241,0.3)', opacity: callLoading ? 0.6 : 1,
            }}
          >
            {callLoading ? '⏳ Calling...' : '📞 Start Demo Call'}
          </button>
        </div>

        {callResult && (
          <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(99,102,241,0.15)', borderRadius: '0.75rem', fontSize: '0.825rem' }}>
            {callResult.blocked ? (
              <div style={{ color: '#fbbf24' }}>
                <div style={{ fontWeight: 700, marginBottom: '0.4rem' }}>🛡️ Policy Blocked</div>
                <div style={{ color: '#94a3b8' }}><strong style={{ color: '#e2e8f0' }}>Reason:</strong> {callResult.reason}</div>
                {callResult.blocked_by && <div style={{ color: '#94a3b8' }}><strong style={{ color: '#e2e8f0' }}>Rule:</strong> {callResult.blocked_by}</div>}
                {callResult.next_contact_at && <div style={{ color: '#94a3b8' }}><strong style={{ color: '#e2e8f0' }}>Next Contact:</strong> {new Date(callResult.next_contact_at).toLocaleString('en-IN')}</div>}
              </div>
            ) : callResult.error ? (
              <p style={{ color: '#f87171' }}>{callResult.error}</p>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', color: '#94a3b8' }}>
                {[
                  ['Status', callResult.status],
                  ['Intent', callResult.intent],
                  ['Answered', callResult.answered ? '✓ Yes' : '✗ No'],
                  ['Paid on call', callResult.paid ? '✓ Yes' : '✗ No'],
                  ['Promise created', callResult.promise_id ? `Yes (ID: ${callResult.promise_id})` : 'No'],
                  ['Warm channel', callResult.warm ? '✓ Yes' : 'No'],
                  ['Health latency', `${callResult.health_latency_ms} ms`],
                  ['Start latency', `${callResult.call_start_latency_ms} ms`],
                ].map(([k, v]) => (
                  <div key={k}><strong style={{ color: '#e2e8f0' }}>{k}:</strong> {v}</div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Sessions Table */}
      <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.875rem' }}>
        Voice Sessions {sessions.length > 0 && <span style={{ color: '#64748b', fontWeight: 400 }}>({sessions.length})</span>}
      </h2>

      {sessions.length === 0 ? (
        <div style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.15)', borderRadius: '1rem', padding: '3rem', textAlign: 'center', color: '#475569' }}>
          <p style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>🎙️</p>
          <p>No voice sessions yet. Use the Demo Call above to create one.</p>
        </div>
      ) : (
        <div style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.15)', borderRadius: '1rem', overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(99,102,241,0.15)' }}>
                  {['Case ID', 'Status', 'Intent', 'Warm', 'Latency (ms)', 'Started At', 'Promise', 'Recovered'].map(h => (
                    <th key={h} style={th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sessions.map((s, i) => (
                  <tr key={s.id ?? i} style={{ borderBottom: '1px solid rgba(99,102,241,0.08)', transition: 'background 0.15s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(99,102,241,0.06)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#94a3b8' }}>{s.recovery_case_id}</td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <span style={{ padding: '0.2rem 0.65rem', borderRadius: '2rem', fontSize: '0.7rem', fontWeight: 600, background: 'rgba(99,102,241,0.15)', color: '#a5b4fc', border: '1px solid rgba(99,102,241,0.3)' }}>
                        {s.status}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#94a3b8' }}>{s.intent ?? '—'}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: s.warm ? '#34d399' : '#64748b' }}>{s.warm ? '✓ Warm' : 'Cold'}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#94a3b8' }}>{s.call_start_latency_ms}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.775rem', color: '#64748b' }}>{new Date(s.started_at).toLocaleString()}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: s.promise_created ? '#34d399' : '#475569' }}>{s.promise_created ? '✓ Yes' : '—'}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', fontWeight: 600, color: '#34d399' }}>₹{Number(s.recovered_amount ?? 0).toLocaleString('en-IN')}</td>
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

export default VoicePage;
