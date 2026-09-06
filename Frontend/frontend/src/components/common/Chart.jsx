import React from 'react';
import { Bar, Line, Pie, Funnel } from 'recharts';

const Chart = ({ title, type, data }) => {
  // For simplicity, we'll assume data is in the format expected by each chart type
  // In a real app, we would transform the data accordingly

  let chartContent = null;
  if (type === 'bar') {
    chartContent = (
      <BarChart data={data}>
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="value" />
      </BarChart>
    );
  } else if (type === 'line') {
    chartContent = (
      <LineChart data={data}>
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="value" stroke="#8884d8" />
      </LineChart>
    );
  } else if (type === 'pie') {
    chartContent = (
      <PieChart data={data}>
        <Tooltip />
        <Legend />
        <Pie dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={60} outerRadius={80} />
      </PieChart>
    );
  } else if (type === 'funnel') {
    // For funnel, we'll use a simple bar chart for now (recharts doesn't have funnel)
    chartContent = (
      <BarChart data={data}>
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="value" />
      </BarChart>
    );
  } else {
    chartContent = <div>Unsupported chart type: {type}</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-medium text-gray-600 mb-4">{title}</h3>
      <div className="h-96 w-full">{chartContent}</div>
    </div>
  );
};

// We need to import the chart components from recharts
const BarChart = ({ children }) => <div className="w-full h-full">{children}</div>;
const LineChart = ({ children }) => <div className="w-full h-full">{children}</div>;
const PieChart = ({ children }) => <div className="w-full h-full">{children}</div>;

export default Chart;