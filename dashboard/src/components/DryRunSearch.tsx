import React, { useState } from 'react';

export default function DryRunSearch({ projectId, apiKey }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/memories/retrieve?query=${encodeURIComponent(query)}&project_id=${projectId}&dry_run=true`, {
        headers: { Authorization: `Bearer ${apiKey}` }
      });
      const data = await res.json();
      setResults(data.memories || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  return (
    <div className="p-4 border rounded-xl shadow-sm bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
      <h3 className="text-lg font-bold mb-2">What would my agent remember?</h3>
      <p className="text-sm text-zinc-500 mb-4">Run a simulated query. Dry-runs do not affect consolidation scores or increment access counts.</p>
      
      <div className="flex gap-2 mb-4">
        <input 
          className="flex-1 p-2 border rounded-md dark:bg-zinc-950 dark:border-zinc-700" 
          value={query} 
          onChange={e => setQuery(e.target.value)} 
          placeholder="e.g. What is the user's favorite color?" 
        />
        <button onClick={handleSearch} disabled={loading} className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition">
          {loading ? 'Searching...' : 'Simulate'}
        </button>
      </div>

      <div className="space-y-3">
        {results.map((mem, i) => (
          <div key={i} className="p-3 border rounded-md bg-zinc-50 dark:bg-zinc-800 dark:border-zinc-700 relative">
            <span className="absolute top-3 right-3 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
              Score: {mem.attention_score.toFixed(2)} ({mem.consolidation_label})
            </span>
            <p className="text-sm border-l-2 border-blue-400 pl-2 mt-2">{mem.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
