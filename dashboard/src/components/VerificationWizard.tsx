import React, { useState } from 'react';

export default function VerificationWizard({ apiKey, projectId }) {
  const [status, setStatus] = useState('idle'); // idle, testing, success, error
  const [logs, setLogs] = useState([]);

  const runTest = async () => {
    setStatus('testing');
    setLogs(['Initiating memory layer test...']);
    try {
      const headers = { 
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'Idempotency-Key': `test-${Date.now()}`
      };

      // 1. Store memory
      setLogs(l => [...l, 'Attempting to store test memory...']);
      const postRes = await fetch('/api/v1/memories', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          content: "The master control sequence is Alpha-7",
          project_id: projectId,
          importance: 0.99
        })
      });
      if (!postRes.ok) throw new Error('Write failed');
      setLogs(l => [...l, '✅ Memory successfully stored.']);

      // 2. Small delay for vector indexing if async
      await new Promise(r => setTimeout(r, 1000));

      // 3. Retrieve
      setLogs(l => [...l, 'Attempting to recall memory details...']);
      const getRes = await fetch(`/api/v1/memories/retrieve?query=master%20control&project_id=${projectId}`, { headers });
      const getData = await getRes.json();
      
      if (getData.memories && getData.memories.length > 0) {
        setLogs(l => [...l, `✅ Recall successful! Attention Score: ${getData.memories[0].attention_score.toFixed(2)}`]);
        setStatus('success');
      } else {
        throw new Error('Retrieved array was empty');
      }
    } catch (e) {
      setLogs(l => [...l, `❌ Error: ${e.message}`]);
      setStatus('error');
    }
  };

  return (
    <div className="p-6 border rounded-xl shadow bg-white dark:bg-zinc-900">
      <h2 className="text-xl font-bold mb-2">Step 3: Verify Integration</h2>
      <p className="mb-4 text-zinc-500">We need to verify that your API key has write credentials and the memory roundtrip operates correctly.</p>
      
      {status === 'idle' && (
        <button onClick={runTest} className="px-5 py-2 bg-black text-white dark:bg-white dark:text-black font-semibold rounded-md hover:opacity-80">
          Run Diagnostic Test
        </button>
      )}

      {status !== 'idle' && (
        <div className="bg-zinc-100 dark:bg-zinc-950 p-4 rounded-md font-mono text-sm">
          {logs.map((log, idx) => <div key={idx} className="mb-1">{log}</div>)}
          {status === 'testing' && <div className="mt-2 text-blue-500 animate-pulse">Running checks...</div>}
        </div>
      )}

      {status === 'success' && (
        <div className="mt-4 p-3 bg-green-100 text-green-800 rounded flex items-center gap-2 font-semibold border border-green-200">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
          System fully operational. Ready for scale.
        </div>
      )}
    </div>
  );
}
