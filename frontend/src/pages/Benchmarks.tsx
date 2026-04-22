import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, CheckCircle, Clock, ExternalLink } from 'lucide-react';
import toast from 'react-hot-toast';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/v1';
const MODELS = ['gpt-4o-mini', 'gpt-3.5-turbo', 'llama-3.2-3b', 'mistral-7b', 'claude-3-haiku'];
const SCENARIOS = ['all', 'multi-turn-recall', 'cross-session', 'catastrophic-forgetting', 'slm-amplification', 'attention-precision'];

export default function Benchmarks() {
  const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');
  const [selectedScenario, setSelectedScenario] = useState('all');
  const [runningId, setRunningId] = useState<string | null>(null);
  const token = localStorage.getItem('nsn-token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  const { data: history = [] } = useQuery({
    queryKey: ['benchmark-history'],
    queryFn: () => fetch(`${API}/benchmark/`, { headers }).then(r => r.json()),
    refetchInterval: runningId ? 5000 : 30000,
  });

  const { data: currentRun } = useQuery({
    queryKey: ['benchmark-run', runningId],
    queryFn: () => fetch(`${API}/benchmark/${runningId}`, { headers }).then(r => r.json()),
    enabled: !!runningId,
    refetchInterval: 3000,
    onSuccess: (data: any) => {
      if (data?.status === 'completed') setRunningId(null);
    },
  });

  const startRun = useMutation({
    mutationFn: () => fetch(`${API}/benchmark/run`, {
      method: 'POST', headers,
      body: JSON.stringify({ model: selectedModel, scenario: selectedScenario }),
    }).then(r => r.json()),
    onSuccess: (data: any) => {
      if (data?.run_id) { setRunningId(data.run_id); toast.success('Benchmark started'); }
    },
    onError: () => toast.error('Failed to start benchmark'),
  });

  const copyBadge = (runId: string) => {
    const url = `${API}/benchmark/${runId}/badge`;
    navigator.clipboard.writeText(`![NSN Benchmark](${url})`);
    toast.success('Badge markdown copied ✓');
  };

  return (
    <div className="page-root">
      <h1 className="dashboard-title">Benchmarks</h1>
      <p className="dashboard-subtitle">Run reproducible memory benchmarks. Every report includes the exact reproduce command.</p>

      <div className="benchmark-config-card">
        <div className="flex gap-4 flex-wrap items-end">
          <div>
            <label className="config-label">Model</label>
            <select className="sort-select" value={selectedModel} onChange={e => setSelectedModel(e.target.value)}>
              {MODELS.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          <div>
            <label className="config-label">Scenario</label>
            <select className="sort-select" value={selectedScenario} onChange={e => setSelectedScenario(e.target.value)}>
              {SCENARIOS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <button className="create-btn" onClick={() => startRun.mutate()} disabled={!!runningId}>
            {runningId ? <><Clock size={13} className="animate-spin" /> Running…</> : <><Play size={13} /> Run Benchmark</>}
          </button>
        </div>
      </div>

      {/* Live progress */}
      <AnimatePresence>
        {runningId && currentRun && (
          <motion.div className="benchmark-running-card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <div className="running-label"><Clock size={14} className="animate-spin" /> Running — {currentRun.scenario} on {currentRun.model}</div>
            <div className="running-bar-bg"><motion.div className="running-bar" style={{ width: `${currentRun.progress ?? 30}%` }} /></div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* History */}
      <div className="section-title mt-8">Run History</div>
      <div className="benchmark-list">
        {(Array.isArray(history) ? history : []).map((run: any) => (
          <div key={run.id} className="benchmark-card">
            <div className="benchmark-card-header">
              <span className="bench-model">{run.model}</span>
              <span className="bench-scenario">{run.scenario}</span>
              <span className={`bench-status ${run.status}`}>{run.status}</span>
            </div>
            {run.status === 'completed' && (
              <div className="bench-results">
                <div className="bench-score-row">
                  <span>With NSN</span><span className="text-teal font-bold">{(run.score * 100).toFixed(0)}%</span>
                </div>
                {run.control_score !== undefined && (
                  <div className="bench-score-row">
                    <span>Without NSN</span><span className="text-muted">{(run.control_score * 100).toFixed(0)}%</span>
                  </div>
                )}
                <div className="bench-reproduce text-xs text-muted">
                  Reproduce: <code>nsn-bench run --model {run.model} --scenario {run.scenario} --seed {run.run_key}</code>
                </div>
              </div>
            )}
            <div className="bench-actions">
              {run.status === 'completed' && (
                <button className="mem-action-btn text-xs" onClick={() => copyBadge(run.id)}>📋 Badge</button>
              )}
            </div>
          </div>
        ))}
        {(!Array.isArray(history) || history.length === 0) && <div className="explorer-empty">No benchmark runs yet.</div>}
      </div>
    </div>
  );
}
