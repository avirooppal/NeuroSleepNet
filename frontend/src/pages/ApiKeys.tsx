import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Plus, Trash2, Copy, CheckCircle, Key } from 'lucide-react';
import toast from 'react-hot-toast';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/v1';

export default function ApiKeys() {
  const [newLabel, setNewLabel] = useState('');
  const [creating, setCreating] = useState(false);
  const token = localStorage.getItem('nsn-token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  const qc = useQueryClient();

  const { data: keys = [] } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => fetch(`${API}/auth/api-key/list`, { headers }).then(r => r.json()),
  });

  const createKey = useMutation({
    mutationFn: (label: string) =>
      fetch(`${API}/auth/api-key/create`, { method: 'POST', headers, body: JSON.stringify({ label }) }).then(r => r.json()),
    onSuccess: () => { toast.success('API key created'); qc.invalidateQueries({ queryKey: ['api-keys'] }); setNewLabel(''); setCreating(false); },
  });

  const revokeKey = useMutation({
    mutationFn: (id: string) => fetch(`${API}/auth/api-key/${id}`, { method: 'DELETE', headers }),
    onSuccess: () => { toast.success('Key revoked'); qc.invalidateQueries({ queryKey: ['api-keys'] }); },
  });

  const copyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    toast.success('Key copied to clipboard ✓');
  };

  return (
    <div className="page-root">
      <div className="page-header">
        <h1 className="dashboard-title">API Keys</h1>
        <button className="create-btn" onClick={() => setCreating(true)}>
          <Plus size={14} /> New Key
        </button>
      </div>

      {creating && (
        <motion.div className="create-form" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
          <input className="memory-search-input" placeholder="Key label (e.g. production-v1)" value={newLabel} onChange={e => setNewLabel(e.target.value)} />
          <button className="create-btn" onClick={() => createKey.mutate(newLabel)} disabled={!newLabel.trim()}>Create</button>
          <button className="cancel-btn" onClick={() => setCreating(false)}>Cancel</button>
        </motion.div>
      )}

      <div className="keys-list">
        {(Array.isArray(keys) ? keys : []).map((k: any) => (
          <div key={k.id} className="key-card">
            <Key size={16} className="text-teal" />
            <div className="key-info">
              <div className="key-label">{k.label || 'Unnamed key'}</div>
              <div className="key-value">{k.key_preview ?? '•••••••••••••••••nsn_...'}  </div>
            </div>
            <div className="key-actions">
              <button className="mem-action-btn" onClick={() => copyKey(k.key ?? k.id)} title="Copy key">
                <Copy size={13} />
              </button>
              <button className="mem-action-btn danger" onClick={() => revokeKey.mutate(k.id)} title="Revoke key">
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ))}
        {(!Array.isArray(keys) || keys.length === 0) && (
          <div className="explorer-empty">No API keys yet. Create one to get started.</div>
        )}
      </div>
    </div>
  );
}
