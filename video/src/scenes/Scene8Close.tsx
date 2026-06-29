import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { C, vh, vw, FONT } from "../theme";
import { Backdrop } from "../components/Backdrop";
import { Kicker, useEntrance, Reveal } from "../components/primitives";

export const Scene8Close: React.FC = () => {
  const ent = useEntrance(0, 16);
  return (
    <AbsoluteFill>
      <Audio src={staticFile("audio/s08.mp3")} />
      <Backdrop />
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: `${vh(5)}px ${vw(6.2)}px ${vh(8)}px`,
          fontFamily: FONT,
          color: C.fg,
          ...ent,
        }}
      >
        <Kicker label="Immortals" center />
        <h1
          style={{
            fontSize: vh(5.6),
            lineHeight: 1.08,
            margin: `0 0 ${vh(1.4)}px`,
            fontWeight: 800,
            letterSpacing: "-.01em",
            maxWidth: "24ch",
          }}
        >
          An expert team — for every
          <br />
          person at Microsoft.
        </h1>
        <Reveal delay={18}>
          <p
            style={{
              fontSize: vh(2.1),
              color: C.muted,
              maxWidth: "50ch",
              margin: `${vh(1.5)}px auto ${vh(2.5)}px`,
              lineHeight: 1.5,
            }}
          >
            Microsoft's mission is to{" "}
            <b style={{ color: C.fg }}>
              empower every person and every organization on the planet to achieve more.
            </b>{" "}
            Immortals gives every one of us an expert team to delegate to.
          </p>
        </Reveal>
        <Reveal delay={30}>
          <div
            style={{
              fontSize: vh(3.0),
              fontWeight: 800,
              backgroundImage: `linear-gradient(90deg,${C.accent},${C.accent2})`,
              WebkitBackgroundClip: "text",
              backgroundClip: "text",
              color: "transparent",
            }}
          >
            Your next idea doesn't wait in your head. It ships.
          </div>
        </Reveal>
        <Reveal delay={42}>
          <div style={{ marginTop: vh(3), fontSize: vh(2.4), fontWeight: 800, letterSpacing: "0.04em" }}>
            <span style={{ color: C.accent }}>⚔</span> Immortals
          </div>
        </Reveal>
      </div>
    </AbsoluteFill>
  );
};
