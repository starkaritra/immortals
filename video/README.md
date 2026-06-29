# Immortals Pitch — Remotion Video

A self-contained [Remotion](https://www.remotion.dev) project that renders the
Immortals demo-day pitch as a narrated **1920×1080 / 30 fps MP4** (~4.5 min).

All 8 deck slides are **natively rebuilt as React scenes** (not screen-captured), so
every animation is frame-perfect: count-up stats, the line-by-line event-log terminal
with a blinking cursor, the drifting node-graph backdrop, the ⚔ orb breathe, the spine
dot that advances per scene, frosted-glass panels, and the animated gradient accent.

Narration is generated with **Edge TTS** (`en-US-ChristopherNeural`, no API key) and
**each scene's length is locked to its own clip's real duration** — audio and visuals
never drift.

## Sources of truth (faithfully recreated, never modified)
- Visuals: `../presentation/immortals-pitch.html` (design tokens, all 8 slides + JS animations)
- Narration: `../presentation/immortals-pitch-script.md` (verbatim spoken paragraphs)

## Prerequisites
- Node ≥ 18 (built/verified on v24). Remotion bundles its own Chromium + ffmpeg.
- The repo venv with `edge-tts` installed, at `../.venv/Scripts/python.exe`
  (only needed to **regenerate** audio; the rendered `public/audio/*.mp3` are committed-ready).
- `npm install` once in this folder.

## Regenerate the narration (Edge TTS)
The 8 section texts live in `src/sections.js` (the script's paragraphs; the final
script block is split into Vision + Close so each of the 8 slides gets its own clip).

```powershell
npm run gen-audio    # node scripts/gen-audio.mjs  -> public/audio/sNN.mp3 + sNN.vtt
npm run timings      # node scripts/gen-timings.mjs -> src/timings.json (real durations + captions)
```

`gen-timings.mjs` reads each clip's real end timestamp from its subtitle file and writes
`src/timings.json` (per-scene `durationFrames` at 30 fps, total duration, and caption cues).
**Re-run both after editing any section text.**

## Preview (Remotion Studio)
```powershell
npm run studio       # opens the interactive preview at http://localhost:3000
```

## Render the MP4
```powershell
npm run render       # remotion render ImmortalsPitch out/immortals-pitch.mp4
```

Render a single still for spot-checking a scene:
```powershell
npx remotion still ImmortalsPitch out/still.png --frame=2276
```

To render **without** the lower-third captions:
```powershell
npx remotion render ImmortalsPitch out/no-captions.mp4 --props="{\"showCaptions\":false}"
```

## Layout
```
video/
├─ src/
│  ├─ index.ts            # registerRoot
│  ├─ Root.tsx            # <Composition id="ImmortalsPitch">
│  ├─ Composition.tsx     # <Series> of 8 scenes + persistent <Chrome> overlay
│  ├─ sections.js         # the 8 narration texts (shared with the audio generator)
│  ├─ timings.json        # GENERATED: real per-scene durations + caption cues
│  ├─ theme.ts            # brand tokens + vh()/vw() px helpers (1080/1920 base)
│  ├─ components/         # Backdrop, Chrome, icons, primitives
│  └─ scenes/             # Scene1Problem … Scene8Close
├─ scripts/
│  ├─ gen-audio.mjs       # Edge TTS -> public/audio/*.mp3 + *.vtt
│  └─ gen-timings.mjs     # subtitle end-times -> src/timings.json
├─ public/audio/          # GENERATED narration clips
└─ out/                   # rendered stills + immortals-pitch.mp4
```

## Notes & judgment calls
- **vh/vw → px.** The deck is authored in viewport units; at a fixed 1080p,
  `1vh = 10.8px` and `1vw = 19.2px` (`theme.ts` helpers), reproducing the deck's sizing.
- **Vision/Close split.** The script's last block covers deck slides 7 and 8; it is split
  at *"…never watching your life."* so each slide has its own clip and TTS-locked length.
- **Scene timing.** `durationFrames = round((clip_seconds + 0.6s tail) × 30)`. The 0.6 s
  tail is a visual hold so scenes don't cut on the last syllable.
- **Event-log terminal.** Reveals line-by-line at a 16-frame cadence starting ~1.3 s in,
  then holds complete with a 1 s blinking cursor (deck cadence was 340 ms).
- **Backdrop determinism.** The node-graph is seeded (mulberry32) and computed purely from
  the frame number, so it renders identically across Remotion's parallel workers.
- **Captions** are lower-thirds built from the TTS subtitle cues, synced per scene; toggle
  off with `--props="{\"showCaptions\":false}"`.

## Last verified render
- Composition `ImmortalsPitch`, 1920×1080 @ 30 fps, **8066 frames ≈ 268.9 s (~4:29)**.
- Output: H.264 video + AAC audio (48 kHz), ~22.6 MB.
