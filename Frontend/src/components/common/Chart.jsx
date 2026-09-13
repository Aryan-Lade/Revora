import React from 'react';
import {
  BarChart, Bar,
  LineChart, Line,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

const COLORS = ['#818cf8', '#34d399', '#fbbf24', '#f87171', '#60a5fa', '#c084fc', '#fb923c'];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(99,102,241,0.3)',
        borderRadius: '0.625rem', padding: '0.6rem 0.9rem', fontSize: '0.8rem', color: '#e2e8f0',
        boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
      }}>
        <p style={{ fontWeight: 600, marginBottom: '0.3rem', color: '#a5b4fc' }}>{label}</p>
        {payload.map((p, i) => (
          <p key={i} style={{ color: p.color }}>
            {p.name}: {typeof p.value === 'number' ? `₹${p.value.toLocaleString('en-IN')}` : p.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

const Chart = ({ title, type, data }) => {
  const containerStyle = {
    background: 'rgba(15, 23, 42, 0.8)',
    border: '1px solid rgba(99,102,241,0.18)',
    borderRadius: '1rem',
    padding: '1.25rem 1.5rem',
    backdropFilter: 'blur(12px)',
  };

  const tickStyle = { fontSize: 11, fill: '#64748b' };
  const gridStyle = { stroke: 'rgba(100,116,139,0.15)', strokeDasharray: '3 3' };

  if (!data || data.length === 0) {
    return (
      <div style={containerStyle}>
        <h3 style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.75rem' }}>{title}</h3>
        <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: '0.85rem' }}>No data available</div>
      </div>
    );
  }

  let chart = null;

  if (type === 'bar') {
    const keys = Object.keys(data[0]).filter(k => k !== 'name');
    chart = (
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
          <CartesianGrid {...gridStyle} />
          <XAxis dataKey="name" tick={tickStyle} axisLine={false} tickLine={false} />
          <YAxis tick={tickStyle} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(99,102,241,0.07)' }} />
          {keys.length > 1 && <Legend wrapperStyle={{ fontSize: '0.75rem', color: '#64748b' }} />}
          {keys.map((k, i) => (
            <Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} radius={[5, 5, 0, 0]}
              opacity={0.85} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    );
  } else if (type === 'line') {
    const keys = Object.keys(data[0]).filter(k => k !== 'name');
    chart = (
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
          <CartesianGrid {...gridStyle} />
          <XAxis dataKey="name" tick={tickStyle} axisLine={false} tickLine={false} />
          <YAxis tick={tickStyle} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} />
          {keys.length > 1 && <Legend wrapperStyle={{ fontSize: '0.75rem', color: '#64748b' }} />}
          {keys.map((k, i) => (
            <Line key={k} type="monotone" dataKey={k} stroke={COLORS[i % COLORS.length]}
              strokeWidth={2.5} dot={false} activeDot={{ r: 5, stroke: 'rgba(15,23,42,0.8)', strokeWidth: 2 }} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  } else if (type === 'pie') {
    chart = (
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%"
            outerRadius={80} innerRadius={40}
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            labelLine={false}>
            {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  return (
    <div style={containerStyle}>
      <h3 style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.75rem' }}>
        {title}
      </h3>
      {chart}
    </div>
  );
};

export default Chart;
