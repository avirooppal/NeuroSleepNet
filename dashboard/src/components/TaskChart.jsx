import React from 'react'

export default function TaskChart({ tasks }) {
  if (!tasks || tasks.length === 0) {
    return (
      <div style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
        <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.25rem', color: '#f1f5f9' }}>Task Performance Over Time</h2>
        <div style={{ color: '#94a3b8' }}>Loading tasks...</div>
      </div>
    )
  }

  return (
    <div style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
      <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.25rem', color: '#f1f5f9' }}>Task Performance Over Time</h2>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {tasks.map(t => (
          <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ width: '5rem', fontWeight: 500, color: t.status === 'active' ? '#60a5fa' : '#cbd5e1' }}>
              {t.id} {t.status === 'active' ? '(act)' : ''}
            </div>
            <div style={{ flex: 1, height: '0.5rem', backgroundColor: '#334155', borderRadius: '9999px', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${t.accuracy * 100}%`, backgroundColor: t.status === 'active' ? '#3b82f6' : '#64748b' }} />
            </div>
            <div style={{ width: '3rem', textAlign: 'right', fontWeight: 600 }}>
              {Math.round(t.accuracy * 100)}%
            </div>
            <div style={{ width: '1.5rem', textAlign: 'center' }}>
              {t.accuracy >= 0.85 ? '✅' : '⚠️'}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
