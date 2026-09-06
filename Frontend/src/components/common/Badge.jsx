import React from 'react';

const Badge = ({ children, variant = 'default' }) => {
  let className = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';
  if (variant === 'success') {
    className += ' bg-green-100 text-green-800';
  } else if (variant === 'error') {
    className += ' bg-red-100 text-red-800';
  } else if (variant === 'warning') {
    className += ' bg-yellow-100 text-yellow-800';
  } else if (variant === 'info') {
    className += ' bg-blue-100 text-blue-800';
  } else {
    className += ' bg-gray-100 text-gray-800';
  }

  return (
    <span className={className}>
      {children}
    </span>
  );
};

export default Badge;