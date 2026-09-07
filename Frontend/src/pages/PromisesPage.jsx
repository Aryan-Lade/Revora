import React from 'react';
import { useApi } from '../hooks/useApi';

const STATUS_COLORS = {
  ACTIVE:    'bg-blue-100 text-blue-800',
  FULFILLED: 'bg-green-100 text-green-800',
  BROKEN:    'bg-red-100 text-red-800',
  EXPIRED:   'bg-gray-100 text-gray-600',
  CANCELLED: 'bg-yellow-100 text-yellow-800',
};

const PromisesPage = () => {
  const { data: promises, loading, error } = useApi('/api/promises');

  if (loading) return <div className="p-6 text-gray-500">Loading promises...</div>;
  if (error)   return <div className="p-6 text-red-500">Error: {error}</div>;

  const list = Array.isArray(promises) ? promises : [];

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Promises to Pay</h1>

      {list.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-6 text-gray-500">No promises to pay recorded.</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['Customer ID', 'Amount', 'Promised Date', 'Channel', 'Status', 'Quote'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {list.map((p, i) => (
                <tr key={p.id ?? i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm">{p.customer_id}</td>
                  <td className="px-4 py-3 text-sm font-medium">₹{Number(p.amount).toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3 text-sm">{new Date(p.promised_date).toLocaleDateString('en-IN')}</td>
                  <td className="px-4 py-3 text-sm">{p.channel}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[p.status] ?? 'bg-gray-100 text-gray-700'}`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">{p.source_quote || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default PromisesPage;
