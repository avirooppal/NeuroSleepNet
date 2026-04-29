import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, 
  Moon, 
  Play, 
  Clock, 
  ArrowUpRight, 
  Brain,
  Shield,
  Layers,
  Search
} from 'lucide-react';
import toast from 'react-hot-toast';
import { Button } from '@/components/ui/button';
import { 
  MissInspector,
  PinManager, 
  SleepCycleLog, 
  AnomalyAlerts,
  LiveSessionFeed,
  AttentionHeatmap,
  PulseShortcut
} from '@/components/DashboardPanels';

// Local mode dashboard API is served from the same port as the frontend
const API_BASE = window.location.origin;

// ── Subcomponents ──────────────────────────────────────────────────────────────

function StatBlock({ label, value, subValue, icon: Icon, trend }: { 
  label: string; 
  value: string | number; 
  subValue?: string;
  icon?: any;
  trend?: string;
}) {
  return (
    <div className="bg-zinc-950 border border-zinc-900 p-5 rounded-xl hover:border-zinc-800 transition-colors group">
      <div className="flex justify-between items-start mb-3">
        <div className="text-[10px] uppercase tracking-[0.2em] font-bold text-zinc-500">{label}</div>
        {Icon && <Icon size={14} className="text-zinc-700 group-hover:text-zinc-400 transition-colors" />}
      </div>
      <div className="flex items-baseline gap-2">
        <div className="text-3xl font-black tracking-tighter text-zinc-100">{value}</div>
        {trend && <div className="text-[10px] font-bold text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded">{trend}</div>}
      </div>
      {subValue && <div className="text-[10px] text-zinc-600 font-mono mt-1">{subValue}</div>}
    </div>
  );
}

function HealthCircle({ score }: { score: number }) {
  const percent = Math.min(100, Math.max(0, score * 100));
  const color = score > 0.7 ? '#10b981' : score > 0.4 ? '#f59e0b' : '#ef4444';
  
  return (
    <div className="flex flex-col items-center justify-center dashboard-panel py-8">
      <div className="relative h-28 w-28">
        <svg className="h-full w-full" viewBox="0 0 36 36">
          <path
            className="stroke-zinc-900 fill-none"
            strokeWidth="3"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          />
          <path
            className="fill-none stroke-emerald-500 transition-all duration-1000 ease-out"
            strokeWidth="3"
            strokeDasharray={`${percent}, 100`}
            strokeLinecap="round"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            style={{ stroke: color }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-black text-white">{percent}%</span>
          <span className="text-[8px] font-bold text-zinc-600 uppercase tracking-tighter">Health</span>
        </div>
      </div>
      <div className="mt-4 text-center">
        <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">Status</div>
        <div className="text-xs font-bold text-white px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800">
          {score > 0.7 ? 'OPTIMIZED' : score > 0.4 ? 'STABLE' : 'FRAGMENTED'}
        </div>
      </div>
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { projectId } = useParams();
  const [events, setEvents] = useState<any[]>([]);

  // ── SSE Live Feed ────────────────────────────────────────────────────────────
  useEffect(() => {
    const sse = new EventSource(`${API_BASE}/api/events?project=${projectId || ''}`);
    
    sse.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        setEvents(prev => [event, ...prev].slice(0, 100));
      } catch (err) {
        console.error("SSE Parse Error:", err);
      }
    };

    return () => sse.close();
  }, [projectId]);

  // ── Data Fetching ────────────────────────────────────────────────────────────
  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['dashboard-stats', projectId],
    queryFn: () => fetch(`${API_BASE}/api/stats?project=${projectId || ''}`).then(r => r.json()),
    refetchInterval: 10000,
  });

  const { data: misses } = useQuery({
    queryKey: ['dashboard-misses', projectId],
    queryFn: () => fetch(`${API_BASE}/api/misses?project=${projectId || ''}`).then(r => r.json()),
    refetchInterval: 5000,
  });

  const { data: pins, refetch: refetchPins } = useQuery({
    queryKey: ['dashboard-pins', projectId],
    queryFn: () => fetch(`${API_BASE}/api/pins?project=${projectId || ''}`).then(r => r.json()),
    refetchInterval: 10000,
  });

  const { data: sleepLog } = useQuery({
    queryKey: ['dashboard-sleep', projectId],
    queryFn: () => fetch(`${API_BASE}/api/sleep?project=${projectId || ''}`).then(r => r.json()),
    refetchInterval: 30000,
  });

  const { data: attentionData } = useQuery({
    queryKey: ['attention', projectId],
    queryFn: () => fetch(`${API_BASE}/api/analytics/attention?project_id=${projectId || ''}`).then(r => r.json()),
    refetchInterval: 10000,
  });

  const triggerSleep = async () => {
    const promise = fetch(`${API_BASE}/api/sleep`, { method: 'POST' });
    toast.promise(promise, {
      loading: 'Waking sleep engine...',
      success: 'Sleep cycle triggered ✓',
      error: 'Failed to trigger sleep',
    });
    await promise;
    refetchStats();
  };

  const handleUnpin = async (id: string) => {
    if (!window.confirm("Are you sure you want to unpin this memory? Pins are hard rules.")) return;
    
    const res = await fetch(`${API_BASE}/api/pins?id=${id}`, { method: 'DELETE' });
    if (res.ok) {
      toast.success('Memory unpinned');
      refetchPins();
    }
  };

  return (
    <div className="dashboard-root max-w-[1600px] mx-auto p-6 bg-black min-h-screen text-zinc-100 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="bg-emerald-500/10 p-2 rounded-lg">
              <Brain size={24} className="text-emerald-500" />
            </div>
            <h1 className="text-3xl font-black tracking-tightest">NeuroSleepNet</h1>
          </div>
          <p className="text-zinc-500 text-sm font-medium">
            Intelligence consolidation for <span className="text-zinc-300 font-bold">{projectId}</span>
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end mr-4">
            <div className="flex items-center gap-2 mb-1">
              <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Live Engine</span>
            </div>
            <div className="text-[10px] font-mono text-zinc-600">Local Mode v0.3.0</div>
          </div>
          
          <Button 
            onClick={triggerSleep}
            className="bg-zinc-100 text-black hover:bg-zinc-300 font-bold text-xs px-6 py-5 rounded-xl flex items-center gap-2"
          >
            <Moon size={16} /> 
            Trigger Sleep
          </Button>
        </div>
      </div>

      <AnomalyAlerts stats={stats} />

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <StatBlock 
          label="Memories" 
          value={(stats?.total_memories ?? 0).toLocaleString()} 
          subValue={`${stats?.archived ?? 0} archived`} 
          icon={Layers}
        />
        <StatBlock 
          label="Attention Score" 
          value={stats?.avg_consolidation_score?.toFixed(3) ?? "0.000"} 
          subValue="Project accuracy"
          icon={Activity}
          trend={stats?.avg_consolidation_score > 0.5 ? "+12%" : undefined}
        />
        <StatBlock 
          label="Recall Misses" 
          value={(stats?.miss_count ?? 0).toLocaleString()} 
          subValue="Withheld (low confidence)"
          icon={Shield}
        />
        <StatBlock 
          label="Sleep Cycles" 
          value={stats?.sleep_cycles_run ?? 0} 
          subValue={stats?.last_sleep ? `Last: ${new Date(stats.last_sleep.finished_at).toLocaleTimeString()}` : 'Never run'}
          icon={Moon}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* Left Column: Health + Pins + Sleep Log */}
        <div className="xl:col-span-4 space-y-6">
          <HealthCircle score={stats?.health_score ?? 0} />
          <AttentionHeatmap data={attentionData} />
          <PulseShortcut projectId={projectId || 'default'} />
          <PinManager pins={pins} onUnpin={handleUnpin} />
          <SleepCycleLog sleepLog={sleepLog} />
        </div>

        {/* Right Column: Feed + Miss Inspector */}
        <div className="xl:col-span-8 space-y-6">
          <LiveSessionFeed events={events} />
          <MissInspector misses={misses} />
        </div>
      </div>

      {/* Footer Navigation */}
      <div className="mt-12 pt-8 border-t border-zinc-900 grid grid-cols-2 md:grid-cols-4 gap-4 pb-12">
        <FooterLink title="Memory Explorer" icon={Search} description="Search and edit every memory." />
        <FooterLink title="Model Templates" icon={Brain} description="Phi-3, Mistral, Llama-3 optimization." />
        <FooterLink title="Project Metrics" icon={Activity} description="Recall vs Miss rate analytics." />
        <FooterLink title="Security Vault" icon={Shield} description="Encryption and isolation policy." />
      </div>
    </div>
  );
}

function FooterLink({ title, icon: Icon, description }: { title: string, icon: any, description: string }) {
  return (
    <div className="group cursor-pointer">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} className="text-zinc-500 group-hover:text-emerald-500 transition-colors" />
        <span className="text-xs font-bold text-zinc-400 group-hover:text-white transition-colors">{title}</span>
      </div>
      <p className="text-[10px] text-zinc-600 leading-snug">{description}</p>
    </div>
  );
}

