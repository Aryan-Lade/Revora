import React from 'react';

const Stat = ({ value, label, prefix = '', suffix = '' }) => {
  return (
    <div className="flex flex-col items-center">
      <div className="text-2xl font-bold">
        {prefix}{value}{suffix}
      </div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );
};

export default Stat;