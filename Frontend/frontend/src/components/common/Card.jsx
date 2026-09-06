import React from 'react';

const Card = ({ title, value, prefix = '', suffix = '' }) => {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 text-center">
      <h3 className="text-lg font-medium text-gray-600 mb-2">{title}</h3>
      <div className="text-2xl font-bold">
        {prefix}{value}{suffix}
      </div>
    </div>
  );
};

export default Card;