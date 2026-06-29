import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { C, vh } from "../theme";
import {
  Kicker,
  Dek,
  SlideShell,
  CenterBand,
  Flow,
  FStage,
  FConn,
  IcoCircle,
  Tag,
  Reveal,
} from "../components/primitives";

const Mut: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span style={{ color: C.muted }}>{children}</span>
);

export const Scene4HowItWorks: React.FC = () => (
  <AbsoluteFill>
    <Audio src={staticFile("audio/s04.mp3")} />
    <SlideShell>
      <Kicker label="How it works" num="04" />
      <h1
        style={{
          fontSize: vh(5.1),
          lineHeight: 1.08,
          margin: `0 0 ${vh(1.4)}px`,
          fontWeight: 800,
          letterSpacing: "-.01em",
          maxWidth: "38ch",
        }}
      >
        Plan → orchestrate → verify,
        <br />
        <span style={{ color: C.accent }}>deterministically.</span>
      </h1>
      <Dek>
        Determinism where it counts: the agents stay creative; the coordination is auditable code.
      </Dek>
      <CenterBand>
        <Flow>
          <Reveal delay={14} style={{ flex: 1, display: "flex" }}>
            <FStage
              icon={<IcoCircle variant="blue" icon="dag" />}
              title="Typed plan"
              desc={
                <>
                  Alex Ferguson <Mut>(the manager)</Mut> turns your goal into a <b>DAG</b> — a
                  flowchart of tasks with the order built in.
                </>
              }
              tags={<Tag>plan/v1</Tag>}
            />
          </Reveal>
          <Reveal delay={22}>
            <FConn label="plan" />
          </Reveal>
          <Reveal delay={28} style={{ flex: 1, display: "flex" }}>
            <FStage
              icon={<IcoCircle variant="blue" icon="gear" />}
              title="Deterministic orchestrator"
              desc={
                <>
                  Runs the plan in order, routes each step, and checks every hand-off against a{" "}
                  <b>contract</b>.
                </>
              }
              tags={
                <>
                  <Tag>topo-order</Tag>
                  <Tag>seam contracts</Tag>
                  <Tag ok>guardrails</Tag>
                  <Tag ok>approval gates</Tag>
                </>
              }
            />
          </Reveal>
          <Reveal delay={36}>
            <FConn label="invoke" />
          </Reveal>
          <Reveal delay={42} style={{ flex: 1, display: "flex" }}>
            <FStage
              icon={<IcoCircle variant="blue" icon="chip" />}
              title="AgentRunner"
              desc={
                <>
                  Runs each specialist as a real <b>headless agent</b> — swappable backend.
                </>
              }
              tags={<Tag>copilot</Tag>}
            />
          </Reveal>
          <Reveal delay={50}>
            <FConn label="events" />
          </Reveal>
          <Reveal delay={56} style={{ flex: 1, display: "flex" }}>
            <FStage
              icon={<IcoCircle variant="green" icon="database" />}
              title="Event-sourced memory"
              desc={
                <>
                  Every move appended to a <b>log</b> in SQLite — the whole run replays exactly.
                </>
              }
              tags={
                <>
                  <Tag ok>audit</Tag>
                  <Tag ok>replay</Tag>
                  <Tag>recall graph</Tag>
                </>
              }
            />
          </Reveal>
        </Flow>
      </CenterBand>
    </SlideShell>
  </AbsoluteFill>
);
