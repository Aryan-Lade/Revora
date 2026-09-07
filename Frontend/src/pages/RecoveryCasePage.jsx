import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApi, usePost } from '../hooks/useApi';
import { Badge } from '../components/common';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const Field = ({ label, value }) => (
  <div className="flex flex-col py-2 border-b border-gray-100 last:border-0">
    <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
    <span className="text-sm font-medium text-gray-900 mt-0.5">{value ?? '—'}</span>
  </div>
);

const Section = ({ title, children }) => (
  <div className="bg-white rounded-lg shadow p-5 mb-4">
    <h2 className="text-base font-semibold text-gray-700 mb-3">{title}</h2>
    {children}
  </div>
);

const StatusBadge = ({ status }) => {
  const colors = {
    RECOVERED: 'bg-green-100 text-green-800',
    ESCALATED: 'bg-red-100 text-red-800',
    PROMISE_TO_PAY: 'bg-blue-100 text-blue-800',
    STOPPED: 'bg-gray-100 text-gray-600',
    PROCESSING: 'bg-purple-100 text-purple-800',
    WAITING: 'bg-yellow-100 text-yellow-800',
  };
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${colors[status] ?? 'bg-blue-100 text-blue-800'}`}>
      {status}
    </span>
  );
};

const ActionButton = ({ label, onClick, variant = 'primary', disabled = false, loading = false }) => {
  const base = 'px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
  const variants = {
    primary:  'bg-indigo-600 hover:bg-indigo-700 text-white',
    success:  'bg-green-600 hover:bg-green-700 text-white',
    danger:   'bg-red-600 hover:bg-red-700 text-white',
    warning:  'bg-amber-500 hover:bg-amber-600 text-white',
    ghost:    'bg-gray-100 hover:bg-gray-200 text-gray-700',
  };
  return (
    <button
      className={`${base} ${variants[variant]}`}
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading ? 'Working...' : label}
    </button>
  );
};

const RecoveryCasePage = () => {
  const { id } = useParams();
  const [actionResult, setActionResult] = useState(null);
  const [actionError, setActionError]   = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [refetchKey, setRefetchKey] = useState(0);

  const { data: caseData,       loading: caseLoading }       = useApi(`/api/recovery/${id}`, refetchKey);
  const { data: timelineData,   loading: timelineLoading }   = useApi(`/api/recovery/${id}/timeline`, refetchKey);
  const { data: predictionData, loading: predictionLoading } = useApi(`/api/recovery/${id}/prediction`, refetchKey);
  const { data: policyData,     loading: policyLoading }     = useApi(`/api/recovery/${id}/policy`, refetchKey);

  const doAction = async (endpoint, method = 'POST') => {
    setActionLoading(true);
    setActionError(null);
    setActionResult(null);
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, { method });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || JSON.stringify(data));
      setActionResult(data);
      setRefetchKey(k => k + 1);
    } catch (e) {
      setActionError(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  if (caseLoading || timelineLoading || predictionLoading || policyLoading) {
    return <div className="p-6 text-gray-500">Loading case...</div>;
  }

  if (!caseData) {
    return (
      <div className="p-6">
        <p className="text-red-500">Case not found.</p>
        <Link to="/recovery-queue" className="text-blue-600 hover:underline mt-2 inline-block">← Back to Queue</Link>
      </div>
    );
  }

  const auditLogs        = timelineData?.audit_logs        ?? [];
  const recoveryAttempts = timelineData?.recovery_attempts ?? [];
  const communications   = timelineData?.communications    ?? [];
  const isTerminal = ['RECOVERED','STOPPED','EXPIRED'].includes(caseData.status);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Link to="/recovery-queue" className="text-sm text-blue-600 hover:underline">← Queue</Link>
        <h1 className="text-2xl font-bold">Case {caseData.reference}</h1>
        <div className="ml-auto flex items-center gap-2">
          <StatusBadge status={caseData.status} />
        </div>
      </div>

      {actionResult && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
          <strong>Success:</strong>{' '}
          {actionResult.status === 'recovered'
            ? `₹${Number(actionResult.recovered_amount).toLocaleString('en-IN')} recovered — case is now ${actionResult.case_status}`
            : actionResult.status === 'already_recovered'
            ? 'This case is already recovered.'
            : JSON.stringify(actionResult)}
        </div>
      )}
      {actionError && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
          <strong>Error:</strong> {actionError}
        </div>
      )}

      {!isTerminal && (
        <Section title="Actions">
          <div className="flex flex-wrap gap-3">
            <ActionButton
              label="⚡ Execute Recovery"
              variant="primary"
              loading={actionLoading}
              onClick={() => doAction(`/api/recovery/${id}/execute`)}
            />
            <ActionButton
              label="✅ Simulate Payment"
              variant="success"
              loading={actionLoading}
              onClick={() => doAction(`/api/recovery/${id}/simulate-payment`)}
            />
            <ActionButton
              label="🔺 Escalate"
              variant="warning"
              loading={actionLoading}
              onClick={() => doAction(`/api/recovery/${id}/escalate`)}
            />
            <ActionButton
              label="⏹ Stop"
              variant="danger"
              loading={actionLoading}
              onClick={() => doAction(`/api/recovery/${id}/stop`)}
            />
          </div>
        </Section>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <Section title="Payment Details">
            <div className="grid grid-cols-2 gap-x-6">
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
              <div className="grid grid-cols-2 gap-x-6">
                <Field label="Recommended Action"  value={predictionData.recommended_action} />
                <Field label="Recommended Channel" value={predictionData.recommended_channel} />
                <Field label="ML Recovery Prob."   value={`${((predictionData.recovery_probability ?? 0) * 100).toFixed(1)}%`} />
                <Field label="AI Confidence"       value={`${((predictionData.ai_confidence ?? 0) * 100).toFixed(1)}%`} />
                <Field label="Expected Recovery"   value={`₹${Number(predictionData.expected_recovery ?? 0).toLocaleString('en-IN')}`} />
              </div>
              {predictionData.reasoning && (
                <div className="mt-3 p-3 bg-indigo-50 rounded text-sm text-indigo-900">
                  <span className="font-medium">Reasoning: </span>{predictionData.reasoning}
                </div>
              )}
            </Section>
          )}

          {policyData && (
            <Section title="Policy Decision">
              <div className="flex items-center gap-2 mb-3">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${policyData.allowed ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  {policyData.allowed ? '✓ Allowed' : '✗ Blocked'}
                </span>
                {policyData.blocked_by && <span className="text-xs text-gray-500">Blocked by: {policyData.blocked_by}</span>}
              </div>
              <p className="text-sm text-gray-700 mb-2">{policyData.reason}</p>
              {policyData.next_contact_at && (
                <Field label="Next Contact At" value={new Date(policyData.next_contact_at).toLocaleString()} />
              )}
              {Array.isArray(policyData.checks) && policyData.checks.length > 0 && (
                <div className="mt-3 space-y-1">
                  {policyData.checks.map((check, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span className={check.passed ? 'text-green-600' : 'text-red-500'}>
                        {check.passed ? '✓' : '✗'}
                      </span>
                      <span className="font-medium">{check.label}:</span>
                      <span className="text-gray-600">{check.detail}</span>
                    </div>
                  ))}
                </div>
              )}
            </Section>
          )}
        </div>

        <div className="space-y-4">
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
              <div className="space-y-2">
                {recoveryAttempts.map((attempt, i) => (
                  <div key={i} className="text-xs bg-gray-50 rounded p-2">
                    <div className="flex justify-between">
                      <span className="font-medium">#{attempt.attempt_number} {attempt.action}</span>
                      <span className={attempt.status === 'SUCCEEDED' ? 'text-green-600' : attempt.status === 'FAILED' ? 'text-red-500' : 'text-gray-500'}>
                        {attempt.status}
                      </span>
                    </div>
                    <div className="text-gray-500">{attempt.channel} · {attempt.reason}</div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {communications.length > 0 && (
            <Section title={`Communications (${communications.length})`}>
              <div className="space-y-2">
                {communications.map((comm, i) => (
                  <div key={i} className="text-xs bg-gray-50 rounded p-2">
                    <div className="flex justify-between">
                      <span className="font-medium">{comm.channel}</span>
                      <span className="text-gray-500">{comm.status}</span>
                    </div>
                    {comm.subject && <div className="text-gray-600 truncate">{comm.subject}</div>}
                    <div className="text-gray-400">{new Date(comm.sent_at).toLocaleString()}</div>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </div>
      </div>

      {auditLogs.length > 0 && (
        <Section title="Audit Timeline">
          <div className="space-y-2">
            {auditLogs.map((log, i) => (
              <div key={i} className="flex gap-3 text-sm">
                <span className="text-gray-400 whitespace-nowrap text-xs pt-0.5">
                  {new Date(log.created_at).toLocaleString()}
                </span>
                <div>
                  <span className="font-medium text-gray-700">{log.event}</span>
                  <span className="text-gray-500 mx-1">·</span>
                  <span className="text-gray-500">{log.actor}</span>
                  {log.reason && <div className="text-xs text-gray-500">{log.reason}</div>}
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
