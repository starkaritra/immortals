// Immortals brand design system, ported 1:1 from presentation/immortals-pitch.html.
// The deck is authored in vh/vw units against the viewport; this video renders at a
// fixed 1920x1080, so 1vh = 10.8px and 1vw = 19.2px. The helpers below reproduce the
// deck's sizing faithfully.

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;

export const vh = (n: number): number => (n * HEIGHT) / 100;
export const vw = (n: number): number => (n * WIDTH) / 100;

// :root brand palette (matched to prototype/jarvis-bubble + dashboard)
export const C = {
  bg: "#0b0d12",
  desk1: "#0f1320",
  panel: "#171a21",
  panel2: "#1e222b",
  line: "#2a2f3a",
  line2: "#39414f",
  fg: "#e9ecf2",
  muted: "#9aa3b2",
  dim: "#5b6577",
  accent: "#6ea8fe",
  accent2: "#8b7cff",
  ok: "#4ec9a8",
  warn: "#e0b341",
  fail: "#f06d6d",
  chip: "#283041",
} as const;

export const FONT =
  '"Segoe UI", system-ui, -apple-system, Roboto, Helvetica, Arial, sans-serif';
export const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";

export const GLOW =
  "0 0 0 4px rgba(110,168,254,.16), 0 18px 50px rgba(0,0,0,.55)";

// Deck #deck background.
export const DECK_BG =
  "radial-gradient(1300px 800px at 72% -12%, #18203a 0%, #0f1320 46%, #0b0d12 100%)";

// Slides that show the ambient node-graph backdrop (deck: GRAPH_SLIDES {0,2,6,7}).
export const GRAPH_SLIDES = new Set([1, 3, 7, 8]); // 1-indexed slide numbers

// Frosted-glass surface used by panels/stats/terminal.
export const glass = (bg = "rgba(23,26,33,.55)"): React.CSSProperties => ({
  background: bg,
  border: "1px solid rgba(255,255,255,.08)",
  backdropFilter: "blur(9px) saturate(1.15)",
  WebkitBackdropFilter: "blur(9px) saturate(1.15)",
  boxShadow:
    "inset 0 1px 0 rgba(255,255,255,.05), 0 14px 34px rgba(0,0,0,.4)",
});
