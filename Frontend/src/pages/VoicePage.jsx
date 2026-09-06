import React, { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';
import { Card, Table } from '../components/common';

const VoicePage = () => {
  const { data: voiceSessions, loading } = useApi('/api/voice/sessions');
  const { data: voiceHealth, loading: healthLoading } = useApi('/api/voice/health');

  if (loading || healthLoading) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Voice AI</h1>

      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-2">Voice Provider Health</h2>
        {voiceHealth && (
          <div className="space-y-4">
            <Card title="Status" value={voiceHealth.status || 'unknown'} />
            <Card title="Latency" value={voiceHealth.latency_ms || 0} suffix="ms" />
            <Card title="Success Count" value={voiceHealth.success_count || 0} />
            <Card title="Failure Count" value={voiceHealth.failure_count || 0} />
          </div>
        )}
      </div>

      <h2 className="text-xl font-semibold mb-4">Voice Sessions</h2>
      {voiceSessions && voiceSessions.length > 0 ? (
        <Table
          data={voiceSessions}
          columns={[
            { key: 'customer.name', label: 'Customer' },
            { key: 'status', label: 'Status' },
            { key: 'started_at', label: 'Started At', format: (val) => new Date(val).toLocaleString() },
            { key: 'ended_at', label: 'Ended At', format: (val) => val ? new Date(val).toLocaleString() : 'Ongoing' },
            { key: 'promise_created', label: 'Promise Created', format: (val) => val ? 'Yes' : 'No' },
            { key: 'recovered_amount', label: 'Recovered (₹)', format: (val) => `₹${val}` },
          ]}
        />
      ) : (
        <p className="text-gray-500">No voice sessions found.</p>
      )}
    </div>
  );
};

export default VoicePage;