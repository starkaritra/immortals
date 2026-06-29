import React from "react";
import {
  AbsoluteFill,
  Audio,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { C, vh, vw, MONO, glass } from "../theme";
import {
  Kicker,
  Dek,
  SlideShell,
  CenterBand,
  Flow,
  FStage,
  FConn,
  IcoCircle,
  Reveal,
} from "../components/primitives";
import { Icon, IconName } from "../components/icons";

const Pchip: React.FC<{ icon: IconName; label: string }> = ({ icon, label }) => (
  <span
    style={{
      background: C.chip,
      border: `1px solid ${C.line2}`,
      borderRadius: 999,
      padding: `${vh(0.5)}px ${vw(1.1)}px`,
      fontSize: vh(1.6),
      fontWeight: 600,
      display: "inline-flex",
      alignItems: "center",
    }}
  >
    <span style={{ color: C.accent, marginRight: "0.45em", display: "inline-flex" }}>
      <Icon name={icon} size={vh(1.8)} />
    </span>
    {label}
  </span>
);

// the 9 event-log lines (deck #term .tl), as render functions
const A = { color: C.accent2, fontWeight: 600 } as const; // agent name
const OK = { color: C.ok } as const;
const ASK = { color: C.warn } as const;
const ARR = { color: C.dim, fontWeight: 400 } as const; // dim arrow
const CMD = { color: C.accent } as const;

const TERM_LINES: React.ReactNode[] = [
  <span style={CMD}>&gt; innovation-digest</span>,
  <>{"  - "}<span style={A}>Humboldt</span>{"  research-sources ..."}</>,
  <>{"  "}<span style={OK}>[ok]</span>{" Humboldt "}<span style={ARR}>-&gt;</span>{" research_report"}</>,
  <>{"  - "}<span style={A}>Socrates</span>{"  stress-test ..."}</>,
  <>{"  "}<span style={OK}>[ok]</span>{" Socrates "}<span style={ARR}>-&gt;</span>{" design_critique   "}<span style={ARR}>&lt;- research_report</span></>,
  <>{"  "}<span style={ASK}>[?]</span>{" "}<span style={A}>Linus</span>{"  build-worker  -- awaiting approval"}</>,
  <>{"  "}<span style={OK}>[approved]</span></>,
  <>{"  "}<span style={OK}>[ok]</span>{" Linus "}<span style={ARR}>-&gt;</span>{" worker_impl"}</>,
  <span style={OK}>= run complete</span>,
];

const TERM_START = 40;
const TERM_CADENCE = 16;

const Term: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const shown = Math.max(0, Math.min(TERM_LINES.length, Math.floor((f - TERM_START) / TERM_CADENCE) + 1));
  const cursorOn = (f % fps) < fps / 2; // 1s step-end blink

  return (
    <div
      style={{
        width: Math.min(vw(56), 760),
        marginTop: vh(0.6),
        borderRadius: 12,
        overflow: "hidden",
        fontFamily: MONO,
        ...glass("rgba(12,15,22,.62)"),
      }}
    >
      <div
        style={{
          height: vh(3),
          display: "flex",
          alignItems: "center",
          gap: "0.5em",
          padding: `0 ${vw(1)}px`,
          background: "rgba(255,255,255,.04)",
          borderBottom: "1px solid rgba(255,255,255,.06)",
        }}
      >
        {["#f0625d", "#f5bf4f", "#5bc26a"].map((c) => (
          <i
            key={c}
            style={{ width: vh(0.95), height: vh(0.95), borderRadius: "50%", background: c, display: "block" }}
          />
        ))}
        <span style={{ fontSize: vh(1.25), color: C.dim, marginLeft: "0.5em" }}>
          innovation-digest · live event log
        </span>
      </div>
      <div
        style={{
          padding: `${vh(1.2)}px ${vw(1.2)}px`,
          fontSize: vh(1.5),
          lineHeight: 1.55,
          minHeight: vh(22),
        }}
      >
        {TERM_LINES.map((ln, i) => {
          const visible = i < shown;
          const isLast = i === shown - 1;
          return (
            <div
              key={i}
              style={{
                whiteSpace: "pre",
                opacity: visible ? 1 : 0,
                transform: visible ? "none" : "translateY(4px)",
              }}
            >
              {ln}
              {isLast && (
                <span
                  style={{
                    display: "inline-block",
                    width: "0.55em",
                    height: "1.05em",
                    verticalAlign: "-.18em",
                    background: C.accent,
                    marginLeft: "0.15em",
                    opacity: cursorOn ? 1 : 0,
                  }}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const Scene5Demo: React.FC = () => (
  <AbsoluteFill>
    <Audio src={staticFile("audio/s05.mp3")} />
    <SlideShell>
      <Kicker label="What you just saw" num="05" />
      <h1
        style={{
          fontSize: vh(5.1),
          lineHeight: 1.08,
          margin: `0 0 ${vh(1.4)}px`,
          fontWeight: 800,
          letterSpacing: "-.01em",
          maxWidth: "20ch",
        }}
      >
        <span style={{ color: C.accent }}>Silence</span> is the default.
      </h1>
      <Dek>
        It interrupts once — for a real judgment call — and tells you how much it handled on its own.
      </Dek>
      <CenterBand>
        <Flow>
          <Reveal delay={12} style={{ flex: 1, display: "flex" }}>
            <FStage icon={<IcoCircle variant="blue" text="1" />} title="Delegate" desc="One sentence, plain English." />
          </Reveal>
          <Reveal delay={18}><FConn /></Reveal>
          <Reveal delay={22} style={{ flex: 1, display: "flex" }}>
            <FStage icon={<IcoCircle variant="blue" text="2" />} title="Team forms" desc="A mini-DAG: research → critique → build." />
          </Reveal>
          <Reveal delay={28}><FConn /></Reveal>
          <Reveal delay={32} style={{ flex: 1, display: "flex" }}>
            <FStage icon={<IcoCircle variant="blue" text="3" />} title="Works silently" desc="A live counter of routine decisions it handles itself." />
          </Reveal>
          <Reveal delay={38}><FConn /></Reveal>
          <Reveal delay={42} style={{ flex: 1, display: "flex" }}>
            <FStage
              icon={<IcoCircle variant="amber" icon="bell" />}
              title="One calibrated ping"
              desc={
                <>
                  A genuine judgment call —
                  <span style={{ color: C.warn, display: "inline-flex", verticalAlign: "-.25vh", margin: "0 .15em" }}>
                    <Icon name="bellOff" size={vh(1.7)} />
                  </span>
                  held back 9 routine choices.
                </>
              }
            />
          </Reveal>
          <Reveal delay={48}><FConn /></Reveal>
          <Reveal delay={52} style={{ flex: 1, display: "flex" }}>
            <FStage icon={<IcoCircle variant="green" icon="check" />} title="Verified report" desc="Provenance-stamped. Auditable from the event log." />
          </Reveal>
        </Flow>

        <div style={{ display: "flex", gap: vw(0.8), justifyContent: "center", alignItems: "center", flexWrap: "wrap" }}>
          <Pchip icon="person" label="PM" />
          <Pchip icon="bars" label="Applied / DS" />
          <Pchip icon="code" label="SWE" />
          <span style={{ fontSize: vh(1.5), color: C.muted }}>— same loop, role-tailored task</span>
        </div>

        <Term />
      </CenterBand>
    </SlideShell>
  </AbsoluteFill>
);
