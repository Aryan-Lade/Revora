import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const VoicePage = () => {
  const [refetchKey, setRefetchKey] = useState(0);
  const { data: voiceSessions, loading }       = useApi('/api/voice/sessions', refetchKey);
  const { data: voiceHealth,   loading: hLoad } = useApi('/api/voice/health', refetchKey);
  const [callResult, setCallResult] = useState(null);
  const [callLoading, setCallLoading] = useState(false);
  const [caseIdInput, setCaseIdInput] = useState('');

  if (loading || hLoad) return <div className="p-6 text-gray-500">Loading voice data...</div>;

  const sessions = Array.isArray(voiceSessions) ? voiceSessions : [];

  const handleDemoCall = async () => {
    const cid = parseInt(caseIdInput, 10);
    if (!cid) return alert('Enter a valid Case ID');
    setCallLoading(true);
    setCallResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/voice/start?customer_id=1&recovery_case_id=${cid}`, { method: 'POST' });
      const data = await res.json();
      setCallResult(data);
      setRefetchKey(k => k + 1);
    } catch (e) {
      setCallResult({ error: e.message });
    } finally {
      setCallLoading(false);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Voice AI</h1>

      <div className="bg-white rounded-lg shadow p-5 mb-6">
        <h2 className="text-base font-semibold text-gray-700 mb-3">Provider Health</h2>
        {voiceHealth ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Status',        value: voiceHealth.status ?? 'HEALTHY' },
              { label: 'Latency',       value: `${voiceHealth.latency_ms ?? 0} ms` },
              { label: 'Success Count', value: voiceHealth.success_count ?? 0 },
              { label: 'Failure Count', value: voiceHealth.failure_count ?? 0 },
            ].map(({ label, value }) => (
              <div key={label} className="text-center p-3 bg-gray-50 rounded">
                <div className="text-xs text-gray-500 uppercase">{label}</div>
                <div className="text-lg font-bold mt-1">{value}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400 text-sm">No health data available.</p>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-5 mb-6">
        <h2 className="text-base font-semibold text-gray-700 mb-3">Demo Voice Call</h2>
        <p className="text-sm text-gray-500 mb-3">
          Enter a recovery case ID to simulate a voice call. The agent will attempt to recover the payment and may record a promise-to-pay.
        </p>
        <div className="flex gap-3 items-center">
          <input
            type="number"
            value={caseIdInput}
            onChange={e => setCaseIdInput(e.target.value)}
            placeholder="Case ID (e.g. 1)"
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          <button
            onClick={handleDemoCall}
            disabled={callLoading}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {callLoading ? 'Calling...' : '📞 Start Demo Call'}
          </button>
        </div>
        {callResult && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg text-sm">
            {callResult.blocked ? (
              <div className="p-3 bg-amber-50 border border-amber-300 rounded text-amber-900 space-y-1">
                <div className="font-semibold text-amber-800">🛡️ Policy Blocked: Call Not Permitted</div>
                <div><strong>Reason:</strong> {callResult.reason}</div>
                {callResult.blocked_by && <div><strong>Blocked by rule:</strong> {callResult.blocked_by}</div>}
                {callResult.next_contact_at && <div><strong>Next eligible contact:</strong> {new Date(callResult.next_contact_at).toLocaleString('en-IN')}</div>}
              </div>
            ) : callResult.error ? (
              <p className="text-red-600">{callResult.error}</p>
            ) : (
              <div className="space-y-1 text-gray-700">
                <div><strong>Status:</strong> {callResult.status}</div>
                <div><strong>Intent:</strong> {callResult.intent}</div>
                <div><strong>Answered:</strong> {callResult.answered ? 'Yes' : 'No'}</div>
                <div><strong>Paid on call:</strong> {callResult.paid ? 'Yes' : 'No'}</div>
                <div><strong>Promise created:</strong> {callResult.promise_id ? `Yes (ID: ${callResult.promise_id})` : 'No'}</div>
                <div><strong>Warm channel:</strong> {callResult.warm ? 'Yes' : 'No'}</div>
                <div><strong>Health latency:</strong> {callResult.health_latency_ms} ms</div>
                <div><strong>Start latency:</strong> {callResult.call_start_latency_ms} ms</div>
              </div>
            )}
          </div>
        )}
      </div>

      <h2 className="text-lg font-semibold mb-3">Voice Sessions</h2>
      {sessions.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-6 text-gray-500">No voice sessions recorded. Use the demo call above to create one.</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['Case ID', 'Status', 'Intent', 'Warm', 'Latency (ms)', 'Started At', 'Promise', 'Recovered'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sessions.map((s, i) => (
                <tr key={s.id ?? i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm">{s.recovery_case_id}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">{s.status}</span>
                  </td>
                  <td className="px-4 py-3 text-sm">{s.intent ?? '—'}</td>
                  <td className="px-4 py-3 text-sm">{s.warm ? '✓ Warm' : 'Cold'}</td>
                  <td className="px-4 py-3 text-sm">{s.call_start_latency_ms}</td>
                  <td className="px-4 py-3 text-sm">{new Date(s.started_at).toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm">{s.promise_created ? '✓ Yes' : '—'}</td>
                  <td className="px-4 py-3 text-sm font-medium">₹{Number(s.recovered_amount ?? 0).toLocaleString('en-IN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default VoicePage;
