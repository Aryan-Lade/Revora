import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const STATUS_COLORS = {
  HEALTHY:     'bg-green-100 text-green-800',
  DEGRADED:    'bg-yellow-100 text-yellow-800',
  UNAVAILABLE: 'bg-red-100 text-red-800',
};

const GatewaysPage = () => {
  const [refetchKey, setRefetchKey] = useState(0);
  const { data: gateways, loading, error } = useApi('/api/gateways/', refetchKey);
  const [toggling, setToggling] = useState(null);
  const [toggleMsg, setToggleMsg] = useState(null);

  if (loading) return <div className="p-6 text-gray-500">Loading gateways...</div>;
  if (error)   return <div className="p-6 text-red-500">Error: {error}</div>;

  const list = Array.isArray(gateways) ? gateways : [];
  const healthy   = list.filter(g => g.status === 'HEALTHY').length;
  const degraded  = list.filter(g => g.status === 'DEGRADED').length;
  const unavail   = list.filter(g => g.status === 'UNAVAILABLE').length;

  const handleToggle = async (gateway) => {
    setToggling(gateway.id);
    setToggleMsg(null);
    try {
      const res = await fetch(`${API_BASE}/api/gateways/${gateway.id}/toggle`, { method: 'POST' });
      const data = await res.json();
      setToggleMsg(`${data.name} is now ${data.status}`);
      setRefetchKey(k => k + 1);
    } catch (e) {
      setToggleMsg('Toggle failed: ' + e.message);
    } finally {
      setToggling(null);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Gateway Providers</h1>

      {toggleMsg && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-900">
          {toggleMsg}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total',       value: list.length,  color: 'bg-white' },
          { label: 'Healthy',     value: healthy,       color: 'bg-green-50' },
          { label: 'Degraded',    value: degraded,      color: 'bg-yellow-50' },
          { label: 'Unavailable', value: unavail,       color: 'bg-red-50' },
        ].map(({ label, value, color }) => (
          <div key={label} className={`${color} rounded-lg shadow p-4 text-center`}>
            <div className="text-xs text-gray-500 uppercase">{label}</div>
            <div className="text-3xl font-bold mt-1">{value}</div>
          </div>
        ))}
      </div>

      {unavail > 0 && healthy > 0 && (
        <div className="mb-4 p-4 bg-amber-50 border border-amber-300 rounded-lg text-sm text-amber-900">
          ⚠️ Adaptive failover active: {unavail} gateway(s) unavailable. Traffic routed to {healthy} healthy gateway(s).
        </div>
      )}

      {list.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-6 text-gray-500">No gateway providers found.</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['Name', 'Label', 'Status', 'Priority', 'Latency (ms)', 'Successes', 'Failures', 'Capacity', 'Demo'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {list.map((g, i) => (
                <tr key={g.id ?? i} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-mono font-medium">{g.name}</td>
                  <td className="px-4 py-3 text-sm">{g.label}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[g.status] ?? 'bg-gray-100 text-gray-600'}`}>
                      {g.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">{g.priority}</td>
                  <td className="px-4 py-3 text-sm">{g.latency_ms}</td>
                  <td className="px-4 py-3 text-sm text-green-700">{g.success_count}</td>
                  <td className="px-4 py-3 text-sm text-red-600">{g.failure_count}</td>
                  <td className="px-4 py-3 text-sm">{g.capacity}</td>
                  <td className="px-4 py-3 text-sm">
                    <button
                      onClick={() => handleToggle(g)}
                      disabled={toggling === g.id}
                      className="px-2 py-1 rounded text-xs font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 disabled:opacity-50"
                    >
                      {toggling === g.id ? '...' : g.status === 'HEALTHY' ? 'Mark Unavailable' : 'Mark Healthy'}
                    </button>
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

export default GatewaysPage;
