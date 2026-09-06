import React, { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';
import { Chart, Card, Cards } from '../components/common';

const AnalyticsPage = () => {
  const { data: recoveryByChannel, loading: channelLoading } = useApi('/api/analytics/recovery-by-channel');
  const { data: recoveryByReason, loading: reasonLoading } = useApi('/api/analytics/recovery-by-reason');
  const { data: mlAnalytics, loading: mlLoading } = useApi('/api/ml/metrics');

  if (channelLoading || reasonLoading || mlLoading) {
    return <div className="p-6">Loading analytics...</div>;
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Analytics</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <h2 className="text-xl font-semibold mb-2">Recovery by Channel</h2>
          {recoveryByChannel && (
            <Chart
              title="Recovery Amount by Channel"
              type="bar"
              data={recoveryByChannel}
            />
          )}
        </div>
        <div>
          <h2 className="text-xl font-semibold mb-2">Recovery by Failure Reason</h2>
          {recoveryByReason && (
            <Chart
              title="Recovery Amount by Failure Reason"
              type="pie"
              data={recoveryByReason}
            />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <h2 className="text-xl font-semibold mb-2">ML Model Performance</h2>
          {mlAnalytics && (
            <div className="space-y-4">
              <Card title="Accuracy" value={(mlAnalytics.accuracy || 0) * 100} suffix="%" />
              <Card title="Precision" value={(mlAnalytics.precision || 0) * 100} suffix="%" />
              <Card title="Recall" value={(mlAnalytics.recall || 0) * 100} suffix="%" />
              <Card title="ROC-AUC" value={(mlAnalytics.roc_auc || 0) * 100} suffix="%" />
            </div>
          )}
        </div>
        <div>
          <h2 className="text-xl font-semibold mb-2">Feature Importance</h2>
          {mlAnalytics && mlAnalytics.feature_importance && (
            <Chart
              title="ML Feature Importance"
              type="bar"
              data={mlAnalytics.feature_importance.map(item => ({
                name: item.feature,
                value: item.importance * 100
              }))}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;