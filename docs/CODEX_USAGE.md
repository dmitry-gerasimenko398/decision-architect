# Codex and GPT-5.6 usage

## During development

Codex was used to create the repository structure, implement the standard-library Python engines, write executable validation and JSON schemas, create tests, audit the code, build the reusable Skill, generate local HTML reports, and prepare release documentation.

Independent Codex review passes checked mathematics, privacy, security, beginner usability, documentation accuracy, contest presentation, release reproducibility, and truthful feature claims. Two live human Skill acceptance tests were also completed.

## During product use

GPT-5.6/Codex is responsible for conversational work:

- Interpret the user’s natural-language decision.
- Select one of the two supported mathematical structures.
- Ask adaptive questions in small batches.
- Preserve user terminology while creating safe internal IDs.
- Separate facts, estimates, preferences, constraints, assumptions, and settings.
- Notice possible double counting or contradictions.
- Assemble and present a proposed model.
- Require exact confirmation before calculation.
- Invoke deterministic validation, analysis, and reporting commands.
- Explain only stored results and keep the recommendation conditional.

## Deterministic boundary

Python is responsible for authoritative numerical calculations. The language model does not manually reproduce Monte Carlo simulation, sensitivity thresholds, or dynamic programming values, and it does not guarantee arithmetic accuracy.

The report generator reads validated saved result JSON. It does not call either engine or independently choose a recommendation.

## Where conversational care remains necessary

Human and language-model judgment can still affect:

- Whether criteria are meaningful and non-overlapping.
- How vague estimates are translated into numerical ranges.
- Whether anchors represent meaningful worst and best outcomes.
- Whether a condition is mandatory or compensable.
- Whether an approximation fits the real decision structure.
- Which private context is unnecessary and should not be stored.

The confirmation review exists so the user—not the language model—approves the final representation before calculation.
