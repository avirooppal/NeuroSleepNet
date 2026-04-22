import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { SlidersHorizontal, Save, Plus, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/v1';

function WeightSlider({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div className="weight-slider-row">
      <span className="weight-label">{label}</span>
      <input type="range" min={0} max={1} step={0.01} value={value} onChange={e => onChange(parseFloat(e.target.value))} className="weight-input" />
      <span className="weight-val" style={{ color: '#00e5cc' }}>{value.toFixed(2)}</span>
    </div>
  );
}

export default function Projects() {
  const token = localStorage.getItem('nsn-token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  const qc = useQueryClient();
  const [newName, setNewName] = useState('');
  const [weights, setWeights] = useState({ w1: 0.50, w2: 0.20, w3: 0.20, w4: 0.10 });
  const [editingId, setEditingId] = useState<string | null>(null);

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: () => fetch(`${API}/projects`, { headers }).then(r => r.json()),
  });

  const createProject = useMutation({
    mutationFn: () => fetch(`${API}/projects`, { method: 'POST', headers, body: JSON.stringify({ name: newName }) }).then(r => r.json()),
    onSuccess: () => { toast.success('Project created'); qc.invalidateQueries({ queryKey: ['projects'] }); setNewName(''); },
  });

  const saveWeights = useMutation({
    mutationFn: (id: string) => fetch(`${API}/projects/${id}`, {
      method: 'PATCH', headers, body: JSON.stringify({ attention_weights: weights }),
    }).then(r => r.json()),
    onSuccess: () => { toast.success('Attention weights saved'); setEditingId(null); },
  });

  const deleteProject = useMutation({
    mutationFn: (id: string) => fetch(`${API}/projects/${id}`, { method: 'DELETE', headers }),
    onSuccess: () => { toast.success('Project deleted'); qc.invalidateQueries({ queryKey: ['projects'] }); },
  });

  const totalWeight = Object.values(weights).reduce((a, b) => a + b, 0);

  return (
    <div className="page-root">
      <div className="page-header">
        <h1 className="dashboard-title">Projects</h1>
        <div className="search-row" style={{ flex: 1, maxWidth: 280 }}>
          <input className="memory-search-input" placeholder="New project name…" value={newName} onChange={e => setNewName(e.target.value)} />
          <button className="create-btn" onClick={() => createProject.mutate()} disabled={!newName.trim()}><Plus size={14} /></button>
        </div>
      </div>

      <div className="keys-list">
        {(Array.isArray(projects) ? projects : []).map((p: any) => (
          <div key={p.id} className="key-card flex-col items-start gap-2">
            <div className="flex w-full items-center justify-between">
              <div>
                <div className="key-label">{p.name}</div>
                <div className="key-value text-xs">{p.id}</div>
              </div>
              <div className="flex gap-2">
                <button className="mem-action-btn" onClick={() => { setEditingId(p.id); setWeights(p.attention_weights ?? weights); }} title="Edit weights">
                  <SlidersHorizontal size={13} />
                </button>
                <button className="mem-action-btn danger" onClick={() => deleteProject.mutate(p.id)}><Trash2 size={13} /></button>
              </div>
            </div>

            {editingId === p.id && (
              <motion.div className="weights-editor w-full" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}>
                <div className="weights-title">Attention Weights <span className={`weight-total ${Math.abs(totalWeight - 1) > 0.01 ? 'text-amber' : 'text-teal'}`}>(sum: {totalWeight.toFixed(2)})</span></div>
                <WeightSlider label="w1 — Semantic (CosineSim)" value={weights.w1} onChange={v => setWeights(w => ({ ...w, w1: v }))} />
                <WeightSlider label="w2 — Recency" value={weights.w2} onChange={v => setWeights(w => ({ ...w, w2: v }))} />
                <WeightSlider label="w3 — Consolidation" value={weights.w3} onChange={v => setWeights(w => ({ ...w, w3: v }))} />
                <WeightSlider label="w4 — Importance boost" value={weights.w4} onChange={v => setWeights(w => ({ ...w, w4: v }))} />
                <button className="create-btn mt-2" onClick={() => saveWeights.mutate(p.id)}><Save size={12} /> Save weights</button>
              </motion.div>
            )}
          </div>
        ))}
        {(!Array.isArray(projects) || projects.length === 0) && <div className="explorer-empty">No projects yet.</div>}
      </div>
    </div>
  );
}
