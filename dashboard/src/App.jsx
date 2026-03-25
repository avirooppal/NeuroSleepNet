import { useState, useEffect } from 'react'
import MemoryHealth from './components/MemoryHealth'
import TaskChart from './components/TaskChart'

function App() {
  const [health, setHealth] = useState(84)
  const [tasks, setTasks] = useState([])
  const [risk, setRisk] = useState(0.01)

  useEffect(() => {
    fetch('http://localhost:8000/api/tasks')
      .then(res => res.json())
      .then(data => setTasks(data.tasks))
      .catch(err => console.error(err))

    const ws = new WebSocket('ws://localhost:8000/ws/live')
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setRisk(data.risk)
      setHealth(prev => Math.min(100, Math.max(0, prev - (data.risk * 10 - 0.5))))
    }
    return () => ws.close()
  }, [])

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', fontFamily: 'Inter, sans-serif' }}>
      <header style={{ borderBottom: '1px solid #334155', paddingBottom: '1rem', marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', color: '#f8fafc' }}>NeuroSleepNet Dashboard</h1>
        <div style={{ padding: '0.25rem 0.75rem', borderRadius: '9999px', backgroundColor: '#064e3b', color: '#34d399', fontSize: '0.875rem', fontWeight: 600 }}>
          {health > 80 ? '🟢 Healthy' : (health > 50 ? '🟡 Warning' : '🔴 Critical')}
        </div>
      </header>

      <main style={{ display: 'grid', gap: '2rem' }}>
        <MemoryHealth health={health} risk={risk} activeTasks={tasks.length} />
        <TaskChart tasks={tasks} />
      </main>
    </div>
  )
}

export default App
