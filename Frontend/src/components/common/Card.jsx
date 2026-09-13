import React from 'react';

const Card = ({ title, value, prefix = '', suffix = '', icon, trend, color = 'indigo' }) => {
  const colorMap = {
    indigo: { bg: 'rgba(99,102,241,0.12)', border: 'rgba(99,102,241,0.25)', accent: '#818cf8' },
    violet: { bg: 'rgba(139,92,246,0.12)', border: 'rgba(139,92,246,0.25)', accent: '#a78bfa' },
    emerald:{ bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.25)', accent: '#34d399' },
    amber:  { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.25)', accent: '#fbbf24' },
    rose:   { bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.25)',  accent: '#f87171' },
  };
  const c = colorMap[color] || colorMap.indigo;

  return (
    <div style={{
      background: 'rgba(15, 23, 42, 0.8)',
      border: `1px solid ${c.border}`,
      borderRadius: '1rem',
      padding: '1.25rem 1.5rem',
      backdropFilter: 'blur(12px)',
      transition: 'transform 0.2s ease, box-shadow 0.2s ease',
      cursor: 'default',
      position: 'relative',
      overflow: 'hidden',
    }}
    onMouseEnter={e => {
      e.currentTarget.style.transform = 'translateY(-2px)';
      e.currentTarget.style.boxShadow = `0 8px 32px ${c.bg}`;
    }}
    onMouseLeave={e => {
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.boxShadow = 'none';
    }}
    >
      {/* Glow orb */}
      <div style={{
        position: 'absolute', top: '-20px', right: '-20px',
        width: '80px', height: '80px',
        background: c.accent, borderRadius: '50%',
        filter: 'blur(32px)', opacity: 0.18,
        pointerEvents: 'none',
      }} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <p style={{ fontSize: '0.72rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '0.5rem' }}>
            {title}
          </p>
          <p style={{ fontSize: '1.9rem', fontWeight: 800, color: '#f1f5f9', lineHeight: 1.1, letterSpacing: '-0.02em' }}>
            {prefix}{typeof value === 'number' ? value.toLocaleString('en-IN') : value}{suffix}
          </p>
          {trend && (
            <p style={{ fontSize: '0.75rem', color: trend > 0 ? '#34d399' : '#f87171', marginTop: '0.35rem', fontWeight: 500 }}>
              {trend > 0 ? '▲' : '▼'} {Math.abs(trend)}% vs last month
            </p>
          )}
        </div>
        {icon && (
          <div style={{
            width: '2.5rem', height: '2.5rem', borderRadius: '0.75rem',
            background: c.bg, display: 'flex', alignItems: 'center',
            justifyContent: 'center', fontSize: '1.2rem',
            border: `1px solid ${c.border}`,
          }}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
};

export default Card;