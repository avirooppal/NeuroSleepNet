import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import ResidualPathwayMap from '../components/ResidualPathwayMap';

const API = window.location.origin;

export default function MemoryPulse() {
  const { projectId } = useParams();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const token = localStorage.getItem('nsn-token');

  const { data, isLoading } = useQuery({
    queryKey: ['pathway-map', projectId],
    queryFn: () => fetch(`${API}/api/analytics/pathway-map?project_id=${projectId || ''}&limit=200`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(r => r.json()),
    refetchInterval: 30000,
  });

  const selectedNode = data?.nodes.find((n: any) => n.id === selectedId);

  return (
    <div className="flex flex-col h-[calc(100vh-100px)] gap-4">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Residual Pathway Map</h1>
          <p className="text-sm text-slate-400">
            Semantic topology of project memories. Node size = reinforcement, Edges = semantic similarity.
          </p>
        </div>
      </div>

      <div className="flex-1 min-h-0 relative">
        {isLoading ? (
          <div className="w-full h-full flex items-center justify-center bg-slate-900/20 rounded-xl border border-slate-800">
            <div className="text-slate-500 animate-pulse">Initializing neural map...</div>
          </div>
        ) : (
          <ResidualPathwayMap 
            data={data || { nodes: [], links: [] }} 
            onNodeClick={(id) => setSelectedId(id)}
            width={1200} 
            height={800} 
          />
        )}
      </div>

      {selectedNode && (
        <div className="absolute right-8 top-32 w-80 bg-slate-900/90 border border-slate-800 p-6 rounded-xl shadow-2xl backdrop-blur-md">
          <button 
            className="absolute top-2 right-2 text-slate-500 hover:text-white"
            onClick={() => setSelectedId(null)}
          >
            ×
          </button>
          <div className="text-[10px] uppercase font-bold tracking-widest text-blue-500 mb-1">
            {selectedNode.type}
          </div>
          <div className="text-slate-100 text-sm mb-4 leading-relaxed">
            {selectedNode.content}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-[9px] text-slate-500 uppercase">Feedback</div>
              <div className="text-slate-200 font-mono">{(selectedNode.feedback * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div className="text-[9px] text-slate-500 uppercase">Importance</div>
              <div className="text-slate-200 font-mono">{selectedNode.importance.toFixed(2)}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

