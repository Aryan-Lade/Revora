import React, { useEffect, useState } from 'react';
import { useApi } from '../hooks/useApi';
import { Table } from '../components/common';

const PromisesPage = () => {
  const { data: promises, loading } = useApi('/api/promises');

  if (loading) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Promises to Pay</h1>
      <Table
        data={promises}
        columns={[
          { key: 'customer.name', label: 'Customer' },
          { key: 'amount', label: 'Amount (₹)', format: (val) => `₹${val}` },
          { key: 'promised_date', label: 'Promised Date', format: (val) => new Date(val).toLocaleDateString() },
          { key: 'channel', label: 'Channel' },
          { key: 'status', label: 'Status' },
        ]}
      />
    </div>
  );
};

export default PromisesPage;