import React from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame } from "remotion";
import { C, vh, vw, glass } from "../theme";
import { Kicker, Dek, SlideShell, easeOut } from "../components/primitives";
import { Icon } from "../components/icons";

const CountUp: React.FC<{ to: number; start?: number; comma?: boolean }> = ({
  to,
  start = 10,
  comma,
}) => {
  const f = useCurrentFrame();
  const dur = 30; // ~1s (deck count-up duration)
  const p = Math.max(0, Math.min(1, (f - start) / dur));
  const v = Math.round(easeOut(p) * to);
  return <>{comma ? v.toLocaleString("en-US") : String(v)}</>;
};

const Stat: React.FC<{
  value: React.ReactNode;
  klass: "ok" | "bl";
  label: React.ReactNode;
}> = ({ value, klass, label }) => (
  <div
    style={{
      borderRadius: 14,
      padding: `${vh(1.5)}px ${vw(1.4)}px`,
      minWidth: vw(9),
      textAlign: "center",
      ...glass(),
    }}
  >
    <div style={{ fontSize: vh(3.6), fontWeight: 800, lineHeight: 1, color: klass === "ok" ? C.ok : C.accent }}>
      {value}
    </div>
    <div style={{ fontSize: vh(1.4), color: C.muted, marginTop: vh(0.7) }}>{label}</div>
  </div>
);

export const Scene6Results: React.FC = () => (
  <AbsoluteFill>
    <Audio src={staticFile("audio/s06.mp3")} />
    <SlideShell>
      <Kicker label="Results · a real run" num="06" />
      <div style={{ margin: "auto 0", display: "flex", flexDirection: "column", minHeight: 0 }}>
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
          A real build. <span style={{ color: C.ok }}>Verified</span> &amp; audited.
        </h1>
        <Dek>
          A critic that catches a critical flaw the plan missed is a real team — not one yes-man chatbot.
        </Dek>
        <p style={{ fontSize: vh(2.55), lineHeight: 1.5, color: C.fg, maxWidth: "46ch", margin: `0 0 ${vh(1.2)}px` }}>
          We handed it a genuine product — a weekly research digest: a <b>Cloudflare</b> backend + a{" "}
          <b>Chrome</b> extension, end to end.
        </p>

        <div style={{ display: "flex", gap: vw(1.2), flexWrap: "wrap", margin: `${vh(0.6)}px 0 ${vh(1.8)}px` }}>
          <Stat klass="ok" value={<><CountUp to={8} />/8</>} label={<>pre-registered<br />criteria passed</>} />
          <Stat klass="ok" value={<><CountUp to={78} />/78</>} label={<>tests passing<br />(55 worker · 23 ext)</>} />
          <Stat klass="bl" value={<><CountUp to={4} /> / <CountUp to={3} /></>} label={<>DAG nodes /<br />specialists</>} />
          <Stat klass="bl" value={<CountUp to={22} />} label={<>event log<br />(replayable)</>} />
          <Stat klass="bl" value={<>~<CountUp to={42} />m</>} label={<>agent compute<br /><CountUp to={155540} comma /> tokens</>} />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: vw(1), borderRadius: 14, padding: `${vh(1.6)}px ${vw(1.4)}px`, maxWidth: vw(78), ...glass() }}>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: vh(0.5), borderLeft: `3px solid ${C.fail}`, paddingLeft: vw(1) }}>
            <div style={{ fontSize: vh(1.35), letterSpacing: "0.14em", textTransform: "uppercase", color: C.dim }}>
              The naive plan
            </div>
            <div style={{ fontSize: vh(1.7), lineHeight: 1.35 }}>
              <span style={{ color: C.fail, fontWeight: 700 }}>Summarize one item per call</span> → blows
              Cloudflare's hard <b>50-subrequest</b> cap → the digest <b>aborts mid-run.</b>
            </div>
          </div>
          <div style={{ color: C.accent, fontSize: vh(2.6), fontWeight: 800 }}>→</div>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: vh(0.5), borderLeft: `3px solid ${C.ok}`, paddingLeft: vw(1) }}>
            <div style={{ fontSize: vh(1.35), letterSpacing: "0.14em", textTransform: "uppercase", color: C.dim }}>
              The critic caught it — on its own
            </div>
            <div style={{ fontSize: vh(1.7), lineHeight: 1.35 }}>
              <span style={{ color: C.ok, fontWeight: 700 }}>Socrates</span>{" "}
              <span style={{ color: C.muted }}>(the critic)</span> flagged the flaw;{" "}
              <span style={{ color: C.ok, fontWeight: 700 }}>Linus</span>{" "}
              <span style={{ color: C.muted }}>(the coder)</span> shipped <b>batched summarization.</b>{" "}
              Better architecture than the plan it was handed.
            </div>
          </div>
        </div>

        <div style={{ fontSize: vh(1.55), color: C.muted, marginTop: vh(1.2), display: "flex", gap: "0.6em", alignItems: "center" }}>
          <span style={{ color: C.warn, display: "inline-flex" }}>
            <Icon name="caveat" size={vh(2)} />
          </span>
          Honest caveat: headless agents verify by build · typecheck · tests · dry-run — the final deploy is still a human click.
        </div>
      </div>
    </SlideShell>
  </AbsoluteFill>
);
