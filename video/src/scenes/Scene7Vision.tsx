import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { C, vh } from "../theme";
import { Backdrop } from "../components/Backdrop";
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

export const Scene7Vision: React.FC = () => (
  <AbsoluteFill>
    <Audio src={staticFile("audio/s07.mp3")} />
    <Backdrop />
    <SlideShell>
      <Kicker label="The vision" num="07" />
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
        Today: minutes.
        <br />
        Next: <span style={{ color: C.accent }}>days.</span>
      </h1>
      <Dek>
        Delegate and walk away for days — and it earns the autonomy to handle more, the more it learns you.
      </Dek>
      <p style={{ fontSize: vh(2.55), lineHeight: 1.5, color: C.fg, maxWidth: "46ch", margin: `0 0 ${vh(0.6)}px` }}>
        A long-running agent you delegate to for days — it survives restarts, learns which calls you want
        to make, and <span style={{ color: C.accent2 }}>earns</span> more autonomy.{" "}
        <span style={{ color: C.muted }}>Always task-scoped; never watching your life.</span>
      </p>
      <CenterBand>
        <Flow>
          <Reveal delay={14} style={{ flex: 1, display: "flex" }}>
            <FStage
              icon={<IcoCircle variant="green" icon="gauge" />}
              phase="Phase 6.5"
              phaseColor={C.ok}
              title="Eval-first"
              desc="An outcome-quality harness — the keystone."
            />
          </Reveal>
          <Reveal delay={20}><FConn /></Reveal>
          <Reveal delay={24} style={{ flex: 1, display: "flex" }}>
            <FStage icon={<IcoCircle variant="blue" icon="refresh" />} phase="Phase 7" title="Durable lifecycle" desc="Tasks survive restarts; park & resume for days." />
          </Reveal>
          <Reveal delay={30}><FConn /></Reveal>
          <Reveal delay={34} style={{ flex: 1, display: "flex" }}>
            <FStage icon={<IcoCircle variant="blue" icon="server" />} phase="Phase 8" title="Manager-as-a-service" desc="An always-on daemon + streaming API." />
          </Reveal>
          <Reveal delay={40}><FConn /></Reveal>
          <Reveal delay={44} style={{ flex: 1, display: "flex" }}>
            <FStage
              icon={<IcoCircle variant="indigo" icon="star" star />}
              phase="Phase 9 ★"
              phaseColor={C.accent2}
              title="Calibrated check-ins"
              titleColor="#fff"
              desc="The novel core — when to interrupt. precision > recall."
            />
          </Reveal>
          <Reveal delay={50}><FConn /></Reveal>
          <Reveal delay={54} style={{ flex: 1, display: "flex" }}>
            <FStage icon={<IcoCircle variant="blue" icon="chat" />} phase="Phase 10" title="Bubble + earned autonomy" desc="patrecAS learns you; the desktop client." />
          </Reveal>
        </Flow>
      </CenterBand>
    </SlideShell>
  </AbsoluteFill>
);
