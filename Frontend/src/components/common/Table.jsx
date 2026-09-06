import React from 'react';

const Table = ({ data, columns }) => {
  if (!data || data.length === 0) {
    return <div className="bg-white rounded-lg shadow p-6">No data available</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.map((row, index) => (
            <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
              {columns.map((column) => {
                const value = column.key.split('.').reduce((obj, key) => (obj && obj[key] !== undefined ? obj[key] : undefined), row);
                const formattedValue = column.format ? column.format(value) : value;
                return (
                  <td key={column.key} className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{formattedValue}</div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Table;