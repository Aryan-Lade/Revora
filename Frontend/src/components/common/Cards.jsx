import React from 'react';

const Cards = ({ title, value, icon }) => {
  return (
    <div style={{
      background: 'rgba(15, 23, 42, 0.7)',
      border: '1px solid rgba(99,102,241,0.18)',
      borderRadius: '0.875rem',
      padding: '1rem 1.25rem',
      backdropFilter: 'blur(12px)',
      transition: 'transform 0.2s ease, border-color 0.2s ease',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.35rem',
    }}
    onMouseEnter={e => {
      e.currentTarget.style.transform = 'translateY(-2px)';
      e.currentTarget.style.borderColor = 'rgba(129,140,248,0.4)';
    }}
    onMouseLeave={e => {
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.borderColor = 'rgba(99,102,241,0.18)';
    }}
    >
      <p style={{ fontSize: '0.7rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
        {icon && <span style={{ marginRight: '0.3rem' }}>{icon}</span>}{title}
      </p>
      <p style={{ fontSize: '1.6rem', fontWeight: 800, color: '#e2e8f0', letterSpacing: '-0.02em' }}>
        {value}
      </p>
    </div>
  );
};

export default Cards;