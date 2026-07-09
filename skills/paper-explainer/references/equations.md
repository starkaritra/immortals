# Equation Style Reference

**All equations must be rendered in LaTeX** using KaTeX loaded from cdnjs. Never use Unicode/ASCII math or plain text for equations. KaTeX renders synchronously — equations appear immediately with no loading delay.

---

## KaTeX Loading Rules

- Load the KaTeX CSS and JS **once only** — in the very first equation widget of the response.
- Every subsequent equation widget omits the `<link>` and `<script src=...>` tags — KaTeX is already available globally.
- Always call `katex.render(tex, element, { displayMode: true/false, throwOnError: false })` — never use raw `$$...$$` or `\[...\]` delimiters, as those require an auto-render pass that may not fire.
- Every `id` attribute must be unique across the whole response — use `eq-attn`, `eq-softmax`, `eq-loss` etc., never reuse `eq-main`.

---

## First Equation Widget Template (includes KaTeX load)

```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css">
<div style="padding:1rem 0">
  <p style="font-size:13px;font-weight:500;color:var(--color-text-primary);margin:0 0 0.5rem">Equation: [Name]</p>

  <div id="eq-main" style="padding:0.75rem;background:var(--color-background-secondary);border-radius:var(--border-radius-md);text-align:center"></div>

  <table style="width:100%;border-collapse:collapse;margin:0.75rem 0;font-size:13px">
    <tr style="border-bottom:0.5px solid var(--color-border-tertiary)">
      <th style="text-align:left;padding:4px 8px;color:var(--color-text-secondary)">Symbol</th>
      <th style="text-align:left;padding:4px 8px;color:var(--color-text-secondary)">Meaning</th>
    </tr>
    <tr>
      <td style="padding:4px 8px"><span id="sym1"></span></td>
      <td style="padding:4px 8px;color:var(--color-text-secondary)">plain English meaning</td>
    </tr>
  </table>

  <div style="font-size:13px;color:var(--color-text-secondary);margin:0.5rem 0">
    <strong style="color:var(--color-text-primary)">Derivation:</strong><br>
    <span style="display:block;margin:4px 0">Step 1: <span id="step1"></span> — [reason]</span>
    <span style="display:block;margin:4px 0">Step 2: <span id="step2"></span> — [reason]</span>
  </div>

  <p style="font-size:13px;border-left:2px solid var(--color-border-secondary);padding-left:0.75rem;margin:0.75rem 0 0">
    <strong>In plain English:</strong> [one sentence]
  </p>
  <p style="font-size:13px;color:var(--color-text-secondary);margin:0.5rem 0 0">
    Intuition: [analogy or concrete numerical example]
  </p>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>
<script>
var opt = { throwOnError: false };
katex.render('YOUR_DISPLAY_LATEX', document.getElementById('eq-main'), { displayMode: true, ...opt });
katex.render('symbol_latex', document.getElementById('sym1'), opt);
katex.render('step1_latex', document.getElementById('step1'), opt);
katex.render('step2_latex', document.getElementById('step2'), opt);
</script>
```

---

## Subsequent Equation Widgets (KaTeX already loaded — no script/link tags)

```html
<div style="padding:1rem 0">
  <p style="font-size:13px;font-weight:500;color:var(--color-text-primary);margin:0 0 0.5rem">Equation: [Name]</p>
  <div id="eq-N" style="padding:0.75rem;background:var(--color-background-secondary);border-radius:var(--border-radius-md);text-align:center"></div>
  <p style="font-size:13px;border-left:2px solid var(--color-border-secondary);padding-left:0.75rem;margin:0.75rem 0 0">
    <strong>In plain English:</strong> [one sentence]
  </p>
</div>
<script>
katex.render('YOUR_LATEX', document.getElementById('eq-N'), { displayMode: true, throwOnError: false });
</script>
```

---

## Pseudocode

Pseudocode goes in a plain fenced code block immediately after the equation widget — not inside a Visualizer widget:

```
Pseudocode: [Equation Name]
  input: ...
  output: ...
  1. ...
  2. ...
```

---

## Depth Rules

- **Simple equations** (e.g. a scaling factor): LaTeX widget with symbol table + plain English only. Skip derivation and pseudocode.
- **Medium equations** (e.g. softmax, attention): full widget — symbols + derivation + plain English + intuition + pseudocode.
- **Complex derivations** (e.g. IO complexity proof, gradient expressions): full widget, walk every algebraic step, explain what cancels and why. If the paper proves it in an appendix, summarize the proof strategy and key steps in a Deep Dive callout with LaTeX for each step.
- **Never skip an equation because it's hard** — that's exactly where the skill adds value.

---

## Deep Dive Callout Format

```
> 🔬 **Deep Dive: [topic]**
> [Extended derivation or proof sketch in prose]
> [Equations inside Deep Dives use KaTeX — use the subsequent equation template (no script/link tags if KaTeX was already loaded)]
> [Reader can skip this and still follow the main narrative]
```

Use Deep Dive blocks for: formal proofs, complexity lower-bound arguments, backward pass derivations, CUDA implementation details, and any math that goes beyond what's needed to understand the result intuitively.
