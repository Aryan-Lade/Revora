import React, { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';
import { Table } from '../components/common';

const RecoveryQueuePage = () => {
  const { data: cases, loading } = useApi('/api/recovery/cases');
  const [sortConfig, setSortConfig] = useState({ key: 'expected_recovery', direction: 'descending' });

  if (loading) return <div className="p-6">Loading...</div>;

  const sortedCases = [...cases].sort((a, b) => {
    if (sortConfig.direction === 'ascending') {
      return a[sortConfig.key] > b[sortConfig.key] ? 1 : -1;
    } else {
      return a[sortConfig.key] < b[sortConfig.key] ? 1 : -1;
    }
  });

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Recovery Queue</h1>
      <Table
        data={sortedCases}
        columns={[
          { key: 'customer.name', label: 'Customer' },
          { key: 'subscription.plan_name', label: 'Subscription' },
          { key: 'amount_at_risk', label: 'Amount (₹)', format: (val) => `₹${val}` },
          { key: 'recovery_probability', label: 'Recovery Probability', format: (val) => `${(val * 100).toFixed(1)}%` },
          { key: 'expected_recovery', label: 'Expected Recovery (₹)', format: (val) => `₹${val.toFixed(2)}` },
          { key: 'risk_level', label: 'Risk' },
          { key: 'recommended_action', label: 'Action' },
          { key: 'recommended_channel', label: 'Channel' },
          { key: 'status', label: 'Status' },
        ]}
      />
    </div>
  );
};

export default RecoveryQueuePage;