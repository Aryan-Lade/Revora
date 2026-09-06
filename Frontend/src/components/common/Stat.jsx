import React from 'react';

const Stat = ({ label, value, prefix = '', suffix = '' }) => {
  return (
    <div className="flex flex-col items-center">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold">{prefix}{value}{suffix}</p>
    </div>
  );
};

export default Stat;