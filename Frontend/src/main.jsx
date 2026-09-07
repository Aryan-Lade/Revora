import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('Revora crashed:', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', minHeight: '100vh', padding: '2rem',
          fontFamily: 'monospace', background: '#0f172a', color: '#f8fafc',
        }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1rem', color: '#ef4444' }}>
            ⚡ Revora — Runtime Error
          </h1>
          <pre style={{
            background: '#1e293b', padding: '1.5rem', borderRadius: '0.5rem',
            maxWidth: '800px', width: '100%', overflow: 'auto',
            fontSize: '0.8rem', color: '#fca5a5',
          }}>
            {this.state.error.toString()}
            {'\n\n'}
            {this.state.error.stack}
          </pre>
          <button
            onClick={() => this.setState({ error: null })}
            style={{
              marginTop: '1.5rem', padding: '0.6rem 1.5rem',
              background: '#3b82f6', color: 'white', border: 'none',
              borderRadius: '0.375rem', cursor: 'pointer', fontSize: '0.9rem',
            }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
