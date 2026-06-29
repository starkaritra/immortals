import React from "react";

// Inline stroke glyphs ported verbatim from the deck (viewBox 0 0 24 24,
// fill:none; stroke:currentColor). Each entry returns the inner SVG nodes.
const GLYPHS: Record<string, React.ReactNode> = {
  // slide 1 — waiting clock
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5V12l3 2" />
    </>
  ),
  // slide 4 — typed plan (DAG)
  dag: (
    <>
      <circle cx="12" cy="5" r="2.1" />
      <circle cx="6" cy="19" r="2.1" />
      <circle cx="18" cy="19" r="2.1" />
      <path d="M10.8 6.6 7.2 17.4M13.2 6.6 16.8 17.4" />
    </>
  ),
  // slide 4 — deterministic orchestrator (gear)
  gear: (
    <>
      <circle cx="12" cy="12" r="3.1" />
      <path d="M12 2.6v3.1M12 18.3v3.1M21.4 12h-3.1M5.7 12H2.6M18.6 5.4l-2.2 2.2M7.6 16.4l-2.2 2.2M18.6 18.6l-2.2-2.2M7.6 7.6 5.4 5.4" />
    </>
  ),
  // slide 4 — AgentRunner (chip)
  chip: (
    <>
      <rect x="6.5" y="6.5" width="11" height="11" rx="2" />
      <rect x="10" y="10" width="4" height="4" rx="1" />
      <path d="M9 3.5v3M15 3.5v3M9 17.5v3M15 17.5v3M3.5 9h3M3.5 15h3M17.5 9h3M17.5 15h3" />
    </>
  ),
  // slide 4 — event-sourced memory (database)
  database: (
    <>
      <ellipse cx="12" cy="5.5" rx="6.5" ry="2.6" />
      <path d="M5.5 5.5v13c0 1.45 2.9 2.6 6.5 2.6s6.5-1.15 6.5-2.6v-13" />
      <path d="M5.5 12c0 1.45 2.9 2.6 6.5 2.6s6.5-1.15 6.5-2.6" />
    </>
  ),
  // slide 5 — one calibrated ping (bell)
  bell: (
    <>
      <path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6z" />
      <path d="M10.3 20a1.9 1.9 0 0 0 3.4 0" />
    </>
  ),
  // slide 5 — held-back (bell-off, inline mini)
  bellOff: (
    <path d="M9 9a6 6 0 0 1 9-1M6 9.5c0 4.5-2 5.5-2 5.5h11M10.3 19a1.9 1.9 0 0 0 3.4 0M3 3l18 18" />
  ),
  // slide 5 — verified report (check)
  check: <path d="M5 12.5l4.2 4.5L19 7" />,
  // slide 5 — personas
  person: (
    <>
      <circle cx="12" cy="8" r="3.4" />
      <path d="M5 20c0-3.7 3.1-6.2 7-6.2s7 2.5 7 6.2" />
    </>
  ),
  bars: (
    <>
      <path d="M3.5 21h17" />
      <rect x="5" y="11" width="3" height="7" />
      <rect x="10.5" y="6" width="3" height="12" />
      <rect x="16" y="13" width="3" height="5" />
    </>
  ),
  code: <path d="M8.5 8.5 4 12l4.5 3.5M15.5 8.5 20 12l-4.5 3.5M13.5 5.5l-3 13" />,
  // shared connector chevron
  chevron: <path d="M9 6l6 6-6 6" />,
  // slide 6 — caveat triangle
  caveat: (
    <>
      <path d="M12 3.5 22 20H2L12 3.5z" />
      <path d="M12 10v4.5M12 17.2v.01" />
    </>
  ),
  // slide 7 — eval-first ("now" gauge)
  gauge: (
    <>
      <path d="M4 19a8 8 0 1 1 16 0" />
      <path d="M12 19l4.5-5.5" />
      <circle cx="12" cy="19" r="1.3" fill="currentColor" stroke="none" />
    </>
  ),
  // slide 7 — durable lifecycle (refresh)
  refresh: (
    <>
      <path d="M20 11A8 8 0 0 0 6.3 6.3L3.5 9" />
      <path d="M3.5 4.5V9H8" />
      <path d="M4 13a8 8 0 0 0 13.7 4.7l2.8-2.7" />
      <path d="M20.5 19.5V15H16" />
    </>
  ),
  // slide 7 — manager-as-a-service (server)
  server: (
    <>
      <rect x="3.5" y="4.5" width="17" height="6" rx="1.6" />
      <rect x="3.5" y="13" width="17" height="6" rx="1.6" />
      <path d="M7 7.5h.01M7 16h.01" />
    </>
  ),
  // slide 7 — calibrated check-ins (star)
  star: (
    <path d="M12 3.2l2.6 5.7 6.2.8-4.6 4.3 1.2 6.1-5.4-3-5.4 3 1.2-6.1-4.6-4.3 6.2-.8z" />
  ),
  // slide 7 — bubble + earned autonomy (chat)
  chat: (
    <>
      <path d="M20.5 11.5a7.5 7.5 0 0 1-10.8 6.8L4 20l1.7-5.6A7.5 7.5 0 1 1 20.5 11.5z" />
      <path d="M9 11h.01M12.5 11h.01M16 11h.01" />
    </>
  ),
};

export type IconName = keyof typeof GLYPHS;

export const Icon: React.FC<{
  name: IconName;
  size?: number;
  strokeWidth?: number;
  style?: React.CSSProperties;
}> = ({ name, size = 24, strokeWidth = 2, style }) => (
  <svg
    viewBox="0 0 24 24"
    width={size}
    height={size}
    style={{
      fill: "none",
      stroke: "currentColor",
      strokeWidth,
      strokeLinecap: "round",
      strokeLinejoin: "round",
      ...style,
    }}
  >
    {GLYPHS[name]}
  </svg>
);
