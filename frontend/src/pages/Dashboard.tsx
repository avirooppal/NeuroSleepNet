import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';
import { Brain, Zap, Moon, AlertTriangle, Search, Play, Clock, TrendingUp, Database, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/v1';

const SCORE_COLORS: Record<string, string> = {
  Core: '#00e5cc',
  Established: '#4f9cf9',
  Developing: '#ffb347',
  Weak: '#ff6b6b',
};

// ── Subcomponents ──────────────────────────────────────────────────────────────

function MemoryHealthPanel({ health }: { health: any }) {
  if (!health) return <PanelSkeleton />;
  const dist = health.score_distribution || {};
  const pieData = Object.entries(dist).map(([name, value]) => ({ name, value }));

  return (
    <div className="dashboard-panel">
      <div className="panel-header">
        <Brain size={18} className="text-teal" />
        <span>Memory Health</span>
        <span className={`health-badge health-${health.health_label?.toLowerCase()}`}>
          {health.health_label}
        </span>
      </div>
      <div className="panel-body flex gap-6 items-center">
        <ResponsiveContainer width={120} height={120}>
          <PieChart>
            <Pie data={pieData} cx="50%" cy="50%" innerRadius={35} outerRadius={55} dataKey="value">
              {pieData.map((entry) => (
                <Cell key={entry.name} fill={SCORE_COLORS[entry.name] || '#444'} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="flex flex-col gap-1.5">
          <div className="stat-row"><span className="stat-label">Active</span><span className="stat-val teal">{(health.active ?? 0).toLocaleString()}</span></div>
          <div className="stat-row"><span className="stat-label">Archived</span><span className="stat-val muted">{(health.archived ?? 0).toLocaleString()}</span></div>
          <div className="stat-row"><span className="stat-label">Avg Score</span><span className="stat-val">{health.avg_consolidation_score?.toFixed(3)}</span></div>
          {Object.entries(dist).map(([label, count]) => (
            <div key={label} className="stat-row">
              <span className="flex items-center gap-1.5">
                <span style={{ background: SCORE_COLORS[label] }} className="w-2 h-2 rounded-full inline-block" />
                <span className="stat-label">{label}</span>
              </span>
              <span className="stat-val text-xs">{String(count)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SleepStatusPanel({ sleepStatus, onTrigger }: { sleepStatus: any; onTrigger: () => void }) {
  if (!sleepStatus) return <PanelSkeleton />;
  const last = sleepStatus.last_run;
  return (
    <div className="dashboard-panel">
      <div className="panel-header">
        <Moon size={18} className="text-teal" />
        <span>Sleep Engine</span>
        <button className="trigger-btn" onClick={onTrigger} title="Run sleep consolidation now">
          <Play size={12} /> Run now
        </button>
      </div>
      <div className="panel-body">
        {last ? (
          <>
            <div className="sleep-summary">{last.summary}</div>
            <div className="text-xs text-muted mt-1">Last run: {new Date(last.ran_at).toLocaleString()}</div>
          </>
        ) : (
          <div className="text-muted text-sm">No runs yet — first nightly run at 3am UTC.</div>
        )}
        <div className="next-run-pill">
          <Clock size={12} />
          Next run in {sleepStatus.hours_until_next_run}h
        </div>
      </div>
    </div>
  );
}

function UsagePanel({ usage }: { usage: any }) {
  if (!usage) return <PanelSkeleton />;
  const pct = usage.quota_pct ?? 0;
  const color = pct >= 95 ? '#ff6b6b' : pct >= 80 ? '#ffb347' : '#00e5cc';
  return (
    <div className="dashboard-panel">
      <div className="panel-header">
        <TrendingUp size={18} className="text-teal" />
        <span>Usage & Quota</span>
      </div>
      <div className="panel-body">
        <div className="quota-ring-container">
          <svg width="80" height="80" viewBox="0 0 80 80">
            <circle cx="40" cy="40" r="34" fill="none" stroke="#1e2030" strokeWidth="8"/>
            <circle
              cx="40" cy="40" r="34" fill="none"
              stroke={color} strokeWidth="8"
              strokeDasharray={`${213.6 * pct / 100} 213.6`}
              strokeLinecap="round"
              transform="rotate(-90 40 40)"
              style={{ transition: 'stroke-dasharray 1s ease' }}
            />
          </svg>
          <div className="quota-pct" style={{ color }}>{pct.toFixed(0)}%</div>
        </div>
        <div className="usage-stats">
          <div className="stat-row"><span className="stat-label">API calls (30d)</span><span className="stat-val">{(usage.api_calls_30d ?? 0).toLocaleString()}</span></div>
          <div className="stat-row"><span className="stat-label">Memories total</span><span className="stat-val">{(usage.memories_total ?? 0).toLocaleString()}</span></div>
          <div className="stat-row"><span className="stat-label">Quota</span><span className="stat-val">{(usage.quota_used ?? 0).toLocaleString()} / {(usage.quota_limit ?? 0).toLocaleString()}</span></div>
        </div>
        {usage.quota_warning && (
          <div className="quota-warning-badge">
            <AlertTriangle size={12} /> {pct >= 95 ? 'Quota critical' : 'Quota warning'}
          </div>
        )}
      </div>
    </div>
  );
}

function WhatWouldRemember() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const token = localStorage.getItem('nsn-token');
      const r = await fetch(`${API}/memories/retrieve?query=${encodeURIComponent(query)}&project_id=default&top_k=5&dry_run=true`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await r.json();
      setResults(data.memories ?? []);
    } catch {
      toast.error('Search failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard-panel col-span-2">
      <div className="panel-header">
        <Search size={18} className="text-teal" />
        <span>What would my agent remember?</span>
        <span className="badge-dry-run">dry_run · no score effect</span>
      </div>
      <div className="panel-body">
        <div className="search-row">
          <input
            id="dry-run-search"
            className="memory-search-input"
            placeholder="Type any query to preview which memories would be injected..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button className="search-btn" onClick={handleSearch} disabled={loading}>
            {loading ? <RefreshCw size={14} className="animate-spin" /> : <Search size={14} />}
          </button>
        </div>
        <AnimatePresence>
          {results.length > 0 && (
            <motion.div
              className="retrieval-results"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              {results.map((mem: any, i: number) => (
                <motion.div
                  key={mem.id || i}
                  className="retrieval-card"
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <div className="rc-score" style={{ color: SCORE_COLORS[mem.consolidation_label?.label ?? 'Weak'] ?? '#00e5cc' }}>
                    {(mem.attention_score ?? mem.consolidation_score ?? 0).toFixed(3)}
                  </div>
                  <div className="rc-content">{mem.content}</div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function TimelineChart({ timeline }: { timeline: any[] }) {
  if (!timeline || !timeline.length) return null;
  return (
    <div className="dashboard-panel col-span-2">
      <div className="panel-header"><Database size={18} className="text-teal" /><span>30-Day Access Timeline</span></div>
      <div className="panel-body h-36">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={timeline}>
            <defs>
              <linearGradient id="tealGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00e5cc" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#00e5cc" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <XAxis dataKey="date" tick={{ fill: '#888', fontSize: 10 }} />
            <YAxis tick={{ fill: '#888', fontSize: 10 }} />
            <Tooltip contentStyle={{ background: '#1e2030', border: '1px solid #00e5cc44', borderRadius: 8 }} />
            <Area type="monotone" dataKey="accesses" stroke="#00e5cc" fill="url(#tealGrad)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function PanelSkeleton() {
  return (
    <div className="dashboard-panel animate-pulse">
      <div className="h-4 bg-white/5 rounded w-1/3 mb-3" />
      <div className="h-16 bg-white/5 rounded" />
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────

export default function Dashboard() {
  const token = localStorage.getItem('nsn-token');
  const headers = { Authorization: `Bearer ${token}` };

  const { data: health } = useQuery({
    queryKey: ['analytics-health'],
    queryFn: () => fetch(`${API}/analytics/health`, { headers }).then(r => r.json()),
    refetchInterval: 30_000,
  });

  const { data: usage } = useQuery({
    queryKey: ['analytics-usage'],
    queryFn: () => fetch(`${API}/analytics/usage`, { headers }).then(r => r.json()),
    refetchInterval: 60_000,
  });

  const { data: sleepStatus } = useQuery({
    queryKey: ['sleep-status'],
    queryFn: () => fetch(`${API}/sleep/status`, { headers }).then(r => r.json()),
    refetchInterval: 60_000,
  });

  const { data: timeline } = useQuery({
    queryKey: ['analytics-timeline'],
    queryFn: () => fetch(`${API}/analytics/timeline`, { headers }).then(r => r.json()),
  });

  const triggerSleep = async () => {
    try {
      await fetch(`${API}/sleep/trigger`, { method: 'POST', headers });
      toast.success('Sleep consolidation queued ✓');
    } catch {
      toast.error('Failed to trigger sleep run');
    }
  };

  return (
    <div className="dashboard-root">
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">Dashboard</h1>
          <p className="dashboard-subtitle">Real-time memory intelligence</p>
        </div>
        <div className="dashboard-live-badge"><span className="live-dot"/><span>Live</span></div>
      </div>

      <div className="dashboard-grid">
        <MemoryHealthPanel health={health} />
        <SleepStatusPanel sleepStatus={sleepStatus} onTrigger={triggerSleep} />
        <UsagePanel usage={usage} />
        <WhatWouldRemember />
        <TimelineChart timeline={timeline ?? []} />
      </div>
    </div>
  );
}
