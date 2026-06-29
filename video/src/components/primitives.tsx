import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, vh, vw, FONT } from "../theme";
import { Icon, IconName } from "./icons";

// ---- easing ----
export const easeOut = (p: number) => 1 - Math.pow(1 - p, 3);

// Generic fade+rise entrance (deck: .slide fade 0.45s + translateY(14px)).
export const useEntrance = (delayF = 0, durF = 14) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [delayF, delayF + durF], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return { opacity: p, transform: `translateY(${(1 - p) * 14}px)` };
};

// The slide frame: padding 5vh 6.2vw 8vh, flex column (deck .slide).
export const SlideShell: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const ent = useEntrance(0, 14);
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        padding: `${vh(5)}px ${vw(6.2)}px ${vh(8)}px`,
        fontFamily: FONT,
        color: C.fg,
        ...ent,
      }}
    >
      {children}
    </div>
  );
};

// kicker: ⚔ <label> · NN
export const Kicker: React.FC<{ label: string; num?: string; center?: boolean }> = ({
  label,
  num,
  center,
}) => (
  <div
    style={{
      fontSize: vh(1.55),
      letterSpacing: "0.22em",
      textTransform: "uppercase",
      color: C.accent,
      fontWeight: 700,
      marginBottom: vh(1.6),
      display: "flex",
      alignItems: "center",
      gap: "0.7em",
      justifyContent: center ? "center" : undefined,
    }}
  >
    <span style={{ color: C.accent }}>⚔</span>
    <span>{label}</span>
    {num && <span style={{ color: C.dim, fontWeight: 600 }}>· {num}</span>}
  </div>
);

// dek: left gradient rule + thesis line
export const Dek: React.FC<{ children: React.ReactNode; maxCh?: number }> = ({
  children,
  maxCh = 68,
}) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: "0.7em",
      fontSize: vh(1.95),
      lineHeight: 1.4,
      fontWeight: 400,
      color: "rgba(233,236,242,.84)",
      maxWidth: `${maxCh}ch`,
      margin: `${vh(0.1)}px 0 ${vh(1.7)}px`,
    }}
  >
    <span
      style={{
        alignSelf: "stretch",
        width: 3,
        minHeight: "1.15em",
        borderRadius: 2,
        flex: "none",
        background: `linear-gradient(180deg,${C.accent},${C.accent2})`,
      }}
    />
    <span>{children}</span>
  </div>
);

// ---- shared diagram system (slides 4 · 5 · 7) ----
const ICO_VARIANT: Record<string, React.CSSProperties> = {
  blue: { background: C.accent, color: "#06101f" },
  green: { background: C.ok, color: "#04140e" },
  amber: { background: C.warn, color: "#1a1205" },
  indigo: {
    background: `linear-gradient(135deg,${C.accent2},#6f5fe0)`,
    color: "#0a0716",
  },
};

export const IcoCircle: React.FC<{
  variant: "blue" | "green" | "amber" | "indigo";
  icon?: IconName;
  text?: string;
  star?: boolean;
}> = ({ variant, icon, text, star }) => (
  <div
    style={{
      width: vh(5.4),
      height: vh(5.4),
      borderRadius: "50%",
      flex: "none",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontWeight: 800,
      fontSize: vh(2.4),
      boxShadow: star
        ? "0 0 0 4px rgba(139,124,255,.22),0 6px 18px rgba(0,0,0,.45)"
        : "0 6px 18px rgba(0,0,0,.4)",
      ...ICO_VARIANT[variant],
    }}
  >
    {icon ? <Icon name={icon} size={vh(2.7)} /> : text}
  </div>
);

export const Tag: React.FC<{ children: React.ReactNode; ok?: boolean }> = ({
  children,
  ok,
}) => (
  <span
    style={{
      background: ok ? "rgba(78,201,168,.10)" : C.chip,
      border: `1px solid ${ok ? "rgba(78,201,168,.4)" : C.line}`,
      borderRadius: 999,
      padding: `${vh(0.35)}px ${vw(0.8)}px`,
      fontSize: vh(1.4),
      color: ok ? C.ok : C.fg,
    }}
  >
    {children}
  </span>
);

// connector: optional label + line·chevron·line, top-aligned to the icon row
export const FConn: React.FC<{ label?: string }> = ({ label }) => (
  <div
    style={{
      flex: "none",
      alignSelf: "flex-start",
      height: vh(5.4),
      width: vw(5.2),
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: vh(0.4),
      color: C.accent,
    }}
  >
    {label && (
      <span
        style={{
          fontSize: vh(1.15),
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: C.dim,
        }}
      >
        {label}
      </span>
    )}
    <span style={{ display: "flex", alignItems: "center", width: "100%" }}>
      <i style={{ flex: 1, height: 2, background: "currentColor", opacity: 0.5 }} />
      <Icon name="chevron" size={vh(2)} strokeWidth={2.4} style={{ margin: "0 -3px" }} />
      <i style={{ flex: 1, height: 2, background: "currentColor", opacity: 0.5 }} />
    </span>
  </div>
);

// a flow stage column (icon + title + desc + optional phase label + tags)
export const FStage: React.FC<{
  icon?: React.ReactNode;
  phase?: string;
  phaseColor?: string;
  title: React.ReactNode;
  desc?: React.ReactNode;
  tags?: React.ReactNode;
  titleColor?: string;
}> = ({ icon, phase, phaseColor, title, desc, tags, titleColor }) => (
  <div
    style={{
      flex: 1,
      minWidth: 0,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      textAlign: "center",
      gap: vh(0.9),
      padding: `0 ${vw(0.55)}px`,
    }}
  >
    {icon}
    {phase && (
      <div
        style={{
          fontSize: vh(1.35),
          fontWeight: 700,
          letterSpacing: "0.05em",
          textTransform: "uppercase",
          color: phaseColor ?? C.accent,
        }}
      >
        {phase}
      </div>
    )}
    <div style={{ fontWeight: 700, fontSize: vh(2.0), lineHeight: 1.16, color: titleColor }}>
      {title}
    </div>
    {desc && (
      <div
        style={{
          fontSize: vh(1.5),
          color: C.muted,
          lineHeight: 1.36,
          maxWidth: "19ch",
        }}
      >
        {desc}
      </div>
    )}
    {tags && (
      <div
        style={{
          display: "flex",
          gap: vw(0.6),
          flexWrap: "wrap",
          justifyContent: "center",
          marginTop: vh(0.2),
        }}
      >
        {tags}
      </div>
    )}
  </div>
);

// staggered entrance wrapper
export const Reveal: React.FC<{
  delay?: number;
  dur?: number;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ delay = 0, dur = 12, style, children }) => {
  const ent = useEntrance(delay, dur);
  return <div style={{ ...ent, ...style }}>{children}</div>;
};

// the centered band that holds a flow (slides 4·5·7)
export const CenterBand: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      flex: 1,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: vh(1.9),
      width: "100%",
    }}
  >
    {children}
  </div>
);

export const Flow: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      display: "flex",
      alignItems: "flex-start",
      justifyContent: "center",
      width: "100%",
      maxWidth: vw(93),
    }}
  >
    {children}
  </div>
);
