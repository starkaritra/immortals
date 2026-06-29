import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { C, vh, vw, GLOW } from "../theme";
import { Kicker, Dek, SlideShell, useEntrance } from "../components/primitives";

const Pt: React.FC<{ head: string; mut: string }> = ({ head, mut }) => (
  <li
    style={{
      position: "relative",
      padding: `${vh(0.9)}px 0 ${vh(0.9)}px 2.2em`,
      fontSize: vh(2.3),
      lineHeight: 1.4,
      color: C.fg,
    }}
  >
    <span
      style={{
        position: "absolute",
        left: 0,
        top: vh(1.5),
        width: "0.7em",
        height: "0.7em",
        borderRadius: 2,
        background: C.fail,
        transform: "rotate(45deg)",
      }}
    />
    {head} <span style={{ color: C.muted }}>{mut}</span>
  </li>
);

export const Scene2Aggravate: React.FC = () => {
  const box = useEntrance(14, 14);
  return (
    <AbsoluteFill>
      <Audio src={staticFile("audio/s02.mp3")} />
      <SlideShell>
        <Kicker label="Why it's still hard" num="02" />
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
          AI gave you a chatbot,
          <br />
          not a team.
        </h1>
        <Dek>
          One generalist with no plan and no memory isn't a team — it's another tab to manage.
        </Dek>
        <div style={{ display: "flex", gap: vw(3), alignItems: "center", flex: 1 }}>
          <div
            style={{
              background: C.panel,
              border: `1px solid ${C.line}`,
              borderRadius: 16,
              padding: `${vh(2.4)}px ${vw(1.8)}px`,
              width: vw(30),
              boxShadow: GLOW,
              opacity: box.opacity,
              transform: box.transform,
            }}
          >
            <div
              style={{
                fontSize: vh(1.4),
                color: C.dim,
                textTransform: "uppercase",
                letterSpacing: "0.16em",
                marginBottom: vh(1.2),
              }}
            >
              Today: one generalist
            </div>
            <div
              style={{
                background: C.panel2,
                border: `1px solid ${C.line}`,
                borderRadius: "14px 14px 14px 4px",
                padding: `${vh(1.4)}px ${vw(1.2)}px`,
                color: C.muted,
                fontSize: vh(1.8),
                lineHeight: 1.4,
              }}
            >
              "Here's a wall of text. Good luck — let me know if you need anything else."
            </div>
            <div
              style={{
                marginTop: vh(1.6),
                display: "flex",
                flexDirection: "column",
                gap: vh(0.7),
              }}
            >
              {[
                "✗ You still break the work down",
                "✗ You still check & fix it",
                "✗ You still stitch it together",
                "✗ No plan · no memory of an hour ago",
              ].map((s) => (
                <span key={s} style={{ fontSize: vh(1.7), color: C.fail }}>
                  {s}
                </span>
              ))}
            </div>
          </div>
          <ul style={{ listStyle: "none", padding: 0, margin: `${vh(0.4)}px 0`, maxWidth: "50ch", flex: 1 }}>
            <Pt head="One chatbot." mut="One generalist doing every role badly." />
            <Pt head="No plan." mut="You're the project manager by default." />
            <Pt head="No memory." mut="It forgets what it did an hour ago." />
          </ul>
        </div>
      </SlideShell>
    </AbsoluteFill>
  );
};
