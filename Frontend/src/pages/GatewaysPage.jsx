import React, { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';
import { Table, Card, Cards } from '../components/common';

const GatewaysPage = () => {
  const { data: gateways, loading } = useApi('/api/gateways');

  if (loading) return <div className="p-6">Loading gateways...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Gateway Providers</h1>

      <div className="mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card title="Total Providers" value={gateways?.length || 0} />
          <Card title="Healthy Providers" value={gateways?.filter(g => g.status === 'healthy').length || 0} />
          <Card title="Unhealthy Providers" value={gateways?.filter(g => g.status !== 'healthy').length || 0} />
        </div>
      </div>

      <h2 className="text-xl font-semibold mb-4">Gateway Details</h2>
      {gateways && gateways.length > 0 ? (
        <Table
          data={gateways}
          columns={[
            { key: 'name', label: 'Name' },
            { key: 'label', label: 'Label' },
            { key: 'status', label: 'Status' },
            { key: 'latency_ms', label: 'Latency (ms)' },
            { key: 'success_count', label: 'Success Count' },
            { key: 'failure_count', label: 'Failure Count' },
            { key: 'capacity', label: 'Capacity' },
            { key: 'priority', label: 'Priority' },
          ]}
        />
      ) : (
        <p className="text-gray-500">No gateway providers found.</p>
      )}
    </div>
  );
};

export default GatewaysPage;