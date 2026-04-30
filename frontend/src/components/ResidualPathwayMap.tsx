import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface Node extends d3.SimulationNodeDatum {
  id: string;
  content: string;
  type: string;
  feedback: number;
  importance: number;
  size: number;
}

interface Link extends d3.SimulationLinkDatum<Node> {
  source: string | Node;
  target: string | Node;
  value: number;
}

interface PathwayMapProps {
  data: {
    nodes: Node[];
    links: Link[];
  };
  onNodeClick?: (nodeId: string) => void;
  width?: number;
  height?: number;
}

const ResidualPathwayMap: React.FC<PathwayMapProps> = ({ data, onNodeClick, width = 800, height = 600 }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !data.nodes.length) return;

    // --- Cleanup previous render ---
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // --- Setup Simulation ---
    const simulation = d3.forceSimulation<Node>(data.nodes)
      .force("link", d3.forceLink<Node, Link>(data.links).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("x", d3.forceX(width / 2).strength(0.1))
      .force("y", d3.forceY(height / 2).strength(0.1));

    // --- Draw Links ---
    const link = svg.append("g")
      .attr("stroke", "#444")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(data.links)
      .join("line")
      .attr("stroke-width", d => Math.sqrt(d.value) * 2);

    // --- Draw Nodes ---
    const node = svg.append("g")
      .selectAll("circle")
      .data(data.nodes)
      .join("circle")
      .attr("r", d => d.size)
      .attr("fill", d => {
        switch (d.type) {
          case 'semantic': return '#3b82f6'; // Blue
          case 'episodic': return '#10b981'; // Green
          case 'procedural': return '#f59e0b'; // Amber
          default: return '#6b7280'; // Gray
        }
      })
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .on("click", (event, d) => {
        if (onNodeClick) onNodeClick(d.id);
      })
      .call(d3.drag<SVGCircleElement, Node>()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended) as any);

    // --- Labels ---
    const label = svg.append("g")
      .selectAll("text")
      .data(data.nodes)
      .join("text")
      .text(d => d.content.substring(0, 20) + "...")
      .attr("font-size", "10px")
      .attr("fill", "#94a3b8")
      .attr("dx", 12)
      .attr("dy", 4);

    // --- Tooltips (Simplified for now) ---
    node.append("title")
      .text(d => `${d.type}: ${d.content}\nScore: ${d.feedback.toFixed(2)}`);

    // --- Tick Function ---
    simulation.on("tick", () => {
      link
        .attr("x1", d => (d.source as Node).x!)
        .attr("y1", d => (d.source as Node).y!)
        .attr("x2", d => (d.target as Node).x!)
        .attr("y2", d => (d.target as Node).y!);

      node
        .attr("cx", d => d.x!)
        .attr("cy", d => d.y!);

      label
        .attr("x", d => d.x!)
        .attr("y", d => d.y!);
    });

    // --- Drag Handlers ---
    function dragstarted(event: any, d: Node) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: any, d: Node) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event: any, d: Node) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    return () => {
      simulation.stop();
    };
  }, [data, width, height]);

  return (
    <div className="w-full h-full bg-slate-950/50 rounded-xl border border-slate-800 overflow-hidden relative">
      <div className="absolute top-4 left-4 z-10">
        <h3 className="text-sm font-medium text-slate-200">Residual Pathway Map</h3>
        <p className="text-xs text-slate-500">Semantic connections between top 200 memories</p>
      </div>
      <svg 
        ref={svgRef} 
        width="100%" 
        height="100%" 
        viewBox={`0 0 ${width} ${height}`}
        className="cursor-move"
      />
      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-slate-900/80 p-2 rounded border border-slate-800 text-[10px] text-slate-400 space-y-1">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-blue-500"></div> Semantic
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500"></div> Episodic
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-amber-500"></div> Procedural
        </div>
      </div>
    </div>
  );
};

export default ResidualPathwayMap;
