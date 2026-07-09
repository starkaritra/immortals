---
name: resume-optimizer
description: "Use when a user shares a resume (file/path/text) together with a target job posting link and wants the resume tailored, optimized, aligned, or ATS-tuned for that job. Also triggers on: optimize my resume for this JD, tailor my CV to this role, make my resume match this posting, align my resume to this job, and on requests for similar/related job openings to apply to. Do NOT use for cover letters, LinkedIn profile rewrites, or generic resume-from-scratch requests unless a target job link is also provided."
argument-hint: "Paste a job posting URL and point me to your resume file (e.g. main.tex)"
---

# Resume Optimizer Skill

Tailor an existing resume to a specific target job description (JD), then surface similar, recent, reliable openings the user could also apply to. The skill keeps **employment and identity facts truthful** (employers, titles, dates, education, identity, real publications/metrics) while treating **projects and skills as flexible** — re-framing or replacing them, along with the summary and section ordering, to align with the JD.

The deliverable is a **tailored copy** of the resume (original left untouched) plus a concise change summary. Chat output stays minimal.

---

## Core principles (read first)

1. **Truthful on employment & identity; flexible on projects/skills.** Never invent or alter employers, titles, dates, education, identity, or real publications/metrics. **Projects and skills are flexible** and may be replaced/regenerated to align with the JD (kept plausible for the candidate's level). If the JD needs employment-level experience the resume lacks, surface it as a *gap* — don't fake a job.
2. **Respect the immutable set.** See "Immutable vs mutable" below. Anything fact-based about the person's identity and history is off-limits to change.
3. **ATS-aware, human-readable.** Mirror the JD's terminology (exact keywords/skills) so applicant-tracking systems match, while keeping prose natural for a human reviewer. Prefer the JD's spelling of a term (e.g. "Large Language Models (LLMs)" if the JD writes it that way).
4. **Preserve format & build-ability.** Keep the resume's existing format (LaTeX/Markdown/docx/plain). For LaTeX, keep it compilable — escape special chars (`& % $ # _ { }`), don't break macros/environments.
5. **Preserve the original.** Write a new file; never overwrite the source. Provide a clear, auditable change summary so the user can accept/reject edits.

---

## Immutable vs mutable

**Immutable — never alter, reword for meaning, or fabricate (only mechanical fixes like typos allowed, and only if obviously a typo):**
- Name, contact details, age/DOB, location, work-authorization, links (email/LinkedIn/GitHub).
- Employers/companies, job titles, employment dates, locations.
- Education: institutions, degrees, fields, GPAs, dates, listed coursework.
- Publications/patents that exist, their status, and authorship.
- Any concrete metric/number the user actually achieved, and the factual claims of past bullets (you may re-word *how* a real accomplishment is phrased and emphasized, but not change *what* was done or the numbers).
- Certifications, awards, honors.

> Do **not** invent or alter employment facts (employers, titles, dates) or change metrics tied to *real experience/publications*. Projects and skills are flexible (see below) and may be replaced with role-aligned ones.

**Fully flexible — may be replaced/regenerated wholesale to fit the JD:**
- **Projects:** treat as illustrative, not a historical ledger. You may **swap, replace, or generate new projects** that are aligned to the target role — picking technologies, methods, and outcomes that match the JD's domain and seniority. Prefer building on the user's real/adjacent work when available, but role-aligned projects may be substituted to maximize fit.
- **Skills:** add, drop, re-order, and rename freely to match the JD's stack and keywords (skills are flexible, not locked to what's already listed).
- Plausibility guard: keep generated projects/skills realistic and **consistent with the candidate's level and field** (don't claim 10 years of a 2-year-old tool, or skills that contradict the experience timeline). Briefly flag any newly generated project in the change summary so the user can confirm/own it.

**Mutable — optimize freely to fit the JD (without inventing employment facts):**
- Professional summary / objective (rewrite to mirror the JD's role, domain, and seniority).
- Section ordering and which optional sections appear.
- Keyword phrasing to align with the JD (e.g. "RLHF" ↔ "Reinforcement Learning from Human Feedback").
- Wording/ordering of experience bullets (verbs, emphasis, terminology) — but the underlying employer, title, dates, and what was actually done there stay true (those are immutable).

When in doubt whether something is an immutable employment/identity fact vs flexible framing, treat it as immutable and ask. Projects and skills are assumed flexible by default.

---

## Step 0 — Gather inputs

You need two things: the **resume** and the **target job link**.

- **Resume:** accept a file path, an attachment, or pasted text. If not given, look in the current working directory for likely resume files (`*.tex`, `*resume*`, `*cv*`, `*.md`, `*.docx`, `*.pdf`) and confirm which one. Detect format from extension/content.
  - `.tex` → parse LaTeX, preserve macros/sections.
  - `.md` / `.txt` → parse plain structure.
  - `.docx` → read text (e.g. via `python-docx` if available); if you can only extract text, produce the tailored copy as Markdown/text and say so.
  - `.pdf` → extract text (e.g. `pdftotext`/`pypdf` if available). PDFs are read-only sources; emit the tailored copy in a text/Markdown/LaTeX form and tell the user the original PDF can't be edited directly.
- **Target job link:** a URL to the posting. If missing, ask for it (this skill requires a JD to optimize against).

If either input is missing and cannot be inferred, ask for it before proceeding.

---

## Step 1 — Fetch & parse the JD

`web_fetch` the job URL. If it fails (login wall, JS-only, 404, captcha, tiny stub):
1. Retry with `raw: true`.
2. Try a cached/alternate view or the company careers permalink if derivable.
3. `web_search` the role + company to recover the description from an aggregator (LinkedIn/Indeed/Greenhouse/Lever/Workday mirror).
4. If still unrecoverable, ask the user to paste the JD text.

Extract and record:
- **Role title & seniority** (intern / new-grad / junior / mid / senior / staff / lead) and **years-of-experience** band.
- **Company** and team/org if stated.
- **Must-have skills/tools/technologies** (hard requirements).
- **Nice-to-have / preferred** qualifications.
- **Key responsibilities** and the domain/problem space.
- **Notable keywords** (exact phrasings) for ATS alignment.
- **Location / work model** and any hard constraints (clearance, degree, certifications).

---

## Step 2 — Parse the resume & build the alignment map

Parse the resume into sections. Classify each piece as immutable or mutable (see table above).

Build an **alignment map**:
- For each JD must-have/nice-to-have → mark **present / partial / absent** in the resume (cite where).
- Identify mutable content to re-frame, and **projects/skills to replace or add** so absent JD items become covered (projects/skills are flexible).
- Identify true **gaps** — JD requirements at the *employment/experience* level the resume can't honestly support. These are *reported*, not faked into the work history.
- Note seniority/scope mismatches (e.g., JD wants leadership the resume doesn't show).

---

## Step 3 — Optimize the mutable content

Rewrite only mutable sections, guided by the alignment map:

- **Summary/objective:** 2–4 lines re-centered on the JD's role, domain, and seniority, using the JD's vocabulary, reflecting only real experience.
- **Skills:** add, drop, re-order, group, and rename freely to match the JD's stack and exact keywords. Skills are flexible — not locked to what's already listed.
- **Projects / project bullets:** treat as flexible. Re-frame existing projects *or* **replace/generate role-aligned projects** that showcase the JD's domain, tools, methods, and impact. Lead with strong action verbs; keep outcomes realistic for the candidate's level. Order so the most JD-relevant come first.
- **Section ordering:** surface the sections that matter most for this JD.

Hard guardrails while editing:
- Do not touch the immutable employment/identity set (employers, titles, dates, education, identity, real publications/metrics) beyond mechanical typo fixes.
- Generated projects/skills must be plausible and consistent with the candidate's level/timeline; flag newly generated projects in the change summary so the user can confirm/own them.
- Keep length and density appropriate (typically 1 page for <~8 yrs experience unless the original was longer).
- Keep the file compilable/valid in its original format.

---

## Step 4 — Write the tailored copy + change summary

- Write a **new file** next to the original: `<basename>_<company-or-role-slug>.<ext>` (e.g. `main_microsoft-as.tex`). Never overwrite the source.
- Keep the same format and preamble/macros as the original.
- Produce a **change summary** capturing: what changed and why (mapped to JD requirements), keywords added for ATS, and a clear **gaps list** (JD asks → not evidenced in resume) for the user to address truthfully.
- If the original is LaTeX and a compiler is available (`tectonic`/`pdflatex`/`latexmk`/`xelatex`), offer to build the PDF; if none is installed, say so and stop at the `.tex`.

---

## Step 5 — Suggest similar jobs (verify-or-omit; eligibility-filtered)

Goal: relevant, **recent**, **verified**, eligibility-matched openings at **different companies**, within the same band as the target link.

1. **Derive the search profile** from the JD: role family, seniority/experience band, **degree eligibility** (BS / MS / PhD), domain/skills, and location/work-model (respect the user's constraints; ask if location preference is unclear). Read the candidate's actual degree from the resume (immutable) — this drives the eligibility filter.
2. **Prefer static, fetchable sources over JS career portals.** JS-rendered career sites (Google/Apple/Meta search pages, Workday/Greenhouse search UIs) usually return only boilerplate to `web_fetch`, so you cannot verify a specific posting from them. Instead, source exact apply URLs from:
   - **Daily-updated static job trackers** with raw markdown/CSV (e.g. GitHub repos like `speedyapply/2026-AI-College-Jobs`, `SimplifyJobs/Summer*-Internships`) — fetch the **raw** file; these list exact ATS apply links plus a freshness/age field.
   - **Direct ATS deep-links** that render server-side (e.g. `*.myworkdayjobs.com/.../job/...`, `job-boards.greenhouse.io/.../jobs/<id>`, `jobs.lever.co/...`, `jobs.ashbyhq.com/...`, `amazon.jobs/jobs/<id>`, `metacareers.com/jobs/<id>`, `apply.careers.microsoft.com/careers/job/<id>`, official program pages).
3. **Verify-or-omit (hard rule).** Every link you present must be **`web_fetch`-confirmed** in this run to resolve to a real, current posting (not 404/expired/login-wall/boilerplate-only). **Never present a link you have not fetched and confirmed.** If a posting is real but its application page is JS-only, present the verified human-readable posting/program page you *did* fetch, and say how to apply (e.g. "apply via team-lead email", "search this req ID on the careers portal") — do not fabricate a deep apply URL.
4. **Eligibility filter with MS/PhD flexibility.** Match each posting to the candidate's degree:
   - A posting open to a range that **includes** the candidate (e.g. "BS/MS", "MS or PhD") → **eligible** — present it.
   - A posting one level **above** the candidate (e.g. PhD-only when candidate is MS) → **likely ineligible** — either omit, or list separately under a clearly-labeled "PhD-only (likely ineligible)" group; never present it as a fit.
   - A posting **at or below** the candidate's level → eligible.
   - When eligibility is genuinely ambiguous from the posting, say so rather than asserting a fit.
5. **Confidence gate — present only high-confidence recommendations.** Only surface a job if it is (a) fetch-verified live, (b) eligibility-matched (incl. MS/PhD flexibility), (c) genuinely relevant to the JD's domain/band, and (d) recent (prefer postings aged within the tracker's freshness window, ~≤120 days). If a candidate fails any of these, drop it. **If nothing clears the bar, present no list** and say so honestly (offer to widen scope or have the user paste a board) rather than padding with weak or unverifiable entries.
6. For each presented entry include: company, role title, **eligibility** (e.g. BS/MS — eligible), why it fits (1 line), location/work-model, posting age if known, and the **verified** link. Note explicitly that you fetched/confirmed each link in this run.

---

## Step 6 — Chat output (keep it minimal)

A successful run prints, in chat:
1. One-line status while fetching the JD.
2. **Tailored resume:** the new file path + a compact change summary (bulleted: key re-framings, ATS keywords added, sections re-ordered).
3. **Gaps to address:** short, honest list of JD requirements not evidenced — framed as suggestions, never inserted into the resume.
4. **Similar jobs:** only high-confidence, fetch-verified, eligibility-matched postings (mark eligibility per entry). If some real-but-relevant roles are a degree-level above the candidate, list them under a separate **"likely ineligible (PhD-only)"** note. If nothing clears the confidence gate, say so — present no list rather than padding.
5. Offer next actions (build PDF, tailor for another link, fix a gap).

Do not dump the full rewritten resume into chat unless asked — it lives in the file. Keep chat scannable.

---

## Guardrails recap

- Never invent or alter employment/identity facts (employers, titles, dates, education, identity, real publications/metrics).
- Projects and skills are flexible — replace/regenerate them to fit the JD, keeping them plausible for the candidate's level and flagging new projects in the summary.
- Surface true employment-level gaps instead of faking a job.
- Preserve the original file; write a tailored copy.
- Mirror JD keywords for ATS without lying.
- **Verify-or-omit:** present only job links you `web_fetch`-confirmed live in this run; never invent, infer, or relay unverified URLs. Prefer static job trackers / server-rendered ATS deep-links over JS career portals.
- **Eligibility-filter with MS/PhD flexibility:** present a role only if the candidate's degree falls within its eligibility range; flag degree-above roles as likely ineligible, never as a fit.
- **Confidence gate:** if no posting is verified + eligible + relevant + recent, present no job list and say so honestly.
- Ask when the immutable/mutable boundary is unclear, when the resume or JD can't be obtained, or when location/seniority/eligibility constraints are ambiguous.
