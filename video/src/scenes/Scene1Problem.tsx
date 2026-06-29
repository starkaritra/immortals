import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { C, vh, vw } from "../theme";
import { Backdrop } from "../components/Backdrop";
import { Kicker, Dek, SlideShell, useEntrance } from "../components/primitives";
import { Icon } from "../components/icons";

const IdeaCard: React.FC<{ t: string; s: string; delay: number }> = ({ t, s, delay }) => {
  const ent = useEntrance(delay, 12);
  return (
    <div
      style={{
        background: C.panel,
        border: `1px solid ${C.line}`,
        borderRadius: 12,
        padding: `${vh(1.6)}px ${vw(1.4)}px`,
        minWidth: vw(11),
        opacity: 0.45 * ent.opacity,
        filter: "grayscale(.4)",
        transform: ent.transform,
      }}
    >
      <div style={{ fontWeight: 700, fontSize: vh(1.9), marginBottom: vh(0.5) }}>{t}</div>
      <div style={{ fontSize: vh(1.5), color: C.dim }}>{s}</div>
      <div
        style={{
          marginTop: vh(1),
          fontSize: vh(1.35),
          color: C.warn,
          letterSpacing: "0.04em",
          display: "flex",
          alignItems: "center",
          gap: "0.35em",
        }}
      >
        <Icon name="clock" size={vh(1.4)} />
        waiting
      </div>
    </div>
  );
};

export const Scene1Problem: React.FC = () => (
  <AbsoluteFill>
    <Audio src={staticFile("audio/s01.mp3")} />
    <Backdrop />
    <SlideShell>
      <Kicker label="The problem" num="01" />
      <h1
        style={{
          fontSize: vh(6.0),
          lineHeight: 1.08,
          margin: `0 0 ${vh(1.4)}px`,
          fontWeight: 800,
          letterSpacing: "-.01em",
          maxWidth: "18ch",
        }}
      >
        Your best ideas are
        <br />
        stuck in your head.
      </h1>
      <Dek>The bottleneck isn't your ideas — it's everything it takes to ship one.</Dek>
      <div style={{ display: "flex", gap: vw(3), alignItems: "center", flex: 1 }}>
        <p
          style={{
            fontSize: vh(2.55),
            lineHeight: 1.5,
            color: C.fg,
            maxWidth: "46ch",
            flex: 1,
            margin: 0,
          }}
        >
          A research dive you keep postponing. A tool you'd build with a free week. A paper, a
          prototype, a plan.{" "}
          <span style={{ color: C.muted }}>
            They wait — because <em>doing</em> one means being a researcher, a critic, an
            engineer, and a project manager, all at once, all yourself.
          </span>
        </p>
        <div style={{ display: "flex", gap: vw(1.2), flexWrap: "wrap", maxWidth: vw(42) }}>
          <IdeaCard t="That research dive" s='"someday…"' delay={16} />
          <IdeaCard t="The tool you'd build" s='"if I had a week"' delay={24} />
          <IdeaCard t="The paper" s='"half-drafted"' delay={32} />
        </div>
      </div>
    </SlideShell>
  </AbsoluteFill>
);
