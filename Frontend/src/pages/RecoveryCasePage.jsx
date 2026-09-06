import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { Card, Stat, Table, Badge } from '../components/common';

const RecoveryCasePage = () => {
  const { id } = useParams();
  const caseId = parseInt(id, 10);

  const { data: caseData, loading: caseLoading } = useApi(`/api/recovery/cases/${caseId}`);
  const { data: timelineData, loading: timelineLoading } = useApi(`/api/recovery/cases/${caseId}/timeline`);
  const { data: predictionData, loading: predictionLoading } = useApi(`/api/recovery/cases/${caseId}/prediction`);
  const { data: policyData, loading: policyLoading } = useApi(`/api/recovery/cases/${caseId}/policy`);

  if (caseLoading || timelineLoading || predictionLoading || policyLoading) {
    return <div className="p-6">Loading...</div>;
  }

  if (!caseData) {
    return <div className="p-6">Case not found</div>;
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Recovery Case Details</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h2 className="text-xl font-bold mb-4">Case Overview</h2>
          <div className="grid grid-cols-1 gap-4">
            <Card title="Customer" value={caseData.customer?.name || 'N/A'} />
            <Card title="Subscription" value={caseData.subscription?.plan_name || 'N/A'} />
            <Card title="Amount at Risk" value={caseData.amount_at_risk || 0} prefix="₹" />
            <Card title="Recovery Probability" value={caseData.recovery_probability || 0} suffix="%" />
            <Card title="Expected Recovery" value={caseData.expected_recovery || 0} prefix="₹" />
            <Card title="Risk Level" value={caseData.risk_level || 'N/A'} />
            <Card title="Priority" value={caseData.priority || 'N/A'} />
            <Card title="Status" value={caseData.status || 'N/A'} />
          </div>
        </div>
        <div>
          <h2 className="text-xl font-bold mb-4">AI Recommendation</h2>
          <div className="space-y-4">
            <Card title="Diagnosis" value={predictionData?.reasoning || 'N/A'} />
            <Card title="Recommended Action" value={predictionData?.recommended_action || 'N/A'} />
            <Card title="Recommended Channel" value={predictionData?.recommended_channel || 'N/A'} />
            <Card title="Confidence" value={predictionData?.ai_confidence || 0} suffix="%" />
            <Card title="Reasoning" value={predictionData?.reasoning || 'N/A'} />
          </div>
        </div>
      </div>
      <div className="mt-6">
        <h2 className="text-xl font-bold mb-4">Policy Decision</h2>
        <div className="space-y-4">
          <Card title="Allowed" value={policyData?.allowed ? 'Yes' : 'No'} />
          {policyData?.channel && <Card title="Channel" value={policyData.channel} />}
          <Card title="Reason" value={policyData?.reason || 'N/A'} />
          {policyData?.blocked_by && <Card title="Blocked By" value={policyData.blocked_by} />}
          {policyData?.next_contact_at && <Card title="Next Contact At" value={new Date(policyData.next_contact_at).toLocaleString()} />}
        </div>
      </div>
      <div className="mt-6">
        <h2 className="text-xl font-bold mb-4">Timeline</h2>
        {timelineData && timelineData.length > 0 ? (
          <Table
            data={timelineData}
            columns={[
              { key: 'created_at', label: 'Time', format: (val) => new Date(val).toLocaleString() },
              { key: 'event', label: 'Event' },
              { key: 'actor', label: 'Actor' },
              { key: 'action', label: 'Action' },
              { key: 'reason', label: 'Reason' },
            ]}
          />
        ) : (
          <p className="text-gray-500">No timeline events yet.</p>
        )}
      </div>
    </div>
  );
};

export default RecoveryCasePage;