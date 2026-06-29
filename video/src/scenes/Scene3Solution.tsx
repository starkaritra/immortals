import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { C, vh, vw, GLOW } from "../theme";
import { Kicker, Dek, SlideShell, useEntrance } from "../components/primitives";
import { Backdrop } from "../components/Backdrop";

const SpecNode: React.FC<{ name: string; role: string; delay: number }> = ({
  name,
  role,
  delay,
}) => {
  const ent = useEntrance(delay, 10);
  return (
    <div
      style={{
        border: `1px solid ${C.line}`,
        background: C.panel,
        borderRadius: 12,
        fontWeight: 700,
        fontSize: vh(1.65),
        textAlign: "center",
        whiteSpace: "nowrap",
        padding: `${vh(0.9)}px ${vw(0.9)}px`,
        lineHeight: 1.2,
        ...ent,
      }}
    >
      {name}
      <span
        style={{
          display: "block",
          fontWeight: 400,
          fontSize: vh(1.12),
          color: C.muted,
          marginTop: vh(0.2),
          letterSpacing: "0.2px",
        }}
      >
        {role}
      </span>
    </div>
  );
};

const Arrow: React.FC<{ delay: number }> = ({ delay }) => {
  const ent = useEntrance(delay, 8);
  return (
    <div style={{ color: C.accent, fontSize: vh(2.6), fontWeight: 800, ...ent }}>→</div>
  );
};

export const Scene3Solution: React.FC = () => {
  const you = useEntrance(14, 10);
  const mgr = useEntrance(26, 10);
  return (
    <AbsoluteFill>
      <Audio src={staticFile("audio/s03.mp3")} />
      <Backdrop />
      <SlideShell>
        <Kicker label="The solution" num="03" />
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
          Immortals:{" "}
          <span style={{ color: C.accent }}>
            an enterprise
            <br />
            team you delegate to.
          </span>
        </h1>
        <Dek>
          You talk to one manager; a whole expert team does the work behind it — and you get back a
          finished result.
        </Dek>
        <p
          style={{
            fontSize: vh(2.55),
            lineHeight: 1.5,
            color: C.fg,
            maxWidth: "46ch",
            margin: `0 0 ${vh(2.2)}px`,
          }}
        >
          Hand one manager your goal in plain English — it{" "}
          <span style={{ color: C.accent2 }}>brings your ideas to life</span>: writes a real plan,
          picks the right specialists, and runs them for you.
        </p>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: vw(1.6),
            flexWrap: "nowrap",
            flex: 1,
          }}
        >
          <div
            style={{
              borderRadius: 12,
              padding: `${vh(1.3)}px ${vw(1.1)}px`,
              fontWeight: 700,
              fontSize: vh(1.9),
              textAlign: "center",
              border: `1px solid ${C.line2}`,
              background: "linear-gradient(135deg,#2a3550,#1c2336)",
              whiteSpace: "nowrap",
              ...you,
            }}
          >
            You
            <br />
            <span style={{ fontWeight: 400, fontSize: vh(1.4), color: C.muted }}>
              plain English
            </span>
          </div>
          <Arrow delay={20} />
          <div
            style={{
              borderRadius: 12,
              padding: `${vh(1.6)}px ${vw(1.4)}px`,
              fontWeight: 700,
              fontSize: vh(2.1),
              textAlign: "center",
              background: `linear-gradient(135deg,${C.accent},${C.accent2})`,
              color: "#06101f",
              boxShadow: GLOW,
              whiteSpace: "nowrap",
              ...mgr,
            }}
          >
            Alex Ferguson
            <br />
            <span style={{ fontWeight: 400, fontSize: vh(1.4) }}>
              the manager · plan · route · synthesize
            </span>
          </div>
          <Arrow delay={34} />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2,auto)",
              gap: `${vh(0.8)}px ${vw(1)}px`,
            }}
          >
            <SpecNode name="Humboldt" role="researcher" delay={42} />
            <SpecNode name="Socrates" role="critic" delay={48} />
            <SpecNode name="Linus" role="coder" delay={54} />
            <SpecNode name="Curie" role="experimentalist" delay={60} />
            <SpecNode name="Feynman" role="teacher" delay={66} />
            <SpecNode name="+ Darwin · Edison · Sagan" role="author · inventor · orator" delay={72} />
          </div>
        </div>
      </SlideShell>
    </AbsoluteFill>
  );
};
