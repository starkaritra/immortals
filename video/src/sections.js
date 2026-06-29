// The 8 narration sections, taken verbatim from
// presentation/immortals-pitch-script.md.
//
// Judgment call (documented in README): the script's final block
// "[04:30 – 05:00] VISION — the close" covers BOTH slide 7 (Vision) and
// slide 8 (Close). It is split here at "...never watching your life." so
// each of the deck's 8 slides gets its own narration clip and its own
// TTS-locked duration.
//
// This file is plain JS so it can be imported by both the Node audio
// generator (scripts/gen-audio.mjs) and the Remotion bundle (src/*).

export const VOICE = "en-US-ChristopherNeural";

export const sections = [
  {
    id: "s01",
    slide: 1,
    title: "Problem",
    text:
      "You have more good ideas than you will ever ship. A research dive you keep postponing. " +
      "A tool you would build if you had a free week. A paper, a prototype, a plan — all stuck " +
      "in the same place: your head. Not because the idea is weak — but because doing it means " +
      "becoming a researcher, a critic, an engineer, and a project manager, all at once. " +
      "So the idea waits. And most of them quietly die there.",
  },
  {
    id: "s02",
    slide: 2,
    title: "Aggravate",
    text:
      "And the AI tools meant to help? They hand you a wall of text and walk away. You are still " +
      "the one who has to break the work down, check it, fix it, and stitch it together. One " +
      "chatbot. One generalist. No plan, and no memory of what it did an hour ago. You did not " +
      "get a team — you got another tab to manage.",
  },
  {
    id: "s03",
    slide: 3,
    title: "Solution",
    text:
      "Immortals is different. It is an enterprise team you delegate to. You hand one manager " +
      "your goal, in plain English — and it brings your ideas to life. The manager writes a " +
      "real plan, picks the right specialists — a researcher, a critic, a coder, an experimenter — " +
      "and runs them for you. You talk to one agent; a whole expert team does the work behind it. " +
      "You delegate the task. You get back a finished result.",
  },
  {
    id: "s04",
    slide: 4,
    title: "How it works",
    text:
      "Here is how, simply. The manager turns your goal into a typed plan — a DAG, a flowchart " +
      "of tasks with the right order built in. A deterministic orchestrator runs that plan: it " +
      "routes each step to the right specialist, and checks every hand-off against a contract — so " +
      "each output is valid input for the next. Guardrails cap time and cost, and risky steps " +
      "wait for your approval. Every move lands in an append-only event log — so the whole " +
      "run is auditable and replayable. The creative parts stay creative; " +
      "the coordination stays deterministic, auditable code.",
  },
  {
    id: "s05",
    slide: 5,
    title: "Demo",
    text:
      "Let's watch it work. This is the Immortals bubble. I type one sentence — build me a weekly " +
      "digest of new AI research. Instantly it assembles a team — you can see the plan as a small " +
      "flowchart: research, then critique, then build. Then it goes quiet and works. Silence is the " +
      "default — no firehose of pings. A live counter shows the routine decisions it is handling on " +
      "its own. It interrupts me exactly once — for a genuine judgment call — and notes that it held " +
      "back nine routine choices to ask this one. I answer, and it finishes: a verified report, " +
      "stamped with who did what. Now — a hard cut to the dashboard. Because this is not a mockup. " +
      "Here is a real run: the actual plan, the event timeline, the cost. Fully auditable.",
  },
  {
    id: "s06",
    slide: 6,
    title: "Results",
    text:
      "And that real run delivered. We gave Immortals a genuine build — a weekly research digest: " +
      "a Cloudflare backend plus a Chrome extension, end to end. Four steps, three specialists, real " +
      "agents. It passed all eight of our pre-registered success criteria. The code it shipped: " +
      "seventy-eight of seventy-eight tests passing, type-clean. But here is the moment that " +
      "matters. The critic agent — on its own — caught a critical flaw the first plan missed: " +
      "summarizing one item at a time would blow a hard platform limit and abort the whole digest. " +
      "The coder fixed it with batching. The team produced better architecture than the plan it was " +
      "handed. Honest caveat: the agents build and test headlessly — the final deploy is still a human " +
      "click. But that is not one yes-man chatbot. That is a real, critical team.",
  },
  {
    id: "s07",
    slide: 7,
    title: "Vision",
    text:
      "This is real today, at minutes-scale. The vision is bigger: a long-running agent you delegate " +
      "to for days — that survives restarts, learns which calls you want to make, and earns " +
      "more autonomy as it does. Always task-scoped; never watching your life.",
  },
  {
    id: "s08",
    slide: 8,
    title: "Close",
    text:
      "Microsoft's mission is to empower every person and organization to achieve more. Immortals " +
      "gives every one of us an expert team to delegate to — so your next idea doesn't wait in your " +
      "head. It ships.",
  },
];
