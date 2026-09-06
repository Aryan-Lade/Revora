import React, { useEffect, useState } from 'react';
import { Card, Cards, Stat, Chart } from '../components/common';
import { useApi } from '../hooks/useApi';

const DashboardPage = () => {
  const { data: overviewData, loading: overviewLoading } = useApi('/api/dashboard/overview');
  const { data: revenueData, loading: revenueLoading } = useApi('/api/dashboard/revenue');
  const { data: trendsData, loading: trendsLoading } = useApi('/api/dashboard/trends');

  if (overviewLoading || revenueDataLoading || trendsLoading) {
    return <div className="p-6">Loading...</div>;
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Revora Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card title="Revenue At Risk" value={overviewData?.revenue_at_risk || 0} prefix="₹" />
        <Card title="Expected Recoverable" value={overviewData?.expected_recoverable || 0} prefix="₹" />
        <Card title="Recovered Revenue" value={overviewData?.recovered_revenue || 0} prefix="₹" />
        <Card title="Recovery Rate" value={overviewData?.recovery_rate || 0} suffix="%" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <Cards title="Active Cases" value={overviewData?.active_cases || 0} />
        <Cards title="Escalated Cases" value={overviewData?.escalated_cases || 0} />
        <Cards title="Policy Blocks" value={overviewData?.policy_blocks || 0} />
        <Cards title="Promises to Pay" value={overviewData?.promises_to_pay || 0} />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Chart title="Recovery Funnel" type="funnel" data={revenueData?.funnel || []} />
        <Chart title="Recovery Trends" type="line" data={trendsData?.monthly || []} />
      </div>
    </div>
  );
};

export default DashboardPage;