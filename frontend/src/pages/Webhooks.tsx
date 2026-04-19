import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Trash2, RefreshCw, CheckCircle, XCircle, Webhook } from 'lucide-react';
import toast from 'react-hot-toast';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/v1';
const EVENT_TYPES = ['memory.stored', 'memory.archived', 'memory.expired', 'sleep.completed', 'quota.warning', 'benchmark.completed'];

export default function Webhooks() {
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ url: '', event_types: [] as string[], secret: '' });
  const token = localStorage.getItem('nsn-token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  const qc = useQueryClient();

  const { data: webhooks = [] } = useQuery({
    queryKey: ['webhooks'],
    queryFn: () => fetch(`${API}/webhooks/`, { headers }).then(r => r.json()),
  });

  const { data: deliveries = [] } = useQuery({
    queryKey: ['webhook-deliveries'],
    queryFn: () => fetch(`${API}/webhooks/deliveries?page_size=50`, { headers }).then(r => r.json()),
    refetchInterval: 15000,
  });

  const createWebhook = useMutation({
    mutationFn: () => fetch(`${API}/webhooks/?project_id=default`, {
      method: 'POST', headers, body: JSON.stringify(form),
    }).then(r => r.json()),
    onSuccess: () => { toast.success('Webhook registered'); qc.invalidateQueries({ queryKey: ['webhooks'] }); setShowCreate(false); },
  });

  const deleteWebhook = useMutation({
    mutationFn: (id: string) => fetch(`${API}/webhooks/${id}`, { method: 'DELETE', headers }),
    onSuccess: () => { toast.success('Webhook removed'); qc.invalidateQueries({ queryKey: ['webhooks'] }); },
  });

  const retryDelivery = useMutation({
    mutationFn: (id: string) => fetch(`${API}/webhooks/deliveries/${id}/retry`, { method: 'POST', headers }),
    onSuccess: () => { toast.success('Retry queued'); qc.invalidateQueries({ queryKey: ['webhook-deliveries'] }); },
  });

  const toggleEvent = (ev: string) => {
    setForm(f => ({
      ...f,
      event_types: f.event_types.includes(ev) ? f.event_types.filter(e => e !== ev) : [...f.event_types, ev],
    }));
  };

  return (
    <div className="page-root">
      <div className="page-header">
        <h1 className="dashboard-title">Webhooks</h1>
        <button className="create-btn" onClick={() => setShowCreate(s => !s)}><Plus size={14} /> Register</button>
      </div>

      <AnimatePresence>
        {showCreate && (
          <motion.div className="create-form" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <input className="memory-search-input" placeholder="https://your-server.com/webhook" value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))} />
            <input className="memory-search-input" placeholder="HMAC secret (optional)" value={form.secret} onChange={e => setForm(f => ({ ...f, secret: e.target.value }))} />
            <div className="event-checkboxes">
              {EVENT_TYPES.map(ev => (
                <label key={ev} className="event-checkbox-label">
                  <input type="checkbox" checked={form.event_types.includes(ev)} onChange={() => toggleEvent(ev)} />
                  <span>{ev}</span>
                </label>
              ))}
            </div>
            <div className="form-actions">
              <button className="create-btn" onClick={() => createWebhook.mutate()} disabled={!form.url}>Save</button>
              <button className="cancel-btn" onClick={() => setShowCreate(false)}>Cancel</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="section-title">Registered Endpoints</div>
      <div className="keys-list">
        {(Array.isArray(webhooks) ? webhooks : []).map((wh: any) => (
          <div key={wh.id} className="key-card">
            <Webhook size={16} className="text-teal" />
            <div className="key-info">
              <div className="key-label">{wh.url}</div>
              <div className="key-value text-xs">{(wh.event_types ?? []).join(', ') || 'All events'}</div>
            </div>
            <span className={`is-active-badge ${wh.is_active ? 'active' : 'inactive'}`}>{wh.is_active ? 'Active' : 'Inactive'}</span>
            <button className="mem-action-btn danger" onClick={() => deleteWebhook.mutate(wh.id)}><Trash2 size={13} /></button>
          </div>
        ))}
      </div>

      <div className="section-title mt-8">Delivery Log</div>
      <div className="deliveries-table">
        <div className="delivery-header-row">
          <span>Event</span><span>Status</span><span>Attempts</span><span>Delivered</span><span>Error</span><span></span>
        </div>
        {(Array.isArray(deliveries) ? deliveries : []).map((d: any) => (
          <div key={d.id} className="delivery-row">
            <span className="delivery-event">{d.event}</span>
            <span>{d.succeeded ? <CheckCircle size={13} className="text-teal" /> : <XCircle size={13} className="text-red" />}</span>
            <span className="text-muted">{d.attempt_count}</span>
            <span className="text-muted text-xs">{new Date(d.delivered_at).toLocaleString()}</span>
            <span className="text-muted text-xs truncate max-w-48">{d.last_error ?? '—'}</span>
            {!d.succeeded && (
              <button className="mem-action-btn" onClick={() => retryDelivery.mutate(d.id)} title="Retry"><RefreshCw size={12} /></button>
            )}
          </div>
        ))}
        {(!Array.isArray(deliveries) || deliveries.length === 0) && (
          <div className="explorer-empty">No deliveries yet.</div>
        )}
      </div>
    </div>
  );
}
