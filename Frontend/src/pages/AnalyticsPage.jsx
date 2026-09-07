import React from 'react';
import { useApi } from '../hooks/useApi';
import { Chart } from '../components/common';

const AnalyticsPage = () => {
  const { data: channelData, loading: channelLoading } = useApi('/api/analytics/recovery-by-channel');
  const { data: reasonData,  loading: reasonLoading  } = useApi('/api/analytics/recovery-by-reason');
  const { data: mlData,      loading: mlLoading      } = useApi('/api/ml/metrics');

  if (channelLoading || reasonLoading || mlLoading) {
    return <div className="p-6 text-gray-500">Loading analytics...</div>;
  }

  // Normalise data – backend may return null if no records exist
  const channelChart = Array.isArray(channelData) ? channelData : [];
  const reasonChart  = Array.isArray(reasonData)  ? reasonData  : [];

  const featureChart = Array.isArray(mlData?.feature_importance)
    ? mlData.feature_importance.map(item => ({
        name:  item.feature,
        value: +(item.importance * 100).toFixed(1),
      }))
    : [];

  const pct = (v) => `${((v ?? 0) * 100).toFixed(1)}%`;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Analytics</h1>

      {/* Channel + Reason charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <Chart title="Recovery by Channel"       type="bar" data={channelChart} />
        <Chart title="Recovery by Failure Reason" type="pie" data={reasonChart}  />
      </div>

      {/* ML metrics + Feature importance */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ML metric cards */}
        <div className="bg-white rounded-lg shadow p-5">
          <h2 className="text-base font-semibold text-gray-700 mb-4">ML Model Performance</h2>
          {mlData ? (
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: 'Model',     value: mlData.model_name },
                { label: 'Dataset',   value: mlData.dataset },
                { label: 'Train samples', value: mlData.training_samples },
                { label: 'Test samples',  value: mlData.test_samples },
                { label: 'Accuracy',  value: pct(mlData.accuracy) },
                { label: 'Precision', value: pct(mlData.precision) },
                { label: 'Recall',    value: pct(mlData.recall) },
                { label: 'ROC-AUC',   value: pct(mlData.roc_auc) },
              ].map(({ label, value }) => (
                <div key={label} className="bg-gray-50 rounded p-3">
                  <div className="text-xs text-gray-500 uppercase">{label}</div>
                  <div className="text-lg font-bold mt-0.5">{value}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">ML metrics not available.</p>
          )}
        </div>

        {/* Feature importance chart */}
        <Chart title="Feature Importance (%)" type="bar" data={featureChart} />
      </div>
    </div>
  );
};

export default AnalyticsPage;
