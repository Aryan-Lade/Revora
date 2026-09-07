import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, Cards, Chart } from '../components/common';
import { useApi, usePost } from '../hooks/useApi';

const DashboardPage = () => {
  const [refetchKey, setRefetchKey] = useState(0);
  const { data: overviewData, loading: overviewLoading } = useApi('/api/dashboard/overview', refetchKey);
  const { data: revenueData,  loading: revenueLoading  } = useApi('/api/dashboard/revenue',  refetchKey);
  const { data: trendsData,   loading: trendsLoading   } = useApi('/api/dashboard/trends',   refetchKey);
  const { post: runBatch, loading: batchLoading } = usePost('/api/recovery/run');
  const [batchMsg, setBatchMsg] = useState(null);

  const handleBatch = async () => {
    setBatchMsg(null);
    const result = await runBatch();
    setBatchMsg(`Scan complete: ${result?.result?.detected ?? 0} new cases detected.`);
    setRefetchKey(k => k + 1);
  };

  if (overviewLoading || revenueLoading || trendsLoading) {
    return <div className="p-6 text-gray-500">Loading dashboard...</div>;
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Revora Dashboard</h1>
        <div className="flex gap-3">
          {batchMsg && <span className="text-sm text-indigo-700 self-center">{batchMsg}</span>}
          <button
            onClick={handleBatch}
            disabled={batchLoading}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {batchLoading ? 'Scanning...' : '⚡ Run Recovery Scan'}
          </button>
          <Link
            to="/recovery-queue"
            className="px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg text-sm font-medium"
          >
            View Queue →
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card title="Revenue At Risk"       value={overviewData?.revenue_at_risk ?? 0}      prefix="₹" />
        <Card title="Expected Recoverable"  value={overviewData?.expected_recoverable ?? 0}  prefix="₹" />
        <Card title="Recovered Revenue"     value={overviewData?.recovered_revenue ?? 0}     prefix="₹" />
        <Card title="Recovery Rate"         value={overviewData?.recovery_rate ?? 0}         suffix="%" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Cards title="Active Cases"     value={overviewData?.active_cases ?? 0} />
        <Cards title="Escalated Cases"  value={overviewData?.escalated_cases ?? 0} />
        <Cards title="Policy Blocks"    value={overviewData?.policy_blocks ?? 0} />
        <Cards title="Promises to Pay"  value={overviewData?.promises_to_pay ?? 0} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Chart
          title="Recovery Funnel"
          type="bar"
          data={[
            { name: 'At Risk',     value: revenueData?.revenue_at_risk ?? 0 },
            { name: 'Recoverable', value: revenueData?.expected_recoverable ?? 0 },
            { name: 'Eligible',    value: revenueData?.eligible ?? 0 },
            { name: 'Intervened',  value: revenueData?.intervention ?? 0 },
            { name: 'Recovered',   value: revenueData?.recovered ?? 0 },
          ]}
        />
        <Chart
          title="Recovery Trends"
          type="line"
          data={(trendsData?.monthly?.labels ?? []).map((label, i) => ({
            name:      label,
            recovered: trendsData.monthly.recovered[i] ?? 0,
            expected:  trendsData.monthly.expected[i]  ?? 0,
          }))}
        />
      </div>
    </div>
  );
};

export default DashboardPage;
