import React, { useEffect, useState } from 'react';

export default function AtRiskMemories({ projectId, apiKey }) {
  const [atRisk, setAtRisk] = useState([]);

  useEffect(() => {
    // In a real app we'd query /memories with sort=consolidation_score&status=active
    const fetchAtRisk = async () => {
      try {
        // Assume API allows querying by consolidation score ascending
        const res = await fetch(`/api/v1/memories/retrieve?query=any&project_id=${projectId}&dry_run=true`, {
          headers: { Authorization: `Bearer ${apiKey}` }
        });
        const data = await res.json();
        // Mock filtering client side for now just for visual proxy
        const weak = (data.memories || []).filter(m => m.consolidation_label === 'Weak');
        setAtRisk(weak.slice(0, 5));
      } catch (e) {
        console.error(e);
      }
    };
    fetchAtRisk();
  }, [projectId, apiKey]);

  const boostMemory = async (id) => {
    // API logic to forcefully set consolidation_score to 1.0 or bump it
  }

  if (atRisk.length === 0) return null;

  return (
    <div className="p-4 border border-rose-200 bg-rose-50 dark:bg-rose-950/20 dark:border-rose-900 rounded-xl">
      <h3 className="text-sm font-bold text-rose-800 dark:text-rose-300 flex items-center gap-2">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
        At Risk of Archiving
      </h3>
      <p className="text-xs text-rose-600 dark:text-rose-400 mt-1 mb-3">These memories will be pruned in the next overnight Sleep Cycle.</p>
      
      <div className="space-y-2">
        {atRisk.map((mem) => (
          <div key={mem.id} className="flex justify-between items-center text-sm bg-white dark:bg-rose-950/50 p-2 rounded">
            <span className="truncate w-3/4">{mem.content}</span>
            <button onClick={() => boostMemory(mem.id)} className="text-xs font-semibold px-2 py-1 bg-white dark:bg-zinc-800 border dark:border-zinc-700 rounded shadow-sm hover:bg-zinc-100">
              Keep This
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
