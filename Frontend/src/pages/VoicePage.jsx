import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

const InfoBox = ({ label, value, color }) => (
  <div style={{
    background: 'rgba(15,23,42,0.6)',
    border: '1px solid rgba(99,102,241,0.18)',
    borderRadius: '0.75rem',
    padding: '0.875rem 1rem',
    textAlign: 'center'
  }}>
    <div style={{ fontSize: '0.68rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '0.3rem' }}>
      {label}
    </div>
    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: color || '#e2e8f0' }}>
      {value}
    </div>
  </div>
);

const VoicePage = () => {
  const [refetchKey, setRefetchKey] = useState(0);
  const { data: voiceSessions, loading } = useApi('/api/voice/sessions', refetchKey);
  const { data: voiceHealth, loading: hLoad } = useApi('/api/voice/health', refetchKey);
  const { data: casesData } = useApi('/api/recovery/cases', refetchKey);

  const [selectedCaseId, setSelectedCaseId] = useState('1');
  const [callLoading, setCallLoading] = useState(false);
  const [callResult, setCallResult] = useState(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [viewingTranscriptSession, setViewingTranscriptSession] = useState(null);

  const cases = Array.isArray(casesData) ? casesData : [];
  const sessions = Array.isArray(voiceSessions) ? voiceSessions : [];

  const handleDemoCall = async (bypassPolicy = false) => {
    const cid = parseInt(selectedCaseId, 10);
    if (!cid) return alert('Please select or enter a valid Case ID');
    setCallLoading(true);
    setCallResult(null);

    try {
      const url = `${API_BASE}/api/voice/start?recovery_case_id=${cid}&customer_id=1&bypass_policy=${bypassPolicy}`;
      const res = await fetch(url, { method: 'POST' });
      const data = await res.json();
      setCallResult(data);
      setRefetchKey(k => k + 1);
    } catch (e) {
      setCallResult({ error: e.message });
    } finally {
      setCallLoading(false);
    }
  };

  const handleSpeakTranscript = (transcript) => {
    if (!('speechSynthesis' in window)) {
      alert('Speech synthesis is not supported in this browser.');
      return;
    }
    if (isPlayingAudio) {
      window.speechSynthesis.cancel();
      setIsPlayingAudio(false);
      return;
    }

    setIsPlayingAudio(true);
    const utterLines = (transcript || []).filter(t => t.role !== 'system');
    let idx = 0;

    const speakNext = () => {
      if (idx >= utterLines.length) {
        setIsPlayingAudio(false);
        return;
      }
      const line = utterLines[idx];
      const u = new SpeechSynthesisUtterance(line.text);
      u.rate = 1.0;
      u.pitch = line.role === 'agent' ? 1.05 : 0.95;
      u.onend = () => {
        idx++;
        speakNext();
      };
      u.onerror = () => {
        setIsPlayingAudio(false);
      };
      window.speechSynthesis.speak(u);
    };

    speakNext();
  };

  if (loading || hLoad) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ width: 44, height: 44, border: '3px solid rgba(99,102,241,0.15)', borderTopColor: '#818cf8', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 1rem' }} />
        <p style={{ color: '#475569', fontSize: '0.875rem' }}>Loading voice data...</p>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  const card = {
    background: 'rgba(15, 23, 42, 0.8)',
    border: '1px solid rgba(99,102,241,0.18)',
    borderRadius: '1rem',
    padding: '1.25rem 1.5rem',
    marginBottom: '1.25rem',
    backdropFilter: 'blur(12px)',
  };

  const th = {
    padding: '0.75rem 1rem',
    fontSize: '0.7rem',
    fontWeight: 600,
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.07em'
  };

  return (
    <div>
      <div style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
          🎙️ Autonomous Voice AI
        </h1>
        <p style={{ fontSize: '0.875rem', color: '#64748b' }}>
          AI-powered conversational recovery calls with real-time intent classification & promise-to-pay recording.
        </p>
      </div>

      {/* Provider Health */}
      <div style={card}>
        <h2 style={{ fontSize: '0.8rem', fontWeight: 600, color: '#818cf8', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '1rem' }}>
          Voice Provider Health & Metrics
        </h2>
        {voiceHealth ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem' }}>
            <InfoBox label="Provider" value={voiceHealth.provider ?? 'DEMO'} color="#818cf8" />
            <InfoBox label="Status" value={voiceHealth.status ?? 'HEALTHY'} color="#34d399" />
            <InfoBox label="Avg Latency" value={`${voiceHealth.latency_ms ?? 0} ms`} color="#38bdf8" />
            <InfoBox label="Start Latency" value={`${voiceHealth.call_start_latency_ms ?? 0} ms`} color="#a78bfa" />
            <InfoBox label="Total Calls" value={voiceHealth.total_calls ?? 0} />
            <InfoBox label="Recovered" value={voiceHealth.success_count ?? 0} color="#34d399" />
          </div>
        ) : (
          <p style={{ color: '#64748b', fontSize: '0.875rem' }}>No health data available.</p>
        )}
      </div>

      {/* Interactive Demo Call Simulator */}
      <div style={{ ...card, border: '1px solid rgba(129,140,248,0.3)', background: 'linear-gradient(180deg, rgba(15,23,42,0.95) 0%, rgba(30,27,75,0.2) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.2rem' }}>
              ⚡ Interactive Voice Call Simulator
            </h2>
            <p style={{ fontSize: '0.825rem', color: '#94a3b8' }}>
              Simulate an AI outbound voice call to a customer with a failed subscription.
            </p>
          </div>
          <span style={{ padding: '0.3rem 0.8rem', borderRadius: '2rem', fontSize: '0.75rem', fontWeight: 600, background: 'rgba(52,211,153,0.15)', color: '#34d399', border: '1px solid rgba(52,211,153,0.3)' }}>
            ● AI Ready
          </span>
        </div>

        {/* Case selector */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center', marginBottom: '1rem' }}>
          <div style={{ flex: '1 1 280px' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '0.35rem' }}>
              Select Recovery Case:
            </label>
            <select
              value={selectedCaseId}
              onChange={e => setSelectedCaseId(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(15,23,42,0.9)',
                border: '1px solid rgba(99,102,241,0.35)',
                borderRadius: '0.625rem',
                padding: '0.6rem 0.875rem',
                fontSize: '0.85rem',
                color: '#f8fafc',
                outline: 'none',
              }}
            >
              {cases.length > 0 ? (
                cases.map(c => (
                  <option key={c.id} value={c.id} style={{ background: '#0f172a', color: '#f8fafc' }}>
                    Case #{c.id} — {c.customer?.name || `Customer #${c.customer_id}`} (₹{Number(c.amount_at_risk || 0).toLocaleString('en-IN')}) [{c.risk_score || 'Risk'}]
                  </option>
                ))
              ) : (
                <>
                  <option value="1">Case #1 — Rahul Sharma (₹4,999) [CRITICAL]</option>
                  <option value="2">Case #2 — Amit Verma (₹35,000) [HIGH]</option>
                  <option value="3">Case #3 — Neha Singh (₹4,999) [MEDIUM]</option>
                  <option value="4">Case #4 — Rohit Mehta (₹4,499) [LOW]</option>
                </>
              )}
            </select>
          </div>

          <div style={{ alignSelf: 'flex-end', display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => handleDemoCall(false)}
              disabled={callLoading}
              style={{
                padding: '0.625rem 1.25rem',
                background: callLoading ? 'rgba(99,102,241,0.3)' : 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                color: '#fff',
                border: 'none',
                borderRadius: '0.625rem',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: callLoading ? 'not-allowed' : 'pointer',
                boxShadow: '0 4px 16px rgba(99,102,241,0.35)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              {callLoading ? '⏳ Calling Customer...' : '📞 Start Demo Call'}
            </button>

            <button
              onClick={() => handleDemoCall(true)}
              disabled={callLoading}
              title="Runs call even during Quiet Hours (22:00-08:00 IST) for hackathon demo testing"
              style={{
                padding: '0.625rem 1rem',
                background: 'rgba(245, 158, 11, 0.15)',
                color: '#fbbf24',
                border: '1px solid rgba(245, 158, 11, 0.4)',
                borderRadius: '0.625rem',
                fontSize: '0.825rem',
                fontWeight: 600,
                cursor: callLoading ? 'not-allowed' : 'pointer',
              }}
            >
              ⚡ Force Call (Demo Override)
            </button>
          </div>
        </div>

        {/* Call Result / Dialog Simulation */}
        {callResult && (
          <div style={{
            marginTop: '1.25rem',
            padding: '1.25rem',
            background: 'rgba(10, 15, 30, 0.9)',
            border: callResult.blocked ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid rgba(52, 211, 153, 0.3)',
            borderRadius: '0.875rem',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
          }}>
            {/* If Policy Blocked */}
            {callResult.blocked ? (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '1.25rem' }}>🛡️</span>
                    <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fbbf24' }}>
                      Policy Guardrail Active — Call Blocked
                    </span>
                  </div>
                  <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '0.2rem 0.6rem', borderRadius: '1rem', background: 'rgba(245,158,11,0.2)', color: '#fbbf24' }}>
                    RULE: {callResult.blocked_by || 'SAFETY_CHECK'}
                  </span>
                </div>
                <p style={{ fontSize: '0.825rem', color: '#cbd5e1', marginBottom: '0.75rem', lineHeight: '1.5' }}>
                  <strong>Reason:</strong> {callResult.reason}
                </p>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(245, 158, 11, 0.08)', padding: '0.75rem 1rem', borderRadius: '0.5rem', border: '1px dashed rgba(245,158,11,0.3)' }}>
                  <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                    💡 <em>Want to see the AI conversational dialogue anyway for demo testing?</em>
                  </span>
                  <button
                    onClick={() => handleDemoCall(true)}
                    disabled={callLoading}
                    style={{
                      background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '0.5rem',
                      padding: '0.4rem 0.9rem',
                      fontSize: '0.78rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    ⚡ Test Call Dialogue Now
                  </button>
                </div>
              </div>
            ) : callResult.error ? (
              <div style={{ color: '#f87171', fontSize: '0.875rem' }}>
                ❌ Error: {callResult.error}
              </div>
            ) : (
              /* If Call Succeeded */
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(99,102,241,0.18)', paddingBottom: '0.75rem', marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#34d399', boxShadow: '0 0 10px #34d399' }} />
                    <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc' }}>
                      Call Completed with {callResult.customer_name || 'Customer'}
                    </span>
                    <span style={{ fontSize: '0.7rem', padding: '0.2rem 0.6rem', borderRadius: '1rem', background: 'rgba(99,102,241,0.2)', color: '#818cf8', fontWeight: 600 }}>
                      Intent: {callResult.intent || callResult.status}
                    </span>
                  </div>

                  {callResult.transcript && callResult.transcript.length > 0 && (
                    <button
                      onClick={() => handleSpeakTranscript(callResult.transcript)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.4rem',
                        padding: '0.35rem 0.8rem',
                        background: isPlayingAudio ? 'rgba(239,68,68,0.2)' : 'rgba(99,102,241,0.2)',
                        color: isPlayingAudio ? '#f87171' : '#a5b4fc',
                        border: '1px solid rgba(99,102,241,0.3)',
                        borderRadius: '0.5rem',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                    >
                      {isPlayingAudio ? '⏹ Stop Audio' : '🔊 Listen Audio (Browser TTS)'}
                    </button>
                  )}
                </div>

                {/* Call outcome metrics */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.5rem', marginBottom: '1.25rem' }}>
                  <div style={{ background: 'rgba(15,23,42,0.6)', padding: '0.5rem 0.75rem', borderRadius: '0.5rem', border: '1px solid rgba(99,102,241,0.1)' }}>
                    <div style={{ fontSize: '0.68rem', color: '#64748b' }}>STATUS</div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#34d399' }}>{callResult.status}</div>
                  </div>
                  <div style={{ background: 'rgba(15,23,42,0.6)', padding: '0.5rem 0.75rem', borderRadius: '0.5rem', border: '1px solid rgba(99,102,241,0.1)' }}>
                    <div style={{ fontSize: '0.68rem', color: '#64748b' }}>PAID ON CALL</div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: callResult.paid ? '#34d399' : '#94a3b8' }}>
                      {callResult.paid ? `✓ Yes (₹${Number(callResult.recovered_amount || 0).toLocaleString('en-IN')})` : '✗ No'}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(15,23,42,0.6)', padding: '0.5rem 0.75rem', borderRadius: '0.5rem', border: '1px solid rgba(99,102,241,0.1)' }}>
                    <div style={{ fontSize: '0.68rem', color: '#64748b' }}>PROMISE RECORDED</div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: callResult.promise_id ? '#38bdf8' : '#94a3b8' }}>
                      {callResult.promise_id ? `✓ Date: ${callResult.promised_date ? new Date(callResult.promised_date).toLocaleDateString() : 'Recorded'}` : 'None'}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(15,23,42,0.6)', padding: '0.5rem 0.75rem', borderRadius: '0.5rem', border: '1px solid rgba(99,102,241,0.1)' }}>
                    <div style={{ fontSize: '0.68rem', color: '#64748b' }}>CALL LATENCY</div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#e2e8f0' }}>{callResult.call_start_latency_ms} ms</div>
                  </div>
                </div>

                {/* Live Conversation Transcript */}
                {callResult.transcript && callResult.transcript.length > 0 && (
                  <div>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#818cf8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.6rem' }}>
                      💬 Call Dialogue Transcript ({callResult.transcript.length} turns)
                    </div>
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.6rem',
                      maxHeight: '300px',
                      overflowY: 'auto',
                      paddingRight: '0.5rem'
                    }}>
                      {callResult.transcript.map((line, idx) => {
                        const isAgent = line.role === 'agent';
                        const isSys = line.role === 'system';
                        if (isSys) {
                          return (
                            <div key={idx} style={{ textAlign: 'center', fontSize: '0.75rem', color: '#64748b', fontStyle: 'italic', margin: '0.2rem 0' }}>
                              — {line.text} —
                            </div>
                          );
                        }
                        return (
                          <div
                            key={idx}
                            style={{
                              alignSelf: isAgent ? 'flex-start' : 'flex-end',
                              maxWidth: '82%',
                              background: isAgent ? 'rgba(99,102,241,0.15)' : 'rgba(52,211,153,0.12)',
                              border: isAgent ? '1px solid rgba(99,102,241,0.3)' : '1px solid rgba(52,211,153,0.25)',
                              borderRadius: '0.75rem',
                              padding: '0.6rem 0.875rem',
                            }}
                          >
                            <div style={{ fontSize: '0.68rem', fontWeight: 700, color: isAgent ? '#a5b4fc' : '#6ee7b7', marginBottom: '0.2rem' }}>
                              {isAgent ? '🎙️ Revora AI (Agent)' : '👤 Customer'}
                            </div>
                            <div style={{ fontSize: '0.825rem', color: '#f1f5f9', lineHeight: '1.4' }}>
                              {line.text}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modal / Section for inspecting past session transcript */}
      {viewingTranscriptSession && (
        <div style={{
          ...card,
          border: '1px solid rgba(129,140,248,0.4)',
          background: 'rgba(15,23,42,0.95)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc' }}>
              📜 Full Transcript — Case #{viewingTranscriptSession.recovery_case_id} (Session #{viewingTranscriptSession.id})
            </h3>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {viewingTranscriptSession.transcript && (
                <button
                  onClick={() => handleSpeakTranscript(viewingTranscriptSession.transcript)}
                  style={{
                    padding: '0.3rem 0.75rem',
                    background: 'rgba(99,102,241,0.2)',
                    color: '#a5b4fc',
                    border: '1px solid rgba(99,102,241,0.3)',
                    borderRadius: '0.5rem',
                    fontSize: '0.75rem',
                    cursor: 'pointer'
                  }}
                >
                  🔊 Listen
                </button>
              )}
              <button
                onClick={() => setViewingTranscriptSession(null)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  fontSize: '1rem',
                  cursor: 'pointer'
                }}
              >
                ✕ Close
              </button>
            </div>
          </div>

          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
            maxHeight: '260px',
            overflowY: 'auto'
          }}>
            {Array.isArray(viewingTranscriptSession.transcript) && viewingTranscriptSession.transcript.length > 0 ? (
              viewingTranscriptSession.transcript.map((line, idx) => (
                <div
                  key={idx}
                  style={{
                    alignSelf: line.role === 'agent' ? 'flex-start' : 'flex-end',
                    maxWidth: '85%',
                    background: line.role === 'agent' ? 'rgba(99,102,241,0.15)' : 'rgba(52,211,153,0.12)',
                    border: line.role === 'agent' ? '1px solid rgba(99,102,241,0.3)' : '1px solid rgba(52,211,153,0.25)',
                    borderRadius: '0.75rem',
                    padding: '0.5rem 0.8rem',
                  }}
                >
                  <div style={{ fontSize: '0.68rem', fontWeight: 700, color: line.role === 'agent' ? '#a5b4fc' : '#6ee7b7', marginBottom: '0.15rem' }}>
                    {line.role === 'agent' ? '🎙️ Revora AI' : line.role === 'system' ? '⚙️ System' : '👤 Customer'}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#f1f5f9' }}>{line.text}</div>
                </div>
              ))
            ) : (
              <p style={{ color: '#64748b', fontSize: '0.825rem' }}>No transcript recorded for this session.</p>
            )}
          </div>
        </div>
      )}

      {/* Sessions Table */}
      <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.875rem' }}>
        Voice Call History & Session Logs {sessions.length > 0 && <span style={{ color: '#64748b', fontWeight: 400 }}>({sessions.length})</span>}
      </h2>

      {sessions.length === 0 ? (
        <div style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.15)', borderRadius: '1rem', padding: '3rem', textAlign: 'center', color: '#64748b' }}>
          <p style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>🎙️</p>
          <p>No voice sessions yet. Use the Interactive Demo Call above to test one.</p>
        </div>
      ) : (
        <div style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.15)', borderRadius: '1rem', overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(99,102,241,0.15)' }}>
                  {['Session ID', 'Case ID', 'Status', 'Intent', 'Channel', 'Start Latency', 'Started At', 'Promise', 'Recovered', 'Action'].map(h => (
                    <th key={h} style={th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sessions.map((s, i) => (
                  <tr key={s.id ?? i} style={{ borderBottom: '1px solid rgba(99,102,241,0.08)', transition: 'background 0.15s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(99,102,241,0.06)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#64748b' }}>#{s.id}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#e2e8f0', fontWeight: 600 }}>Case #{s.recovery_case_id}</td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <span style={{ padding: '0.2rem 0.65rem', borderRadius: '2rem', fontSize: '0.7rem', fontWeight: 600, background: 'rgba(99,102,241,0.15)', color: '#a5b4fc', border: '1px solid rgba(99,102,241,0.3)' }}>
                        {s.status}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#94a3b8' }}>{s.intent ?? '—'}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: s.warm ? '#34d399' : '#64748b' }}>{s.warm ? '✓ Warm Pool' : 'Cold'}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: '#94a3b8' }}>{s.call_start_latency_ms} ms</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.775rem', color: '#64748b' }}>{new Date(s.started_at).toLocaleString()}</td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', color: s.promise_created ? '#38bdf8' : '#475569' }}>
                      {s.promise_created ? '✓ Yes' : '—'}
                    </td>
                    <td style={{ padding: '0.75rem 1rem', fontSize: '0.825rem', fontWeight: 600, color: s.recovered_amount > 0 ? '#34d399' : '#64748b' }}>
                      ₹{Number(s.recovered_amount ?? 0).toLocaleString('en-IN')}
                    </td>
                    <td style={{ padding: '0.75rem 1rem' }}>
                      <button
                        onClick={() => setViewingTranscriptSession(s)}
                        style={{
                          background: 'rgba(99,102,241,0.15)',
                          border: '1px solid rgba(99,102,241,0.3)',
                          borderRadius: '0.4rem',
                          color: '#818cf8',
                          padding: '0.25rem 0.6rem',
                          fontSize: '0.725rem',
                          cursor: 'pointer'
                        }}
                      >
                        👁️ Transcript
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default VoicePage;
