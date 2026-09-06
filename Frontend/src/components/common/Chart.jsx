import React from 'react';
import { Bar, Line, Pie, Funnel } from 'recharts';

const Chart = ({ title, type, data }) => {
  // We'll create a simple chart based on the type
  // For simplicity, we'll assume data is in the format expected by recharts
  // In a real app, we would transform the data accordingly

  let chartContent = null;
  if (type === 'bar') {
    chartContent = (
      <BarChart data={data}>
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="value" fill="#8884d8" />
      </BarChart>
    );
  } else if (type === 'line') {
    chartContent = (
      <LineChart data={data}>
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="value" stroke="#82ca9d" />
      </LineChart>
    );
  } else if (type === 'pie') {
    chartContent = (
      <PieChart data={data}>
        <Tooltip />
        <Legend />
        <Pie dataKey="value" nameKey="name" cx="50%" cy="50%" labelLine={false} label={({ name, value, percent }) => `${name}: ${percent}%`} innerRadius={60} outerRadius={80} fill="#8884d8" />
      </PieChart>
    );
  } else if (type === 'funnel') {
    // We don't have a funnel chart in recharts, so we'll use a bar chart for now
    chartContent = (
      <BarChart data={data}>
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="value" fill="#8884d8" />
      </BarChart>
    );
  } else {
    chartContent = <div>Unsupported chart type</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-gray-500 mb-4">{title}</h3>
      <div className="h-64 w-full">{chartContent}</div>
    </div>
  );
};

// We need to define the chart components from recharts
const BarChart = ({ children, data, ...props }) => (
  <recharts.BarChart data={data} {...props}>
    {children}
  </recharts.BarChart>
);
const LineChart = ({ children, data, ...props }) => (
  <recharts.LineChart data={data} {...props}>
    {children}
  </recharts.LineChart>
);
const PieChart = ({ children, data, ...props }) => (
  <recharts.PieChart data={data} {...props}>
    {children}
  </recharts.PieChart>
);
const FunnelChart = ({ children, data, ...props }) => (
  <recharts.BarChart data={data} {...props}> {/* Using BarChart as placeholder for Funnel */}
    {children}
  </recharts.BarChart>
);

export default Chart;