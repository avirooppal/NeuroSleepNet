import React from 'react'

export default function MemoryHealth({ health, risk, activeTasks }) {
  return (
    <div style={{ backgroundColor: '#1e293b', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #334155' }}>
      <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.25rem', color: '#f1f5f9' }}>Memory Health</h2>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        <div>
          <div style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '0.25rem' }}>Global Health</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ flex: 1, height: '0.5rem', backgroundColor: '#334155', borderRadius: '9999px', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${Math.max(0, Math.min(100, health))}%`, backgroundColor: health > 80 ? '#10b981' : (health > 50 ? '#f59e0b' : '#ef4444'), transition: 'width 0.5s ease-out' }} />
            </div>
            <span style={{ fontWeight: 600, width: '3rem' }}>{Math.round(health)}%</span>
          </div>
        </div>

        <div>
          <div style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '0.25rem' }}>Forgetting Risk</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 600, color: risk > 0.1 ? '#ef4444' : '#10b981' }}>
            {risk > 0.1 ? '↑' : '↓'} {risk.toFixed(3)}
          </div>
        </div>

        <div>
           <div style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '0.25rem' }}>Active Tasks</div>
           <div style={{ fontSize: '1.125rem', fontWeight: 500 }}>{activeTasks} Loaded</div>
        </div>
        
        <div>
           <div style={{ color: '#94a3b8', fontSize: '0.875rem', marginBottom: '0.25rem' }}>Last Sleep Phase</div>
           <div style={{ fontSize: '1.125rem', fontWeight: 500 }}>2 min ago · 312 replayed</div>
        </div>
      </div>
      
      <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem' }}>
        <button style={{ backgroundColor: '#2563eb', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '0.25rem', fontWeight: 600, cursor: 'pointer' }}>Trigger Sleep Now</button>
        <button style={{ backgroundColor: 'transparent', color: '#94a3b8', border: '1px solid #475569', padding: '0.5rem 1rem', borderRadius: '0.25rem', fontWeight: 600, cursor: 'pointer' }}>View Replay Log</button>
      </div>
    </div>
  )
}
