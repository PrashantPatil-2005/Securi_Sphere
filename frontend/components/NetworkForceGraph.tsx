"use client";

import { useEffect, useRef } from "react";

interface Node {
  id: string;
  label: string;
  type: string;
  status: string;
  threat_score?: number;
  ip?: string;
}

interface Edge {
  from: string;
  to: string;
}

function nodeColor(n: Node) {
  if (n.type === "server") return "#3b82f6";
  if (n.status === "critical" || (n.threat_score ?? 0) >= 70) return "#ef4444";
  if (n.status === "warning" || (n.threat_score ?? 0) >= 40) return "#eab308";
  if (n.status === "online") return "#22c55e";
  return "#6b7280";
}

export function NetworkForceGraph({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || nodes.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const server = nodes.find((n) => n.type === "server");
    const hosts = nodes.filter((n) => n.type === "host");

    const positions: Record<string, { x: number; y: number; vx: number; vy: number }> = {};
    if (server) positions[server.id] = { x: cx, y: cy * 0.35, vx: 0, vy: 0 };
    hosts.forEach((host, i) => {
      const angle = (i / hosts.length) * Math.PI * 2 - Math.PI / 2;
      const r = Math.min(w, h) * 0.32;
      positions[host.id] = {
        x: cx + Math.cos(angle) * r,
        y: cy + Math.sin(angle) * r + 40,
        vx: 0,
        vy: 0,
      };
    });

    let frame = 0;
    let raf = 0;
    const tick = () => {
      frame++;
      ctx.clearRect(0, 0, w, h);
      for (const edge of edges) {
        const a = positions[edge.from];
        const b = positions[edge.to];
        if (!a || !b) continue;
        ctx.strokeStyle = "rgba(255,255,255,0.12)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
      for (const n of nodes) {
        const p = positions[n.id];
        if (!p) continue;
        if (n.type !== "server" && frame < 120) {
          p.vx += (cx - p.x) * 0.0002;
          p.vy += (cy + 60 - p.y) * 0.0002;
          p.x += p.vx;
          p.y += p.vy;
          p.vx *= 0.92;
          p.vy *= 0.92;
        }
        const color = nodeColor(n);
        ctx.beginPath();
        ctx.arc(p.x, p.y, n.type === "server" ? 28 : 22, 0, Math.PI * 2);
        ctx.fillStyle = color + "33";
        ctx.fill();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.fillStyle = "#e5e7eb";
        ctx.font = "11px system-ui";
        ctx.textAlign = "center";
        ctx.fillText(n.label, p.x, p.y + 36);
      }
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(raf);
  }, [nodes, edges]);

  return (
    <canvas
      ref={canvasRef}
      width={900}
      height={480}
      className="w-full rounded-lg glass-panel"
      aria-label="Network topology graph"
    />
  );
}
