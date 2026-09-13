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
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: 44, height: 44, border: '3px solid rgba(99,102,241,0.15)',
            borderTopColor: '#818cf8', borderRadius: '50%',
            animation: 'spin 0.8s linear infinite', margin: '0 auto 1rem',
          }} />
          <p style={{ color: '#475569', fontSize: '0.875rem' }}>Loading dashboard...</p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div>
      {/* Page header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.75rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.02em', marginBottom: '0.2rem' }}>
            Revenue Recovery
          </h1>
          <p style={{ fontSize: '0.825rem', color: '#475569' }}>AI-driven recovery dashboard — real-time insights</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          {batchMsg && (
            <span style={{
              fontSize: '0.775rem', color: '#a5b4fc',
              background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.25)',
              padding: '0.3rem 0.8rem', borderRadius: '2rem',
            }}>
              ✓ {batchMsg}
            </span>
          )}
          <button
            onClick={handleBatch}
            disabled={batchLoading}
            style={{
              padding: '0.5rem 1.2rem',
              background: batchLoading ? 'rgba(99,102,241,0.3)' : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              color: '#fff', border: 'none', borderRadius: '0.625rem',
              fontSize: '0.825rem', fontWeight: 600, cursor: batchLoading ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 16px rgba(99,102,241,0.3)', transition: 'opacity 0.2s',
              opacity: batchLoading ? 0.6 : 1,
            }}
          >
            {batchLoading ? '⏳ Scanning...' : '⚡ Run Recovery Scan'}
          </button>
          <Link
            to="/recovery-queue"
            style={{
              padding: '0.5rem 1.1rem',
              background: 'rgba(15,23,42,0.8)', color: '#a5b4fc',
              border: '1px solid rgba(99,102,241,0.25)', borderRadius: '0.625rem',
              fontSize: '0.825rem', fontWeight: 600, textDecoration: 'none',
              transition: 'background 0.2s',
            }}
          >
            View Queue →
          </Link>
        </div>
      </div>

      {/* Primary KPI cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
        <Card title="Revenue At Risk"      value={overviewData?.revenue_at_risk ?? 0}      prefix="₹" icon="🔥" color="rose" />
        <Card title="Expected Recoverable" value={overviewData?.expected_recoverable ?? 0}  prefix="₹" icon="📈" color="amber" />
        <Card title="Recovered Revenue"    value={overviewData?.recovered_revenue ?? 0}     prefix="₹" icon="✅" color="emerald" />
        <Card title="Recovery Rate"        value={overviewData?.recovery_rate ?? 0}         suffix="%" icon="🎯" color="indigo" />
      </div>

      {/* Secondary stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.875rem', marginBottom: '1.5rem' }}>
        <Cards title="Active Cases"    value={overviewData?.active_cases ?? 0}    icon="⚡" />
        <Cards title="Escalated Cases" value={overviewData?.escalated_cases ?? 0} icon="🚨" />
        <Cards title="Policy Blocks"   value={overviewData?.policy_blocks ?? 0}   icon="🛡️" />
        <Cards title="Promises to Pay" value={overviewData?.promises_to_pay ?? 0} icon="🤝" />
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
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
          title="Recovery Trends (6 months)"
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
