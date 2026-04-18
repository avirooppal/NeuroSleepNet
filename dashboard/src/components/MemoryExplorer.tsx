import React, { useState } from 'react';

// Advanced filters mock layout
export default function MemoryExplorer({ memories }) {
  const [filterTier, setFilterTier] = useState('All'); // All, Core, Established, Developing, Weak
  const [neverRetrieved, setNeverRetrieved] = useState(false);
  const [sortByRisk, setSortByRisk] = useState(false);

  // Apply filters
  let filtered = [...(memories || [])];
  
  if (filterTier !== 'All') {
    filtered = filtered.filter(m => m.consolidation_label === filterTier);
  }
  
  if (neverRetrieved) {
    filtered = filtered.filter(m => m.access_count === 0);
  }

  if (sortByRisk) {
    filtered.sort((a, b) => a.consolidation_score - b.consolidation_score); // ascending score means higher risk
  } else {
    filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }

  return (
    <div className="p-6 border rounded-xl shadow-sm bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold">Memory Explorer</h2>
        
        <div className="flex gap-4 items-center text-sm">
          <select 
            value={filterTier} 
            onChange={e => setFilterTier(e.target.value)}
            className="p-1 border rounded dark:bg-zinc-800 dark:border-zinc-700"
          >
            <option>All Tiers</option>
            <option>Core</option>
            <option>Established</option>
            <option>Developing</option>
            <option>Weak</option>
          </select>

          <label className="flex items-center gap-2">
            <input 
              type="checkbox" 
              checked={neverRetrieved} 
              onChange={e => setNeverRetrieved(e.target.checked)} 
            />
            Never Retrieved
          </label>

          <button 
            onClick={() => setSortByRisk(!sortByRisk)}
            className={`px-3 py-1 rounded border ${sortByRisk ? 'bg-rose-100 border-rose-200 text-rose-800 dark:bg-rose-900/30' : 'bg-transparent dark:border-zinc-700'}`}
          >
            Sort by Risk
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-zinc-50 dark:bg-zinc-800/50 text-zinc-500 uppercase font-semibold">
            <tr>
              <th className="p-3 w-1/2">Content</th>
              <th className="p-3">Retrievals</th>
              <th className="p-3">Tier</th>
              <th className="p-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
            {filtered.map(m => (
              <tr key={m.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/20">
                <td className="p-3 truncate max-w-sm">{m.content}</td>
                <td className="p-3">{m.access_count}</td>
                <td className="p-3">
                  <span className={`px-2 py-1 rounded text-xs font-bold ${
                    m.consolidation_label === 'Core' ? 'bg-purple-100 text-purple-700' :
                    m.consolidation_label === 'Weak' ? 'bg-rose-100 text-rose-700' :
                    'bg-slate-100 text-slate-700'
                  }`}>
                    {m.consolidation_label}
                  </span>
                </td>
                <td className="p-3">
                  {m.consolidation_label === 'Weak' && m.access_count === 0 && (
                    <span className="text-rose-500 flex items-center gap-1">
                      <div className="w-2 h-2 rounded-full bg-rose-500"></div> At Risk
                    </span>
                  )}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={4} className="p-6 text-center text-zinc-500">No memories found matching filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
