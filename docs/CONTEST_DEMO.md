# Contest demonstration

Target: **2 minutes 45 seconds**. Keep the main video visual and conversational; do not show the full university interview or a wall of terminal commands.

## Shot list

### 0:00–0:15 — Product promise

Show the README title and say:

> Decision Architect turns an informal personal decision into a user-confirmed mathematical model, deterministic analysis, and an explainable local report.

Briefly show the architecture flow. Mention that no API key or external backend is required.

### 0:15–1:15 — Live Feynman-inspired interview

In Codex, type exactly:

```text
$decision-analysis I will visit this restaurant eight more times. Should I try a new dish or order the best one I already know?
```

Use these concise answers when asked:

```text
I have 8 visits left including the next visit and 10 genuinely untried dishes. My best-known dish is 6.5 on a 0–10 net-enjoyment scale.
```

```text
For a new dish, use minimum 2, most likely 6, maximum 10. A good discovery can be ordered again later.
```

Accept the displayed finite-horizon, independent-draw, no-learning, no-discounting assumptions and the provisional `101` quadrature points.

Accelerate or cut repetitive data-entry moments. Pause when the Skill says:

> Your model is ready for review. No recommendation has been calculated yet.

Show `confirmed_by_user: false` or the missing result artifact briefly. Then type:

```text
CONFIRM
```

### 1:15–1:45 — Result and horizon policy

Open `reports/feynman-restaurant-report.html`.

Show:

1. EXPLORE at eight visits.
2. Explore value about `57.5382`, exploit value about `56.2533`.
3. Horizon chart: EXPLOIT at 1–2; EXPLORE from 3.
4. Conditionality and assumptions.

### 1:45–2:05 — Multi-criteria evidence

Open `reports/job-choice-report.html` and show:

1. Monte Carlo uncertainty table.
2. Hard-constraint exclusion.
3. Weight-switch sensitivity.
4. The explanation that simulated win probability is modeled first-place frequency, not real-life success probability.

Say that a second live human acceptance test compared staying, transferring now, and postponing a university transfer. It preserved a near-home hard constraint, corrected double counting, and recommended postponement under the confirmed inputs. Do not replay the long interview.

### 2:05–2:30 — Architecture and evidence

Briefly show:

- `.agents/skills/decision-analysis/SKILL.md`
- `decision_architect/multi_criteria.py`
- `decision_architect/sequential_exploration.py`
- `schemas/decision-model-v1.schema.json`
- the final test count from `py -m decision_architect verify-release`

Say:

> GPT-5.6/Codex handles interpretation, adaptive interviewing, confirmation, tool invocation, and conditional explanation. Deterministic Python performs the numerical calculations.

### 2:30–2:45 — Close

Use this final sentence:

> Decision Architect does not claim the objectively correct life choice; it makes the user’s assumptions visible and shows what is preferable under the model they confirmed.

## Recording notes

- Pre-open the report tabs before recording.
- Increase browser zoom enough for headings and values to be readable.
- Cut loading and long interview pauses; do not fake the confirmation order.
- Keep browser print headers and footers off if showing a PDF capture, because browsers can add local file paths that are not present in the HTML source.
