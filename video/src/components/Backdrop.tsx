import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { WIDTH, HEIGHT } from "../theme";

// Deterministic 26-node drifting constellation (deck #nodegraph), recomputed per
// frame so it renders identically across Remotion's parallel workers.
function mulberry32(seed: number) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type Node = { x: number; y: number; vx: number; vy: number };
const NODES: Node[] = (() => {
  const r = mulberry32(0x9e3779b1);
  const out: Node[] = [];
  for (let i = 0; i < 26; i++) {
    out.push({
      x: r(),
      y: r(),
      vx: (r() - 0.5) * 0.00032,
      vy: (r() - 0.5) * 0.00032,
    });
  }
  return out;
})();

const wrap = (v: number) => ((v % 1) + 1) % 1;

export const Backdrop: React.FC = () => {
  const f = useCurrentFrame();
  // fade in over ~0.8s (deck .on transition)
  const op = interpolate(f, [0, 24], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const pts = NODES.map((n) => ({
    x: wrap(n.x + n.vx * f) * WIDTH,
    y: wrap(n.y + n.vy * f) * HEIGHT,
  }));

  const lines: React.ReactNode[] = [];
  const TH = 0.16;
  for (let a = 0; a < pts.length; a++) {
    for (let b = a + 1; b < pts.length; b++) {
      const dx = (pts[a].x - pts[b].x) / WIDTH;
      const dy = (pts[a].y - pts[b].y) / HEIGHT;
      const dd = Math.sqrt(dx * dx + dy * dy);
      if (dd < TH) {
        lines.push(
          <line
            key={`${a}-${b}`}
            x1={pts[a].x}
            y1={pts[a].y}
            x2={pts[b].x}
            y2={pts[b].y}
            stroke={`rgba(122,150,230,${((1 - dd / TH) * 0.16).toFixed(3)})`}
            strokeWidth={1.5}
          />
        );
      }
    }
  }

  return (
    <svg
      width={WIDTH}
      height={HEIGHT}
      style={{ position: "absolute", inset: 0, opacity: op, pointerEvents: "none" }}
    >
      {lines}
      {pts.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill="rgba(150,180,255,0.42)" />
      ))}
    </svg>
  );
};
