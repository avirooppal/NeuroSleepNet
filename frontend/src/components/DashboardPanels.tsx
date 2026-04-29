import React from 'react';
import { 
  AlertTriangle, 
  Moon, 
  Pin, 
  Search, 
  Trash2, 
  Zap, 
  Activity, 
  Clock, 
  User,
  ShieldCheck,
  Brain
} from 'lucide-react';
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  ScrollArea 
} from "@/components/ui/scroll-area";
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as RechartsTooltip, 
  Cell 
} from 'recharts';
import { Link } from 'react-router-dom';

// ── Miss Inspector ─────────────────────────────────────────────────────────────

export function MissInspector({ misses }: { misses: any[] }) {
  return (
    <Card className="bg-zinc-950 border-zinc-900">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
            <Search size={16} className="text-zinc-400" />
            Miss Inspector
          </CardTitle>
          <Badge variant="outline" className="text-[10px] border-zinc-800 text-zinc-500">
            {misses?.length || 0} Withheld
          </Badge>
        </div>
        <CardDescription className="text-[11px] text-zinc-500">
          Memories below recall threshold are withheld to prevent hallucinations.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px] pr-4">
          {misses && misses.length > 0 ? (
            <Table>
              <TableHeader className="hover:bg-transparent border-zinc-900">
                <TableRow className="hover:bg-transparent border-zinc-900">
                  <TableHead className="text-[10px] uppercase font-bold text-zinc-600">Query / Context</TableHead>
                  <TableHead className="text-[10px] uppercase font-bold text-zinc-600 w-24 text-right">Score</TableHead>
                  <TableHead className="text-[10px] uppercase font-bold text-zinc-600 w-32 text-right">Reason</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {misses.map((miss, i) => (
                  <TableRow key={i} className="border-zinc-900 hover:bg-zinc-900/50">
                    <TableCell className="py-3">
                      <div className="text-xs text-zinc-300 font-medium mb-1 line-clamp-1">{miss.query}</div>
                      <div className="text-[10px] text-zinc-600 italic line-clamp-1">
                        Matched: {miss.memory_content}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="text-xs font-mono text-zinc-400">
                        {miss.score?.toFixed(3)}
                      </div>
                      <div className="text-[9px] text-zinc-700">vs {miss.threshold?.toFixed(2)}</div>
                    </TableCell>
                    <TableCell className="text-right">
                      <Badge className="bg-zinc-900 text-zinc-500 hover:bg-zinc-900 border-none text-[9px] px-1.5 h-4 uppercase font-bold">
                        {miss.reason || 'LOW_CONFIDENCE'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-zinc-700">
              <ShieldCheck className="opacity-10 mb-2" size={32} />
              <div className="text-xs font-medium">No misses detected</div>
              <div className="text-[10px]">Retrieval is perfectly aligned.</div>
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// ── Pin Manager ────────────────────────────────────────────────────────────────

export function PinManager({ pins, onUnpin }: { pins: any[], onUnpin: (id: string) => void }) {
  return (
    <Card className="bg-zinc-950 border-zinc-900">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
          <Pin size={16} className="text-zinc-400" />
          Pin Manager
        </CardTitle>
        <CardDescription className="text-[11px] text-zinc-500">
          Hard rules and permanent context that bypass sleep decay.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[250px] pr-4">
          <div className="space-y-3">
            {pins && pins.length > 0 ? (
              pins.map((pin, i) => (
                <div key={i} className="bg-zinc-900/40 border border-zinc-900 p-3 rounded-lg group">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1.5">
                        <Badge className="bg-zinc-800 text-white border-zinc-700 text-[10px] h-4">
                          {pin.label || 'pinned-rule'}
                        </Badge>
                        {pin.user_id && (
                          <span className="text-[10px] text-zinc-600 flex items-center gap-1">
                            <User size={10} /> {pin.user_id}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-zinc-300 leading-relaxed">{pin.content}</p>
                    </div>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-7 w-7 text-zinc-700 hover:text-red-400 hover:bg-red-400/10 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => onUnpin(pin.id)}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-zinc-700">
                <Pin className="opacity-10 mb-2" size={32} />
                <div className="text-xs font-medium">No active pins</div>
                <div className="text-[10px]">Use nsn.pin() to lock context.</div>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// ── Sleep Cycle Log ─────────────────────────────────────────────────────────────

export function SleepCycleLog({ sleepLog }: { sleepLog: any[] }) {
  return (
    <Card className="bg-zinc-950 border-zinc-900">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
          <Moon size={16} className="text-zinc-400" />
          Sleep Cycle Log
        </CardTitle>
        <CardDescription className="text-[11px] text-zinc-500">
          History of memory consolidation and promotion events.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[250px] pr-4">
          <Table>
            <TableHeader className="hover:bg-transparent border-zinc-900">
              <TableRow className="hover:bg-transparent border-zinc-900">
                <TableHead className="text-[10px] uppercase font-bold text-zinc-600">Finished At</TableHead>
                <TableHead className="text-[10px] uppercase font-bold text-zinc-600 text-center">Consolidated</TableHead>
                <TableHead className="text-[10px] uppercase font-bold text-zinc-600 text-right">Promoted</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sleepLog && sleepLog.length > 0 ? (
                sleepLog.map((log, i) => (
                  <TableRow key={i} className="border-zinc-900 hover:bg-zinc-900/50">
                    <TableCell className="py-3 font-mono text-[10px] text-zinc-500">
                      {new Date(log.finished_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger>
                              <div className="flex items-center gap-1">
                                <span className="text-[11px] font-bold text-zinc-300">{log.boosted + log.deduped + log.archived}</span>
                                <Activity size={10} className="text-blue-500" />
                              </div>
                            </TooltipTrigger>
                            <TooltipContent className="bg-zinc-900 border-zinc-800 text-[10px]">
                              Boosted: {log.boosted} | Deduped: {log.deduped} | Archived: {log.archived}
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <span className="text-[11px] font-bold text-emerald-500">+{log.promoted}</span>
                        <Zap size={10} className="text-emerald-500 fill-emerald-500" />
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow className="border-none">
                  <TableCell colSpan={3} className="text-center py-12 text-zinc-700 text-xs">
                    No sleep cycles recorded.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// ── Anomaly Alerts ─────────────────────────────────────────────────────────────

export function AnomalyAlerts({ stats }: { stats: any }) {
  const alerts = [];
  if (stats?.anomaly_miss_spike) {
    alerts.push({
      type: 'warning',
      title: 'Recall Miss Spike',
      message: `Detected ${stats.recent_misses_1h} misses in the last hour — 50% higher than baseline.`,
    });
  }
  
  if (stats?.avg_consolidation_score < 0.3 && stats?.total_memories > 50) {
    alerts.push({
      type: 'critical',
      title: 'Fragmented Memory',
      message: 'Low average consolidation score. Consider manual nsn.sleep() if interval is high.',
    });
  }

  if (alerts.length === 0) return null;

  return (
    <div className="space-y-2 mb-4">
      {alerts.map((alert, i) => (
        <div 
          key={i} 
          className={`flex items-start gap-3 p-3 rounded-lg border ${
            alert.type === 'critical' 
              ? 'bg-red-500/10 border-red-500/20 text-red-400' 
              : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
          }`}
        >
          <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" />
          <div>
            <div className="text-xs font-bold uppercase tracking-wider">{alert.title}</div>
            <div className="text-[10px] opacity-80">{alert.message}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Live Session Feed ───────────────────────────────────────────────────────────

export function LiveSessionFeed({ events }: { events: any[] }) {
  return (
    <Card className="bg-zinc-950 border-zinc-900 col-span-full">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
            <Activity size={16} className="text-zinc-400" />
            Live Session Feed
          </CardTitle>
          <CardDescription className="text-[11px] text-zinc-500">
            Real-time stream of intercepted memory events.
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
           <span className="text-[9px] font-bold text-zinc-600 uppercase">Live</span>
           <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)] animate-pulse" />
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[200px] pr-4">
          <div className="space-y-1">
            {events && events.length > 0 ? (
              events.map((event, i) => (
                <div key={i} className="flex items-start gap-3 py-2 border-b border-zinc-900/50 last:border-0 hover:bg-zinc-900/20 transition-colors px-2 rounded">
                  <div className="text-[9px] font-mono text-zinc-600 mt-1 flex-shrink-0">
                    {new Date(event.ts * 1000).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </div>
                  <div className="flex-shrink-0">
                    {event.type === 'remember' && <Badge className="bg-blue-500/10 text-blue-400 border-0 text-[9px] h-4">REMEMBER</Badge>}
                    {event.type === 'recall' && <Badge className="bg-emerald-500/10 text-emerald-400 border-0 text-[9px] h-4">RECALL</Badge>}
                    {event.type === 'pin' && <Badge className="bg-amber-500/10 text-amber-400 border-0 text-[9px] h-4">PIN</Badge>}
                  </div>
                  <div className="flex-1 text-[11px] text-zinc-400 truncate">
                    {event.type === 'recall' ? (
                      <span>
                        Query: <span className="text-zinc-200">"{event.data.query}"</span> 
                        <span className="ml-2 text-zinc-600">({event.data.hits} hits, {event.data.misses} misses)</span>
                      </span>
                    ) : (
                      <span>
                        {event.data.content}
                        {event.data.label && <span className="ml-2 text-zinc-600">[{event.data.label}]</span>}
                      </span>
                    )}
                  </div>
                  {event.data.user_id && (
                    <div className="text-[9px] text-zinc-700 flex items-center gap-1 flex-shrink-0">
                      <User size={10} /> {event.data.user_id}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-zinc-700">
                <Brain className="opacity-10 mb-2" size={32} />
                <div className="text-xs font-medium">Waiting for events...</div>
                <div className="text-[10px]">Interactions will appear here in real-time.</div>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// ── Attention Heatmap ─────────────────────────────────────────────────────────

export function AttentionHeatmap({ data }: { data: any[] }) {
  const COLORS = ['#00e5cc', '#4f9cf9', '#a78bfa', '#fbbf24', '#f87171'];

  return (
    <Card className="bg-zinc-950 border-zinc-900">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
          <Activity size={16} className="text-zinc-400" />
          Attention Distribution
        </CardTitle>
        <CardDescription className="text-[11px] text-zinc-500">
          Which memory types are being recalled most in recent tasks.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[200px] w-full mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#18181b" horizontal={false} />
              <XAxis type="number" hide />
              <YAxis 
                dataKey="type" 
                type="category" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fill: '#71717a', fontSize: 10, fontWeight: 700 }}
                width={80}
              />
              <RechartsTooltip 
                cursor={{ fill: 'transparent' }}
                contentStyle={{ background: '#09090b', border: '1px solid #27272a', borderRadius: '8px', fontSize: '10px' }}
                itemStyle={{ color: '#00e5cc' }}
              />
              <Bar dataKey="recalls" radius={[0, 4, 4, 0]} barSize={12}>
                {data?.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Residual Pathway Map Link ──────────────────────────────────────────────────

export function PulseShortcut({ projectId }: { projectId: string }) {
  return (
    <Link to={`/dashboard/${projectId}/pulse`}>
      <Card className="bg-zinc-950 border-zinc-900 hover:border-emerald-500/50 transition-colors group cursor-pointer overflow-hidden relative">
        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-30 transition-opacity">
          <Activity size={80} className="text-emerald-500" />
        </div>
        <CardHeader>
          <CardTitle className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
            <Brain size={16} className="text-zinc-400" />
            Residual Pathway Map
          </CardTitle>
          <CardDescription className="text-[11px] text-zinc-500">
            Open the force-directed graph of memory connections.
          </CardDescription>
        </CardHeader>
        <CardContent>
           <div className="flex items-center gap-2 text-emerald-500 text-xs font-bold">
              Explore Neural Graph →
           </div>
        </CardContent>
      </Card>
    </Link>
  );
}
