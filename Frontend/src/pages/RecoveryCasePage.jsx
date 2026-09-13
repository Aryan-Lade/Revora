import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

const STATUS_STYLE = {
  RECOVERED:     { background: 'rgba(16,185,129,0.15)',  color: '#34d399', border: '1px solid rgba(16,185,129,0.3)' },
  ESCALATED:     { background: 'rgba(239,68,68,0.15)',   color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' },
  PROMISE_TO_PAY:{ background: 'rgba(99,102,241,0.15)',  color: '#a5b4fc', border: '1px solid rgba(99,102,241,0.3)' },
  STOPPED:       { background: 'rgba(100,116,139,0.15)', color: '#64748b', border: '1px solid rgba(100,116,139,0.3)' },
  PROCESSING:    { background: 'rgba(139,92,246,0.15)',  color: '#c084fc', border: '1px solid rgba(139,92,246,0.3)' },
  WAITING:       { background: 'rgba(245,158,11,0.15)',  color: '#fbbf24', border: '1px solid rgba(245,158,11,0.3)' },
  DETECTED:      { background: 'rgba(96,165,250,0.15)',  color: '#60a5fa', border: '1px solid rgba(96,165,250,0.3)' },
};

const StatusBadge = ({ status }) => {
  const s = STATUS_STYLE[status] || STATUS_STYLE.DETECTED;
  return <span style={{ ...s, padding: '0.3rem 0.9rem', borderRadius: '2rem', fontSize: '0.8rem', fontWeight: 600 }}>{status}</span>;
};

const Field = ({ label, value }) => (
  <div style={{ padding: '0.6rem 0', borderBottom: '1px solid rgba(99,102,241,0.08)' }}>
    <div style={{ fontSize: '0.68rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '0.2rem' }}>{label}</div>
    <div style={{ fontSize: '0.85rem', fontWeight: 500, color: '#e2e8f0' }}>{value ?? '—'}</div>
  </div>
);

const Section = ({ title, children }) => (
  <div style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.18)', borderRadius: '1rem', padding: '1.25rem 1.5rem', marginBottom: '1rem' }}>
    <h2 style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '1rem' }}>{title}</h2>
    {children}
  </div>
);

const ActionBtn = ({ label, onClick, color = '#6366f1', bg = 'rgba(99,102,241,0.15)', disabled }) => (
  <button onClick={onClick} disabled={disabled} style={{
    padding: '0.5rem 1.1rem', fontSize: '0.825rem', fontWeight: 600,
    background: bg, color, border: `1px solid ${color}44`,
    borderRadius: '0.625rem', cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1, transition: 'opacity 0.2s',
  }}>
    {label}
  </button>
);

const RecoveryCasePage = () => {
  const { id } = useParams();
  const [actionResult, setActionResult] = useState(null);
  const [actionError, setActionError]   = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [refetchKey, setRefetchKey] = useState(0);

  const { data: caseData,       loading: caseLoading }       = useApi(`/api/recovery/${id}`,            refetchKey);
  const { data: timelineData,   loading: timelineLoading }   = useApi(`/api/recovery/${id}/timeline`,   refetchKey);
  const { data: predictionData, loading: predictionLoading } = useApi(`/api/recovery/${id}/prediction`, refetchKey);
  const { data: policyData,     loading: policyLoading }     = useApi(`/api/recovery/${id}/policy`,     refetchKey);

  const doAction = async (endpoint, method = 'POST') => {
    setActionLoading(true); setActionError(null); setActionResult(null);
    try {
      const res  = await fetch(`${API_BASE}${endpoint}`, { method });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || JSON.stringify(data));
      setActionResult(data); setRefetchKey(k => k + 1);
    } catch (e) { setActionError(e.message); }
    finally { setActionLoading(false); }
  };

  if (caseLoading || timelineLoading || predictionLoading || policyLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: 44, height: 44, border: '3px solid rgba(99,102,241,0.15)', borderTopColor: '#818cf8', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 1rem' }} />
          <p style={{ color: '#475569', fontSize: '0.875rem' }}>Loading case details...</p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!caseData) return (
    <div>
      <p style={{ color: '#f87171', marginBottom: '0.75rem' }}>Case not found.</p>
      <Link to="/recovery-queue" style={{ color: '#818cf8', fontSize: '0.875rem' }}>← Back to Queue</Link>
    </div>
  );

  const auditLogs        = timelineData?.audit_logs        ?? [];
  const recoveryAttempts = timelineData?.recovery_attempts ?? [];
  const communications   = timelineData?.communications    ?? [];
  const isTerminal = ['RECOVERED', 'STOPPED', 'EXPIRED'].includes(caseData.status);

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
        <Link to="/recovery-queue" style={{ color: '#64748b', fontSize: '0.825rem', textDecoration: 'none' }}>← Queue</Link>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.02em' }}>
          Case {caseData.reference}
        </h1>
        <StatusBadge status={caseData.status} />
      </div>

      {actionResult && (
        <div style={{ marginBottom: '1rem', padding: '0.875rem 1rem', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.25)', borderRadius: '0.75rem', fontSize: '0.825rem', color: '#34d399' }}>
          ✓ {actionResult.status === 'recovered'
            ? `₹${Number(actionResult.recovered_amount).toLocaleString('en-IN')} recovered — case is now ${actionResult.case_status}`
            : actionResult.status === 'already_recovered'
            ? 'This case is already recovered.'
            : JSON.stringify(actionResult)}
        </div>
      )}
      {actionError && (
        <div style={{ marginBottom: '1rem', padding: '0.875rem 1rem', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: '0.75rem', fontSize: '0.825rem', color: '#f87171' }}>
          ✗ {actionError}
        </div>
      )}

      {/* Actions */}
      {!isTerminal && (
        <Section title="Actions">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
            <ActionBtn label="⚡ Execute Recovery" onClick={() => doAction(`/api/recovery/${id}/execute`)}       disabled={actionLoading} color="#818cf8" bg="rgba(99,102,241,0.15)" />
            <ActionBtn label="✅ Simulate Payment" onClick={() => doAction(`/api/recovery/${id}/simulate-payment`)} disabled={actionLoading} color="#34d399" bg="rgba(16,185,129,0.15)" />
            <ActionBtn label="🔺 Escalate"         onClick={() => doAction(`/api/recovery/${id}/escalate`)}      disabled={actionLoading} color="#fbbf24" bg="rgba(245,158,11,0.15)" />
            <ActionBtn label="⏹ Stop"             onClick={() => doAction(`/api/recovery/${id}/stop`)}          disabled={actionLoading} color="#f87171" bg="rgba(239,68,68,0.15)" />
          </div>
        </Section>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1rem' }}>
        {/* Left column */}
        <div>
          <Section title="Payment Details">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 1.5rem' }}>
              <Field label="Amount at Risk"       value={`₹${Number(caseData.amount_at_risk).toLocaleString('en-IN')}`} />
              <Field label="Expected Recovery"    value={`₹${Number(caseData.expected_recovery ?? 0).toLocaleString('en-IN')}`} />
              <Field label="Failure Type"         value={caseData.failure_type} />
              <Field label="Risk Level"           value={caseData.risk_level} />
              <Field label="Risk Score"           value={(caseData.risk_score ?? 0).toFixed(2)} />
              <Field label="Priority"             value={caseData.priority} />
              <Field label="Attempt Count"        value={caseData.attempt_count} />
              <Field label="Contact Count"        value={caseData.contact_count} />
              <Field label="Recovery Probability" value={`${((caseData.recovery_probability ?? 0) * 100).toFixed(1)}%`} />
              <Field label="Recovered Amount"     value={`₹${Number(caseData.recovered_amount ?? 0).toLocaleString('en-IN')}`} />
            </div>
          </Section>

          {predictionData && (
            <Section title="AI Recommendation">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 1.5rem' }}>
                <Field label="Recommended Action"  value={predictionData.recommended_action} />
                <Field label="Recommended Channel" value={predictionData.recommended_channel} />
                <Field label="ML Recovery Prob."   value={`${((predictionData.recovery_probability ?? 0) * 100).toFixed(1)}%`} />
                <Field label="AI Confidence"       value={`${((predictionData.ai_confidence ?? 0) * 100).toFixed(1)}%`} />
                <Field label="Expected Recovery"   value={`₹${Number(predictionData.expected_recovery ?? 0).toLocaleString('en-IN')}`} />
              </div>
              {predictionData.reasoning && (
                <div style={{ marginTop: '0.75rem', padding: '0.875rem', background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: '0.625rem', fontSize: '0.825rem', color: '#a5b4fc' }}>
                  <span style={{ fontWeight: 600 }}>Reasoning: </span>{predictionData.reasoning}
                </div>
              )}
            </Section>
          )}

          {policyData && (
            <Section title="Policy Decision">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                <span style={{
                  padding: '0.2rem 0.75rem', borderRadius: '2rem', fontSize: '0.75rem', fontWeight: 600,
                  ...(policyData.allowed
                    ? { background: 'rgba(16,185,129,0.15)', color: '#34d399', border: '1px solid rgba(16,185,129,0.3)' }
                    : { background: 'rgba(239,68,68,0.15)',  color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' }),
                }}>
                  {policyData.allowed ? '✓ Allowed' : '✗ Blocked'}
                </span>
                {policyData.blocked_by && <span style={{ fontSize: '0.775rem', color: '#64748b' }}>Blocked by: {policyData.blocked_by}</span>}
              </div>
              <p style={{ fontSize: '0.825rem', color: '#94a3b8', marginBottom: '0.5rem' }}>{policyData.reason}</p>
              {policyData.next_contact_at && <Field label="Next Contact At" value={new Date(policyData.next_contact_at).toLocaleString()} />}
              {Array.isArray(policyData.checks) && policyData.checks.length > 0 && (
                <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                  {policyData.checks.map((check, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.775rem' }}>
                      <span style={{ color: check.passed ? '#34d399' : '#f87171', fontWeight: 700 }}>{check.passed ? '✓' : '✗'}</span>
                      <span style={{ fontWeight: 600, color: '#94a3b8' }}>{check.label}:</span>
                      <span style={{ color: '#64748b' }}>{check.detail}</span>
                    </div>
                  ))}
                </div>
              )}
            </Section>
          )}
        </div>

        {/* Right column */}
        <div>
          <Section title="Case Info">
            <Field label="Reference"   value={caseData.reference} />
            <Field label="Status"      value={caseData.status} />
            <Field label="Detected At" value={caseData.detected_at ? new Date(caseData.detected_at).toLocaleString() : null} />
            <Field label="Resolved At" value={caseData.resolved_at ? new Date(caseData.resolved_at).toLocaleString() : 'Ongoing'} />
            {caseData.blocked_reason && <Field label="Blocked Reason" value={caseData.blocked_reason} />}
            {caseData.stop_reason    && <Field label="Stop Reason"    value={caseData.stop_reason} />}
          </Section>

          {recoveryAttempts.length > 0 && (
            <Section title={`Recovery Attempts (${recoveryAttempts.length})`}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {recoveryAttempts.map((a, i) => (
                  <div key={i} style={{ background: 'rgba(15,23,42,0.5)', border: '1px solid rgba(99,102,241,0.12)', borderRadius: '0.625rem', padding: '0.625rem 0.875rem', fontSize: '0.775rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                      <span style={{ fontWeight: 600, color: '#e2e8f0' }}>#{a.attempt_number} {a.action}</span>
                      <span style={{ color: a.status === 'SUCCEEDED' ? '#34d399' : a.status === 'FAILED' ? '#f87171' : '#64748b' }}>{a.status}</span>
                    </div>
                    <div style={{ color: '#64748b' }}>{a.channel} · {a.reason}</div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {communications.length > 0 && (
            <Section title={`Communications (${communications.length})`}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {communications.map((c, i) => (
                  <div key={i} style={{ background: 'rgba(15,23,42,0.5)', border: '1px solid rgba(99,102,241,0.12)', borderRadius: '0.625rem', padding: '0.625rem 0.875rem', fontSize: '0.775rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                      <span style={{ fontWeight: 600, color: '#e2e8f0' }}>{c.channel}</span>
                      <span style={{ color: '#64748b' }}>{c.status}</span>
                    </div>
                    {c.subject && <div style={{ color: '#94a3b8', marginBottom: '0.2rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.subject}</div>}
                    <div style={{ color: '#475569' }}>{new Date(c.sent_at).toLocaleString()}</div>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </div>
      </div>

      {/* Audit Timeline */}
      {auditLogs.length > 0 && (
        <Section title={`Audit Timeline (${auditLogs.length} events)`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {auditLogs.map((log, i) => (
              <div key={i} style={{ display: 'flex', gap: '1rem', fontSize: '0.825rem', paddingBottom: '0.5rem', borderBottom: '1px solid rgba(99,102,241,0.08)' }}>
                <span style={{ fontSize: '0.725rem', color: '#475569', whiteSpace: 'nowrap', paddingTop: '0.1rem', minWidth: 130 }}>
                  {new Date(log.created_at).toLocaleString()}
                </span>
                <div>
                  <span style={{ fontWeight: 600, color: '#e2e8f0' }}>{log.event}</span>
                  <span style={{ color: '#475569', margin: '0 0.4rem' }}>·</span>
                  <span style={{ color: '#64748b' }}>{log.actor}</span>
                  {log.reason && <div style={{ fontSize: '0.775rem', color: '#475569' }}>{log.reason}</div>}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
};

export default RecoveryCasePage;
