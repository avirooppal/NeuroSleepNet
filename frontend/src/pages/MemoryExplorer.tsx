import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { FixedSizeList } from 'react-window';
import { motion } from 'framer-motion';
import { Search, Trash2, Star, Archive, Filter, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';

const API = window.location.origin;
const SCORE_COLORS: Record<string, string> = { Core: '#00e5cc', Established: '#4f9cf9', Developing: '#ffb347', Weak: '#ff6b6b' };

function getLabel(score: number) {
  if (score >= 0.75) return 'Core';
  if (score >= 0.5) return 'Established';
  if (score >= 0.25) return 'Developing';
  return 'Weak';
}

export default function MemoryExplorer() {
  const { projectId } = useParams();
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<'all' | 'at-risk' | 'never-retrieved' | 'core'>('all');
  const [sortBy, setSortBy] = useState<'score' | 'accessed' | 'created' | 'count'>('score');
  const token = localStorage.getItem('nsn-token');
  const headers = { Authorization: `Bearer ${token}` };
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['memories-explorer', projectId, query, filter, sortBy],
    queryFn: () =>
      fetch(`${API}/api/memories/retrieve?query=${encodeURIComponent(query || 'memory')}&project_id=${projectId || ''}&top_k=200`, { headers })
        .then(r => r.json()),
    keepPreviousData: true,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => fetch(`${API}/api/memories/${id}`, { method: 'DELETE', headers }),
    onSuccess: () => { toast.success('Memory deleted'); qc.invalidateQueries({ queryKey: ['memories-explorer'] }); },
  });

  const memories: any[] = (data?.memories ?? []).filter((m: any) => {
    if (filter === 'at-risk') return m.consolidation_score < 0.25 && m.access_count === 0;
    if (filter === 'never-retrieved') return m.access_count === 0;
    if (filter === 'core') return m.consolidation_score >= 0.75;
    return true;
  }).sort((a: any, b: any) => {
    if (sortBy === 'score') return b.consolidation_score - a.consolidation_score;
    if (sortBy === 'count') return (b.access_count ?? 0) - (a.access_count ?? 0);
    if (sortBy === 'accessed') return new Date(b.last_accessed_at).getTime() - new Date(a.last_accessed_at).getTime();
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const mem = memories[index];
    const label = getLabel(mem.consolidation_score);
    const isAtRisk = mem.consolidation_score < 0.25 && mem.access_count === 0;
    return (
      <div style={style} className="memory-row">
        <div className="memory-row-inner group">
          <span className="score-badge" style={{ color: SCORE_COLORS[label], borderColor: SCORE_COLORS[label] + '44' }}>
            {mem.consolidation_score.toFixed(3)}
          </span>
          <span className="mem-label-pill" style={{ background: SCORE_COLORS[label] + '22', color: SCORE_COLORS[label] }}>
            {label}
          </span>
          {isAtRisk && (
            <span className="at-risk-badge"><AlertTriangle size={10} /> At risk</span>
          )}
          <span className="mem-content">{mem.content.slice(0, 120)}{mem.content.length > 120 ? '…' : ''}</span>
          <div className="mem-actions">
            <button title="Delete" onClick={() => deleteMutation.mutate(mem.id)} className="mem-action-btn danger">
              <Trash2 size={13} />
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="explorer-root">
      <div className="explorer-header">
        <h1 className="dashboard-title">Memory Explorer</h1>
        <p className="dashboard-subtitle">Search, filter, and manage your memory store.</p>
      </div>

      <div className="explorer-controls">
        <div className="search-row">
          <Search size={15} className="search-icon" />
          <input
            id="memory-explorer-search"
            className="memory-search-input"
            placeholder="Semantic search — embedding-based, not text search..."
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
        </div>
        <div className="filter-row">
          {(['all', 'at-risk', 'never-retrieved', 'core'] as const).map(f => (
            <button key={f} className={`filter-btn ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
              {f === 'at-risk' ? <><AlertTriangle size={11} /> At Risk</> : f === 'core' ? <><Star size={11} /> Core</> : f}
            </button>
          ))}
          <select className="sort-select" value={sortBy} onChange={e => setSortBy(e.target.value as any)}>
            <option value="score">Sort: Score</option>
            <option value="count">Sort: Accesses</option>
            <option value="accessed">Sort: Last accessed</option>
            <option value="created">Sort: Created</option>
          </select>
        </div>
        <div className="result-count">{memories.length} memories</div>
      </div>

      {isLoading ? (
        <div className="explorer-loading">Loading memories...</div>
      ) : memories.length === 0 ? (
        <div className="explorer-empty">No memories match this filter.</div>
      ) : (
        <FixedSizeList height={Math.min(600, memories.length * 64)} itemCount={memories.length} itemSize={64} width="100%">
          {Row}
        </FixedSizeList>
      )}
    </div>
  );
}
