import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi, usePost } from '../hooks/useApi';

const RISK_COLORS = {
  CRITICAL: 'bg-red-100 text-red-800',
  HIGH:     'bg-orange-100 text-orange-800',
  MEDIUM:   'bg-yellow-100 text-yellow-800',
  LOW:      'bg-green-100 text-green-800',
};

const STATUS_COLORS = {
  RECOVERED:     'bg-green-100 text-green-800',
  ESCALATED:     'bg-red-100 text-red-800',
  PROMISE_TO_PAY:'bg-blue-100 text-blue-800',
  STOPPED:       'bg-gray-100 text-gray-600',
  WAITING:       'bg-yellow-100 text-yellow-800',
};

const RecoveryQueuePage = () => {
  const [refetchKey, setRefetchKey] = useState(0);
  const { data: cases, loading, error } = useApi('/api/recovery/', refetchKey);
  const { post: runBatch, loading: batchLoading, data: batchResult } = usePost('/api/recovery/run');
  const [sortConfig, setSortConfig] = useState({ key: 'expected_recovery', direction: 'descending' });

  if (loading) return <div className="p-6 text-gray-500">Loading recovery queue...</div>;
  if (error)   return <div className="p-6 text-red-500">Error: {error}</div>;

  const caseList = Array.isArray(cases) ? cases : [];

  const sortedCases = [...caseList].sort((a, b) => {
    const av = a[sortConfig.key] ?? 0;
    const bv = b[sortConfig.key] ?? 0;
    return sortConfig.direction === 'ascending' ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
  });

  const handleSort = (key) => {
    setSortConfig(prev =>
      prev.key === key
        ? { key, direction: prev.direction === 'ascending' ? 'descending' : 'ascending' }
        : { key, direction: 'descending' }
    );
  };

  const handleRunBatch = async () => {
    await runBatch();
    setRefetchKey(k => k + 1);
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Recovery Queue</h1>
        <button
          onClick={handleRunBatch}
          disabled={batchLoading}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium disabled:opacity-50"
        >
          {batchLoading ? 'Running...' : '⚡ Run Batch Recovery'}
        </button>
      </div>

      {batchResult && (
        <div className="mb-4 p-3 bg-indigo-50 border border-indigo-200 rounded-lg text-sm text-indigo-900">
          Batch complete: {batchResult.result?.detected ?? 0} cases detected,
          ₹{Number(batchResult.result?.amount_at_risk ?? 0).toLocaleString('en-IN')} at risk.
        </div>
      )}

      {sortedCases.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-6 text-gray-500">
          No recovery cases found. Click "Run Batch Recovery" to detect failed payments.
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {[
                  { key: 'reference',            label: 'Reference' },
                  { key: 'customer_name',         label: 'Customer' },
                  { key: 'amount_at_risk',        label: 'Amount at Risk' },
                  { key: 'recovery_probability',  label: 'Prob.' },
                  { key: 'expected_recovery',     label: 'Expected Recovery' },
                  { key: 'risk_level',            label: 'Risk' },
                  { key: 'recommended_action',    label: 'Action' },
                  { key: 'recommended_channel',   label: 'Channel' },
                  { key: 'status',                label: 'Status' },
                ].map(col => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none"
                  >
                    {col.label}
                    {sortConfig.key === col.key && (sortConfig.direction === 'ascending' ? ' ↑' : ' ↓')}
                  </th>
                ))}
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sortedCases.map((c, idx) => (
                <tr key={c.id ?? idx} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-mono">{c.reference}</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {c.customer?.name ?? `Customer #${c.customer_id}`}
                  </td>
                  <td className="px-4 py-3 text-sm">₹{Number(c.amount_at_risk).toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3 text-sm">{((c.recovery_probability ?? 0) * 100).toFixed(0)}%</td>
                  <td className="px-4 py-3 text-sm">₹{Number(c.expected_recovery ?? 0).toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${RISK_COLORS[c.risk_level] ?? 'bg-gray-100 text-gray-700'}`}>
                      {c.risk_level ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">{c.recommended_action ?? '—'}</td>
                  <td className="px-4 py-3 text-sm">{c.recommended_channel ?? '—'}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[c.status] ?? 'bg-gray-100 text-gray-700'}`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <Link to={`/recovery-case/${c.id}`} className="text-blue-600 hover:underline font-medium">
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default RecoveryQueuePage;
