import React, { useState, useCallback } from 'react';

const SAMPLE_DATA = Array.from({ length: 30 }, (_, i) => ({
  day: i + 1,
  stored: Math.floor(Math.random() * 40 + 10),
  retrieved: Math.floor(Math.random() * 30 + 5),
  archived: Math.floor(Math.random() * 5),
  sleepRan: i % 7 === 6,
}));

function Tooltip({ data, x, y }: { data: typeof SAMPLE_DATA[0], x: number, y: number }) {
  return (
    <div
      className="absolute z-10 pointer-events-none bg-zinc-900 border border-zinc-700 rounded-lg p-3 shadow-xl text-xs"
      style={{ left: x + 12, top: y - 60 }}
    >
      <div className="font-bold text-white mb-1">Day {data.day}</div>
      <div className="flex items-center gap-1 text-emerald-400">
        <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" /> Stored: {data.stored}
      </div>
      <div className="flex items-center gap-1 text-blue-400">
        <span className="w-2 h-2 rounded-full bg-blue-400 inline-block" /> Retrieved: {data.retrieved}
      </div>
      <div className="flex items-center gap-1 text-rose-400">
        <span className="w-2 h-2 rounded-full bg-rose-400 inline-block" /> Archived: {data.archived}
      </div>
      {data.sleepRan && (
        <div className="mt-1 pt-1 border-t border-zinc-700 text-purple-300">🌙 Sleep cycle ran</div>
      )}
    </div>
  );
}

export default function PulseGraph({ data = SAMPLE_DATA }: { data?: typeof SAMPLE_DATA }) {
  const [tooltip, setTooltip] = useState<{ d: typeof SAMPLE_DATA[0]; x: number; y: number } | null>(null);

  const W = 700;
  const H = 200;
  const PAD = { top: 16, right: 20, bottom: 32, left: 40 };
  const inner = { w: W - PAD.left - PAD.right, h: H - PAD.top - PAD.bottom };

  const maxVal = Math.max(...data.map(d => d.stored + d.retrieved));
  const xStep = inner.w / (data.length - 1);
  const yScale = (v: number) => inner.h - (v / maxVal) * inner.h;

  const buildPath = (getter: (d: typeof SAMPLE_DATA[0]) => number, cumulative = false) => {
    return data.map((d, i) => {
      const v = cumulative ? d.stored + d.retrieved : getter(d);
      const x = PAD.left + i * xStep;
      const y = PAD.top + yScale(v);
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
  };

  const areaPath = (getter: (d: typeof SAMPLE_DATA[0]) => number) => {
    const top = data.map((d, i) => {
      const x = PAD.left + i * xStep;
      const y = PAD.top + yScale(getter(d));
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    const lastX = (PAD.left + (data.length - 1) * xStep).toFixed(1);
    const baseY = (PAD.top + inner.h).toFixed(1);
    const firstX = PAD.left.toFixed(1);
    return `${top} L${lastX},${baseY} L${firstX},${baseY} Z`;
  };

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = e.clientX - rect.left - PAD.left;
    const idx = Math.max(0, Math.min(data.length - 1, Math.round(relX / xStep)));
    setTooltip({ d: data[idx], x: PAD.left + idx * xStep, y: PAD.top + yScale(data[idx].stored) });
  }, [data, xStep]);

  return (
    <div className="p-4 border rounded-xl bg-zinc-900 border-zinc-800 relative">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-white">Memory Pulse — Last 30 Days</h3>
        <div className="flex items-center gap-4 text-xs text-zinc-400">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />Stored</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-400 inline-block" />Retrieved</span>
          <span className="flex items-center gap-1"><span className="w-2 h-1.5 inline-block" style={{ background: 'linear-gradient(90deg, #7c3aed, transparent)' }} />Sleep</span>
        </div>
      </div>

      <div className="relative">
        <svg
          width="100%" viewBox={`0 0 ${W} ${H}`}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setTooltip(null)}
          className="cursor-crosshair overflow-visible"
        >
          <defs>
            <linearGradient id="stored-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#34d399" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#34d399" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="retrieved-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#60a5fa" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Sleep cycle markers */}
          {data.map((d, i) => d.sleepRan && (
            <rect
              key={i}
              x={PAD.left + i * xStep - 1}
              y={PAD.top}
              width={2}
              height={inner.h}
              fill="#7c3aed"
              opacity={0.35}
            />
          ))}

          {/* Y-axis gridlines */}
          {[0.25, 0.5, 0.75, 1].map(ratio => (
            <line
              key={ratio}
              x1={PAD.left} y1={PAD.top + inner.h * (1 - ratio)}
              x2={PAD.left + inner.w} y2={PAD.top + inner.h * (1 - ratio)}
              stroke="#27272a" strokeWidth="1"
            />
          ))}

          {/* Area fills */}
          <path d={areaPath(d => d.stored)} fill="url(#stored-grad)" />
          <path d={areaPath(d => d.retrieved)} fill="url(#retrieved-grad)" />

          {/* Lines */}
          <path d={buildPath(d => d.stored)} fill="none" stroke="#34d399" strokeWidth="2" strokeLinejoin="round" />
          <path d={buildPath(d => d.retrieved)} fill="none" stroke="#60a5fa" strokeWidth="2" strokeLinejoin="round" strokeDasharray="4 2" />

          {/* Hover dot */}
          {tooltip && (
            <circle
              cx={PAD.left + data.findIndex(d => d === tooltip.d) * xStep}
              cy={PAD.top + yScale(tooltip.d.stored)}
              r={4} fill="#34d399" stroke="#fff" strokeWidth="2"
            />
          )}
        </svg>

        {tooltip && <Tooltip data={tooltip.d} x={tooltip.x} y={tooltip.y} />}
      </div>
    </div>
  );
}
