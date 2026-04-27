import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';
import { Brain, Zap, Moon, AlertTriangle, Search, Play, Clock, TrendingUp, Database, RefreshCw, Activity } from 'lucide-react';
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

function LiveSDKLogs({ projectId }: { projectId?: string }) {
  const headers = { Authorization: `Bearer local_test_key` };
  const { data } = useQuery({
    queryKey: ['live-logs', projectId],
    queryFn: () => fetch(`${API}/memories/explain_last?project_id=${projectId || ''}`, { headers }).then(r => r.json()),
    refetchInterval: 2000,
  });

  return (
    <div className="dashboard-panel col-span-2 border border-teal-500/30 shadow-[0_0_15px_rgba(0,229,204,0.1)]">
      <div className="panel-header">
        <Activity size={18} className="text-teal-400" />
        <span className="text-teal-400">Live SDK Interceptor Logs</span>
        <span className="live-dot ml-auto" />
      </div>
      <div className="panel-body max-h-80 overflow-y-auto pr-2 space-y-4">
        {data?.query ? (
          <div className="text-sm">
            <div className="text-slate-500 text-xs mb-1 uppercase tracking-widest font-bold">Latest Intercepted Prompt</div>
            <div className="bg-black/50 p-4 rounded-xl border border-white/5 font-mono text-teal-300">
              "{data.query}"
            </div>
            <div className="text-slate-500 text-xs mt-4 mb-2 uppercase tracking-widest font-bold">Auto-Injected Context (Memories)</div>
            {data.memories?.length > 0 ? data.memories.map((m: any, i: number) => (
              <div key={i} className="flex gap-3 bg-white/5 p-3 rounded-xl border border-white/5 mt-2 text-slate-300 text-sm items-start hover:bg-white/10 transition-colors">
                <span className="text-[10px] font-bold text-teal-400 bg-teal-400/10 px-2 py-1 rounded font-mono mt-0.5">
                  {(data.attention_scores?.[i] ?? m.attention_score ?? 0).toFixed(2)}
                </span>
                <span className="flex-1">{m.content}</span>
              </div>
            )) : (
              <div className="text-slate-500 italic text-xs">No memories were injected for this prompt.</div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-10 text-slate-500 text-sm">
            <Activity className="h-8 w-8 mb-3 opacity-20" />
            <span>Waiting for SDK activity...</span>
            <span className="text-xs mt-1">Run your python script to see live interception!</span>
          </div>
        )}
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
  const { projectId } = useParams();
  const token = "local_test_key"; // Bypass auth locally
  const headers = { Authorization: `Bearer ${token}` };

  const { data: health } = useQuery({
    queryKey: ['analytics-health', projectId],
    queryFn: () => fetch(`${API}/analytics/health?project_id=${projectId || ''}`, { headers }).then(r => r.json()),
    refetchInterval: 30_000,
  });

  const { data: usage } = useQuery({
    queryKey: ['analytics-usage', projectId],
    queryFn: () => fetch(`${API}/analytics/usage?project_id=${projectId || ''}`, { headers }).then(r => r.json()),
    refetchInterval: 60_000,
  });

  const { data: sleepStatus } = useQuery({
    queryKey: ['sleep-status', projectId],
    queryFn: () => fetch(`${API}/sleep/status?project_id=${projectId || ''}`, { headers }).then(r => r.json()),
    refetchInterval: 60_000,
  });

  const { data: timeline } = useQuery({
    queryKey: ['analytics-timeline', projectId],
    queryFn: () => fetch(`${API}/analytics/timeline?project_id=${projectId || ''}`, { headers }).then(r => r.json()),
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
        <LiveSDKLogs projectId={projectId} />
        <MemoryHealthPanel health={health} />
        <SleepStatusPanel sleepStatus={sleepStatus} onTrigger={triggerSleep} />
        <UsagePanel usage={usage} />
      </div>
    </div>
  );
}
