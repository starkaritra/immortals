import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { C, vh, vw, FONT } from "../theme";
import { easeOut } from "./primitives";

type SceneT = {
  durationFrames: number;
  captions: { startSec: number; endSec: number; text: string }[];
};

export const Chrome: React.FC<{ scenes: SceneT[]; showCaptions?: boolean }> = ({
  scenes,
  showCaptions = true,
}) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const N = scenes.length;

  // scene boundaries (start frame of each scene)
  const starts: number[] = [];
  let acc = 0;
  for (const s of scenes) {
    starts.push(acc);
    acc += s.durationFrames;
  }
  // active index
  let idx = 0;
  for (let i = 0; i < N; i++) if (f >= starts[i]) idx = i;
  const localF = f - starts[idx];
  const localSec = localF / fps;

  // spine node positions (i / (N-1) * 100)
  const pos = (i: number) => (N === 1 ? 50 : (i / (N - 1)) * 100);
  // dot eases from prev node to current over 0.6s at each boundary
  const T = 0.6 * fps;
  const dotLeft =
    idx === 0 || localF >= T
      ? pos(idx)
      : pos(idx - 1) + (pos(idx) - pos(idx - 1)) * easeOut(localF / T);

  // orb breathe + per-scene pulse
  const breathe = 1 + 0.06 * Math.sin((f / (3.6 * fps)) * Math.PI * 2);
  const pulseP = Math.min(1, localF / (0.75 * fps)); // 0..1 over 0.75s
  const ringSize = 16 * pulseP;
  const ringOpacity = 0.5 * (1 - pulseP);

  // top progress bar: width = idx/(N-1), animated gradient slide
  const barW = (idx / (N - 1)) * 100;
  const bgPos = (((f / (6 * fps)) % 1) * 200).toFixed(1);

  const clock = Math.floor(f / fps);
  const mm = String(Math.floor(clock / 60)).padStart(2, "0");
  const ss = String(clock % 60).padStart(2, "0");

  // active caption cue for the current scene
  let caption = "";
  if (showCaptions) {
    for (const c of scenes[idx].captions) {
      if (localSec >= c.startSec && localSec < c.endSec) {
        caption = c.text;
        break;
      }
    }
  }

  return (
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none", fontFamily: FONT }}>
      {/* top progress bar */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          height: 3,
          width: `${barW}%`,
          background: `linear-gradient(90deg,${C.accent},${C.accent2},${C.accent})`,
          backgroundSize: "200% 100%",
          backgroundPositionX: `${bgPos}%`,
        }}
      />

      {/* ⚔ orb (top-right) */}
      <div
        style={{
          position: "absolute",
          top: vh(2.4),
          right: vw(2),
          width: vh(5.2),
          height: vh(5.2),
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            boxShadow: `0 0 0 ${ringSize}px rgba(110,168,254,${ringOpacity})`,
          }}
        />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "100%",
            height: "100%",
            borderRadius: "50%",
            fontSize: vh(2.4),
            color: "#06101f",
            fontWeight: 800,
            transform: `scale(${breathe})`,
            background:
              "radial-gradient(circle at 35% 30%, #9cc1ff 0%, #6ea8fe 42%, #8b7cff 100%)",
            boxShadow: "0 0 0 4px rgba(110,168,254,.14),0 10px 30px rgba(0,0,0,.5)",
          }}
        >
          ⚔
        </div>
      </div>

      {/* DAG spine */}
      <div
        style={{
          position: "absolute",
          left: vw(6.2),
          right: vw(6.2),
          bottom: vh(6),
          height: 14,
        }}
      >
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: 0,
            right: 0,
            height: 2,
            transform: "translateY(-50%)",
            background:
              "linear-gradient(90deg,rgba(110,168,254,.22),rgba(139,124,255,.22))",
          }}
        />
        {scenes.map((_, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              top: "50%",
              left: `${pos(i)}%`,
              width: 7,
              height: 7,
              borderRadius: "50%",
              transform: "translate(-50%,-50%)",
              background: i <= idx ? C.accent : C.line2,
            }}
          />
        ))}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: `${dotLeft}%`,
            width: 13,
            height: 13,
            borderRadius: "50%",
            transform: "translate(-50%,-50%)",
            background:
              "radial-gradient(circle at 40% 35%,#bcd4ff,#6ea8fe 55%,#8b7cff)",
            boxShadow: "0 0 12px 3px rgba(110,168,254,.6)",
          }}
        />
      </div>

      {/* captions (lower-third, from the TTS subtitles) */}
      {caption && (
        <div
          style={{
            position: "absolute",
            left: "50%",
            bottom: vh(8.2),
            transform: "translateX(-50%)",
            maxWidth: vw(62),
            textAlign: "center",
            fontSize: vh(1.9),
            lineHeight: 1.35,
            color: C.fg,
            padding: `${vh(0.7)}px ${vw(1.3)}px`,
            borderRadius: 12,
            background: "rgba(11,13,18,.62)",
            backdropFilter: "blur(8px)",
            WebkitBackdropFilter: "blur(8px)",
            border: "1px solid rgba(255,255,255,.07)",
          }}
        >
          {caption}
        </div>
      )}

      {/* footer */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: vh(5.2),
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: `0 ${vw(2.4)}px`,
          fontSize: vh(1.45),
          color: C.dim,
          borderTop: `1px solid ${C.line}`,
          background: "rgba(11,13,18,.72)",
          backdropFilter: "blur(6px)",
        }}
      >
        <span style={{ fontWeight: 800, color: C.fg, letterSpacing: "0.03em" }}>
          <span style={{ color: C.accent }}>⚔</span> Immortals
        </span>
        <span style={{ color: C.dim }}>Microsoft demo-day · ~5 min pitch</span>
        <span>
          {idx + 1} / {N} &nbsp;·&nbsp; {mm}:{ss}
        </span>
      </div>
    </div>
  );
};
