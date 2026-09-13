import React from 'react';
import { useApi } from '../hooks/useApi';
import { Chart } from '../components/common';

const StatBox = ({ label, value }) => (
  <div style={{
    background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(99,102,241,0.18)',
    borderRadius: '0.75rem', padding: '0.875rem 1rem',
  }}>
    <div style={{ fontSize: '0.68rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '0.3rem' }}>{label}</div>
    <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#e2e8f0' }}>{value ?? '—'}</div>
  </div>
);

const AnalyticsPage = () => {
  const { data: channelData, loading: channelLoading } = useApi('/api/analytics/recovery-by-channel');
  const { data: reasonData,  loading: reasonLoading  } = useApi('/api/analytics/recovery-by-reason');
  const { data: mlData,      loading: mlLoading      } = useApi('/api/ml/metrics');

  if (channelLoading || reasonLoading || mlLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: 44, height: 44, border: '3px solid rgba(99,102,241,0.15)', borderTopColor: '#818cf8', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 1rem' }} />
          <p style={{ color: '#475569', fontSize: '0.875rem' }}>Loading analytics...</p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  const channelChart = Array.isArray(channelData) ? channelData : [];
  const reasonChart  = Array.isArray(reasonData)  ? reasonData  : [];
  const featureChart = Array.isArray(mlData?.feature_importance)
    ? mlData.feature_importance.map(item => ({ name: item.feature, value: +(item.importance * 100).toFixed(1) }))
    : [];

  const pct = (v) => `${((v ?? 0) * 100).toFixed(1)}%`;

  return (
    <div>
      <div style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.02em', marginBottom: '0.2rem' }}>Analytics</h1>
        <p style={{ fontSize: '0.825rem', color: '#475569' }}>Recovery performance, channel metrics & ML model insights</p>
      </div>

      {/* Channel + Reason charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
        <Chart title="Recovery by Channel"       type="bar" data={channelChart} />
        <Chart title="Recovery by Failure Reason" type="pie" data={reasonChart}  />
      </div>

      {/* ML metrics + Feature importance */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.18)', borderRadius: '1rem', padding: '1.25rem 1.5rem' }}>
          <h2 style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '1rem' }}>
            ML Model Performance
          </h2>
          {mlData ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              {[
                { label: 'Model',          value: mlData.model_name },
                { label: 'Dataset',        value: mlData.dataset },
                { label: 'Train Samples',  value: mlData.training_samples },
                { label: 'Test Samples',   value: mlData.test_samples },
                { label: 'Accuracy',       value: pct(mlData.accuracy) },
                { label: 'Precision',      value: pct(mlData.precision) },
                { label: 'Recall',         value: pct(mlData.recall) },
                { label: 'ROC-AUC',        value: pct(mlData.roc_auc) },
              ].map(({ label, value }) => (
                <StatBox key={label} label={label} value={value} />
              ))}
            </div>
          ) : (
            <p style={{ color: '#475569', fontSize: '0.875rem' }}>ML metrics not available.</p>
          )}
        </div>
        <Chart title="Feature Importance (%)" type="bar" data={featureChart} />
      </div>
    </div>
  );
};

export default AnalyticsPage;
