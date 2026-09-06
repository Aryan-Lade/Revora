import React from 'react';

const Card = ({ title, value, prefix = '', suffix = '' }) => {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-gray-500 mb-2">{title}</h3>
      <p className="text-3xl font-bold">{prefix}{value}{suffix}</p>
    </div>
  );
};

export default Card;