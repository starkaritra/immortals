import React from "react";
import { Composition } from "remotion";
import { ImmortalsPitch } from "./Composition";
import { FPS, WIDTH, HEIGHT } from "./theme";
import timings from "./timings.json";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ImmortalsPitch"
        component={ImmortalsPitch}
        durationInFrames={timings.totalFrames}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={{ showCaptions: true }}
      />
    </>
  );
};
