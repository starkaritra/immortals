// Reproducibly (re)generates the Edge-TTS narration for all 8 sections.
//
//   node scripts/gen-audio.mjs
//
// For each section it writes public/audio/<id>.mp3 and <id>.vtt using the
// repo venv's edge-tts (no API key required). Voice is en-US-ChristopherNeural.
//
// Re-run any time the section texts in src/sections.js change.

import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { existsSync, mkdirSync } from "node:fs";
import { sections, VOICE } from "../src/sections.js";

// Speech rate passed to edge-tts (e.g. "+50%" = 1.5x faster, "-10%" = slower).
// Override per-run with the TTS_RATE env var. Default tuned to land the full video ~3:00.
const RATE = process.env.TTS_RATE || "+50%";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const repoRoot = join(root, "..");
const audioDir = join(root, "public", "audio");

// Repo venv python that has edge-tts installed.
const PY = join(repoRoot, ".venv", "Scripts", "python.exe");

if (!existsSync(PY)) {
  console.error(`[gen-audio] venv python not found at ${PY}`);
  process.exit(1);
}
mkdirSync(audioDir, { recursive: true });

console.log(`[gen-audio] voice=${VOICE}  rate=${RATE}  ->  ${audioDir}`);
for (const s of sections) {
  const mp3 = join(audioDir, `${s.id}.mp3`);
  const vtt = join(audioDir, `${s.id}.vtt`);
  process.stdout.write(`  ${s.id} (${s.title}) ... `);
  // Args passed as an array -> no shell escaping issues with em-dashes/quotes.
  execFileSync(
    PY,
    [
      "-m", "edge_tts",
      "--voice", VOICE,
      "--rate", RATE,
      "--text", s.text,
      "--write-media", mp3,
      "--write-subtitles", vtt,
    ],
    { stdio: ["ignore", "ignore", "inherit"] }
  );
  console.log("done");
}
console.log("[gen-audio] complete. Now run: node scripts/gen-timings.mjs");
