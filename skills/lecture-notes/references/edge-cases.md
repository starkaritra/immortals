# Edge Cases (lecture-notes)

## No captions available
`fetch_transcript.py get` exits with "no captions available". Options, in order:
1. Try the auto-subs of a re-upload or the official course channel version of the same talk.
2. If the user can supply a transcript/PDF of slides, use that.
3. As a last resort, offer to build notes from slide text / the description / your own domain
   knowledge — but **tell the user** the notes aren't grounded in the spoken content.
Never silently fabricate lecture-specific claims.

## Non-English lecture
Pull the original captions; if the user wants English notes, translate faithfully and keep
key technical terms in both languages in the glossary. Flag machine-translation uncertainty.

## Very long lecture (2h+ / dense)
Split into a **multi-part note set** (Part 1/2/…), each a normal note with its own TOC, joined
by prev/next nav — rather than one giant file. Or, if the user prefers, one note with a
tighter section granularity. Confirm which.

## Playlist / course
1. `fetch_transcript.py list <url>` to enumerate.
2. **Confirm scope with the user** before bulk work: a foundational batch of ~5, the whole
   thing, a specific version/module, or a hand-picked set. Never silently generate 50 notes.
3. Order the batch pedagogically (overview → mechanics → applications), not just by index.
4. Build one **`index.html` hub** linking all notes in learning order (see the template's
   nav + a card list). Wire prev/next across notes.
5. For big playlists, generate in **batches**; validate each batch; report and pause for the
   next.

## Auto-generated captions are messy
Expect transcription errors (names, symbols, technical terms garbled). **Rely on correct
domain knowledge**; use the transcript for the lecture's *emphasis, order, examples, and
anecdotes*, not as literal ground truth for spelling/facts. Cross-check named papers/people.

## Whiteboard / heavy-math lecture with little on-screen text
The audio transcript will describe equations verbally ("x squared over two"). Reconstruct the
actual LaTeX from context and render it properly; add the worked example the lecturer did on
the board.

## Slide-driven talk
Captions may under-describe visuals. Recreate the key figures as Mermaid/SVG from the verbal
description; don't screenshot copyrighted slides.

## Members-only / paywalled / age-restricted video
`yt-dlp` may fail. Tell the user; ask for an accessible URL or a transcript. Do not attempt to
bypass access controls.

## Panel / multi-speaker / fireside chat
Structure by **theme**, not by speaker turn. Attribute distinct claims where it matters
(especially competing opinions), and keep the epistemic-status signaling tight.

## Very short clip (<10 min)
Skip the multi-section scaffold; produce a single tight note (hook → one worked example →
recap). Don't pad.

## Rendering environment lacks a browser (validation)
If no system Edge/Chrome is found and puppeteer's bundled Chromium can't download, skip the
headless validation but **manually audit** every Mermaid block for a closed `</div>` and
quoted labels, and every `$$`/`\(` pair. State that automated validation was skipped.
