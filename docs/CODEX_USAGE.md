# Codex and GPT-5.6 usage

## Supported repository-scoped workflow

Download the complete Decision Architect repository and open its root folder as the current Codex project. For this release, no separate or global Skill installation is required: Codex discovers the repository-scoped Skill at `.agents/skills/decision-analysis/`.

Downloading only the Skill folder is not the supported complete workflow. The Skill relies on the accompanying deterministic Python engine, schemas, validation, and report generator.

Start with `$decision-analysis`, then describe the decision in natural language. Ordinary Skill users do not need JSON knowledge or manual Python commands.

## During development

Codex was used to create the repository structure, implement the standard-library Python engines, write executable validation and JSON schemas, create tests, audit the code, build the reusable Skill, generate local HTML reports, and prepare release documentation.

Independent Codex review passes checked mathematics, privacy, security, beginner usability, documentation accuracy, contest presentation, release reproducibility, and truthful feature claims. Two live human Skill acceptance tests were also completed.

## During product use

Codex and the language model are responsible for conversational and structuring work:

- Interpret the user’s natural-language decision.
- Select one of the two supported mathematical structures.
- Ask adaptive questions in small batches.
- Preserve user terminology while creating safe internal IDs.
- Separate facts, estimates, preferences, constraints, assumptions, and settings.
- Notice possible double counting or contradictions.
- Assemble and present a complete proposed model.
- Require the exact reply `CONFIRM` before calculation.
- Invoke deterministic validation, analysis, and reporting commands after confirmation.
- Explain only stored results and keep the recommendation conditional.

No recommendation calculation occurs before the user reviews the proposed model and replies exactly `CONFIRM`.

## Deterministic boundary

Python is responsible for authoritative numerical calculations. The language model does not manually reproduce Monte Carlo simulation, sensitivity thresholds, or dynamic programming values, and it does not guarantee arithmetic accuracy.

After exact confirmation, Python validates the model, performs the numerical analysis, saves versioned result JSON, and generates a local HTML report. The report generator reads validated saved result JSON; it does not call either engine or independently choose a recommendation.

Direct Python CLI commands are optional tools for developers, reviewers, and manual verification. They are not required for ordinary repository-scoped Skill use.

## Where conversational care remains necessary

Human and language-model judgment can still affect:

- Whether criteria are meaningful and non-overlapping.
- How vague estimates are translated into numerical ranges.
- Whether anchors represent meaningful worst and best outcomes.
- Whether a condition is mandatory or compensable.
- Whether an approximation fits the real decision structure.
- Which private context is unnecessary and should not be stored.

The confirmation review exists so the user—not the language model—approves the final representation before calculation.
