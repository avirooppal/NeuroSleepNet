import React, { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import * as d3 from 'd3-force';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/v1';
const SCORE_COLORS: Record<string, string> = { Core: '#00e5cc', Established: '#4f9cf9', Developing: '#ffb347', Weak: '#ff6b6b' };

function getLabel(score: number): string {
  if (score >= 0.75) return 'Core';
  if (score >= 0.50) return 'Established';
  if (score >= 0.25) return 'Developing';
  return 'Weak';
}

interface MemNode extends d3.SimulationNodeDatum {
  id: string; content: string; consolidation_score: number; access_count: number;
  label: string; color: string; r: number;
}

export default function MemoryPulse() {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selected, setSelected] = useState<MemNode | null>(null);
  const [dim, setDim] = useState({ w: 900, h: 580 });
  const token = localStorage.getItem('nsn-token');

  const { data } = useQuery({
    queryKey: ['memories-pulse'],
    queryFn: () => fetch(`${API}/memories/retrieve?query=&project_id=default&top_k=100`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(r => r.json()),
    refetchInterval: 30000,
  });

  useEffect(() => {
    const onResize = () => {
      if (svgRef.current?.parentElement) {
        const { clientWidth } = svgRef.current.parentElement;
        setDim({ w: clientWidth, h: Math.max(500, window.innerHeight - 240) });
      }
    };
    onResize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    const memories: any[] = data?.memories ?? [];
    if (!memories.length || !svgRef.current) return;
    const svg = d3.select(svgRef.current as any);
    svg.selectAll('*').remove();
    const { w, h } = dim;

    const nodes: MemNode[] = memories.map(m => ({
      id: m.id, content: m.content, consolidation_score: m.consolidation_score,
      access_count: m.access_count ?? 0, label: getLabel(m.consolidation_score),
      color: SCORE_COLORS[getLabel(m.consolidation_score)],
      r: 10 + m.consolidation_score * 22,
      x: w / 2 + (Math.random() - 0.5) * 200, y: h / 2 + (Math.random() - 0.5) * 200,
    }));

    const links: any[] = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const aTags: string[] = memories[i].tags ?? [];
        const bTags: string[] = memories[j].tags ?? [];
        if (aTags.some((t: string) => bTags.includes(t))) links.push({ source: nodes[i], target: nodes[j] });
      }
    }

    const sim = d3.forceSimulation(nodes as any)
      .force('charge', d3.forceManyBody().strength(-80))
      .force('center', d3.forceCenter(w / 2, h / 2))
      .force('collision', d3.forceCollide().radius((d: any) => d.r + 4));

    const defs = svg.append('defs');
    const f = defs.append('filter').attr('id', 'glow');
    f.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'coloredBlur');
    const fm = f.append('feMerge');
    fm.append('feMergeNode').attr('in', 'coloredBlur');
    fm.append('feMergeNode').attr('in', 'SourceGraphic');

    const linkEls = svg.append('g').selectAll('line').data(links).enter().append('line')
      .attr('stroke', '#00e5cc22').attr('stroke-width', 1);

    const nodeEls = svg.append('g').selectAll('g').data(nodes).enter().append('g')
      .style('cursor', 'pointer')
      .on('click', (_: any, d: MemNode) => setSelected(d))
      .on('mouseover', function(_: any, d: MemNode) {
        linkEls.attr('stroke', (l: any) =>
          l.source.id === d.id || l.target.id === d.id ? '#00e5cc88' : '#00e5cc11');
      })
      .on('mouseout', () => linkEls.attr('stroke', '#00e5cc22'));

    nodeEls.append('circle')
      .attr('r', (d: MemNode) => d.r)
      .attr('fill', (d: MemNode) => d.color + '33')
      .attr('stroke', (d: MemNode) => d.color)
      .attr('stroke-width', 2).attr('filter', 'url(#glow)');

    nodeEls.append('text').attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
      .attr('fill', '#fff').attr('font-size', 9).attr('pointer-events', 'none')
      .text((d: MemNode) => d.label[0]);

    sim.on('tick', () => {
      linkEls.attr('x1', (l: any) => l.source.x).attr('y1', (l: any) => l.source.y)
        .attr('x2', (l: any) => l.target.x).attr('y2', (l: any) => l.target.y);
      nodeEls.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });
    return () => { sim.stop(); };
  }, [data, dim]);

  return (
    <div className="pulse-root">
      <div className="pulse-header">
        <h1 className="dashboard-title">Memory Pulse</h1>
        <p className="dashboard-subtitle">Force-directed graph — node size = consolidation score, edges = co-retrieved memories.</p>
        <div className="pulse-legend">
          {Object.entries(SCORE_COLORS).map(([label, color]) => (
            <span key={label} className="legend-item">
              <span className="legend-dot" style={{ background: color }} />{label}
            </span>
          ))}
        </div>
      </div>
      <div className="pulse-canvas-wrapper">
        <svg ref={svgRef} width="100%" height={dim.h} style={{ borderRadius: 16, background: '#0a0a0f' }} />
      </div>
      {selected && (
        <motion.div className="pulse-detail-panel" initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }}>
          <button className="detail-close" onClick={() => setSelected(null)}>×</button>
          <div className="detail-label" style={{ color: SCORE_COLORS[selected.label] }}>{selected.label}</div>
          <div className="detail-score">{selected.consolidation_score.toFixed(4)}</div>
          <div className="detail-content">{selected.content}</div>
          <div className="detail-meta">Accesses: <strong>{selected.access_count}</strong></div>
        </motion.div>
      )}
    </div>
  );
}
