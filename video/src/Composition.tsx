import React from "react";
import { AbsoluteFill, Series } from "remotion";
import { DECK_BG } from "./theme";
import timings from "./timings.json";
import { Chrome } from "./components/Chrome";
import { Scene1Problem } from "./scenes/Scene1Problem";
import { Scene2Aggravate } from "./scenes/Scene2Aggravate";
import { Scene3Solution } from "./scenes/Scene3Solution";
import { Scene4HowItWorks } from "./scenes/Scene4HowItWorks";
import { Scene5Demo } from "./scenes/Scene5Demo";
import { Scene6Results } from "./scenes/Scene6Results";
import { Scene7Vision } from "./scenes/Scene7Vision";
import { Scene8Close } from "./scenes/Scene8Close";

const SCENE_BY_ID: Record<string, React.FC> = {
  s01: Scene1Problem,
  s02: Scene2Aggravate,
  s03: Scene3Solution,
  s04: Scene4HowItWorks,
  s05: Scene5Demo,
  s06: Scene6Results,
  s07: Scene7Vision,
  s08: Scene8Close,
};

export type PitchProps = { showCaptions: boolean };

export const ImmortalsPitch: React.FC<PitchProps> = ({ showCaptions }) => (
  <AbsoluteFill style={{ background: DECK_BG }}>
    <Series>
      {timings.scenes.map((s) => {
        const Scene = SCENE_BY_ID[s.id];
        return (
          <Series.Sequence key={s.id} durationInFrames={s.durationFrames}>
            <Scene />
          </Series.Sequence>
        );
      })}
    </Series>
    <Chrome scenes={timings.scenes} showCaptions={showCaptions} />
  </AbsoluteFill>
);
