import { Config } from "@remotion/cli/config";

// 1080p, high-quality H.264. Chromium + ffmpeg are bundled by Remotion.
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setConcurrency(null); // let Remotion pick based on CPU
Config.setChromiumOpenGlRenderer("angle");
