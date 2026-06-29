// Reads the REAL spoken duration of each TTS clip from its .vtt subtitle file
// (the last cue's end timestamp) and writes src/timings.json. The Remotion
// composition uses these so every scene's length is locked to its own audio.
//
//   node scripts/gen-timings.mjs
//
// Run after gen-audio.mjs.

import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { sections } from "../src/sections.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const audioDir = join(root, "public", "audio");

const FPS = 30;
// Visual hold after the voice stops, so scenes don't cut on the last syllable.
const TAIL_PAD_SEC = 0.6;
// Lead-in silence is baked into the VTT (cues start a touch after 0); we keep it.

function vttEndSeconds(vttPath) {
  return parseCues(vttPath).reduce((mx, c) => Math.max(mx, c.endSec), 0);
}

// Parse SRT-style cues into {startSec, endSec, text}.
function parseCues(vttPath) {
  const txt = readFileSync(vttPath, "utf8").replace(/\r/g, "");
  const re =
    /(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*\n([^\n]*)/g;
  const cues = [];
  let m;
  const toSec = (h, mm, s, ms) =>
    Number(h) * 3600 + Number(mm) * 60 + Number(s) + Number(ms) / 1000;
  while ((m = re.exec(txt)) !== null) {
    cues.push({
      startSec: Number(toSec(m[1], m[2], m[3], m[4]).toFixed(3)),
      endSec: Number(toSec(m[5], m[6], m[7], m[8]).toFixed(3)),
      text: m[9].trim(),
    });
  }
  return cues;
}

const scenes = sections.map((s) => {
  const vtt = join(audioDir, `${s.id}.vtt`);
  if (!existsSync(vtt)) {
    throw new Error(`Missing ${vtt} — run gen-audio.mjs first.`);
  }
  const audioSec = vttEndSeconds(vtt);
  const durationFrames = Math.round((audioSec + TAIL_PAD_SEC) * FPS);
  return {
    id: s.id,
    slide: s.slide,
    title: s.title,
    audioSec: Number(audioSec.toFixed(3)),
    durationFrames,
    captions: parseCues(vtt),
  };
});

const totalFrames = scenes.reduce((a, s) => a + s.durationFrames, 0);
const out = {
  fps: FPS,
  width: 1920,
  height: 1080,
  tailPadSec: TAIL_PAD_SEC,
  totalFrames,
  totalSeconds: Number((totalFrames / FPS).toFixed(2)),
  scenes,
};

writeFileSync(join(root, "src", "timings.json"), JSON.stringify(out, null, 2));
console.log(`[gen-timings] wrote src/timings.json`);
for (const s of scenes) {
  console.log(
    `  ${s.id}  ${s.title.padEnd(12)}  audio ${s.audioSec.toFixed(1)}s  -> ${s.durationFrames}f`
  );
}
console.log(
  `[gen-timings] total ${out.totalSeconds}s (${totalFrames} frames @ ${FPS}fps)`
);
