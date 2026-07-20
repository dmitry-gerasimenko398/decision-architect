# Demonstration conversation: choosing a job

This transcript is condensed for readability but preserves the actual interview sequence. Its released model is `examples/job-choice.json`; the recommendation comes from `outputs/job-choice-result.json`.

**User:** I’m not sure whether I should accept a new job offer.

**Decision Architect:** Is this one choice among known job options, or will you repeatedly try jobs and reuse information from each attempt?

**User:** One choice. I have three realistic options: a stable corporation, a remote startup, and a local nonprofit. I expect to stay about two years.

**Decision Architect:** This fits `multi_criteria`: one decision among known alternatives with competing considerations. I’ve started a draft decision model. I won’t calculate a recommendation until you review and confirm it. Is there a meaningful fourth option such as negotiating or continuing the search?

**User:** No. Use those three.

**Decision Architect:** You mentioned needing at least €50,000. If an offer might fall below that, should it be eliminated completely, or merely receive a lower salary score?

**User:** Eliminate it. That is a genuine minimum.

**Decision Architect:** I’ll record a hard constraint: every supported salary value must be at least €50,000. What distinct considerations should score the remaining options?

**User:** Annual salary, work-life balance, learning and growth, and weekly commute time.

**Decision Architect:** Those are distinct enough if commute means total minutes per week. Please confirm provisional utility anchors—the values that represent utility 0 and 1:

- Salary: worst €45,000; best €100,000.
- Work-life balance: worst 3; best 9 on a 0–10 rating.
- Learning and growth: worst 2; best 10.
- Weekly commute: worst 120 minutes; best 0 minutes.

**User:** Confirmed. Commute is total minutes per week.

**Decision Architect:** Imagine every criterion at its worst meaningful level. Which worst-to-best improvement matters most? Then allocate 100 relative importance points.

**User:** Salary first, balance and growth tied next, commute last. Use 35 points for salary, 25 balance, 25 growth, and 15 commute.

**Decision Architect:** That produces confirmed weights of 35%, 25%, 25%, and 15%. Please give your minimum / most likely / maximum estimates in the units above. A compact table is fine.

**User:** Here are my estimates:

| Alternative | Salary (€) | Balance (0–10) | Growth (0–10) | Commute (min/week) |
|---|---:|---:|---:|---:|
| Stable corporation | 70,000 / 75,000 / 82,000 | 5 / 6 / 7 | 5 / 6 / 8 | 45 / 60 / 75 |
| Remote startup | 60,000 / 70,000 / 90,000 | 4 / 6 / 8 | 7 / 9 / 10 | 0 / 0 / 0 |
| Local nonprofit | 48,000 / 52,000 / 58,000 | 7 / 8 / 9 | 4 / 6 / 7 | 15 / 25 / 40 |

**Decision Architect:** I propose the documented fixed defaults of 10,000 Monte Carlo samples, seed `20260720`, and utility clamping. Assumptions: salary is gross annual euros; criterion estimates are independent in the MVP; the minimum salary rule is applied to the complete estimated range; the horizon is about two years. Are these correct?

**User:** Yes.

**Decision Architect:** Your model is ready for review. No recommendation has been calculated yet. The complete review lists all alternatives, constraint outcomes, criteria, anchors, weights, ranges, assumptions, sample count, and seed. Please reply **CONFIRM** to run this exact model, or tell me what should be changed.

**User:** CONFIRM

**Decision Architect:** Model confirmed. I’ve now run the deterministic analysis and generated your report.

Under the confirmed preferences, estimates, constraints, two-year horizon, and assumptions, **Remote startup** is preferable. It has Monte Carlo mean utility `0.6635452465` and wins `98.76%` of simulated scenarios. The local nonprofit is excluded by the salary constraint. The closest fixed-sample preference switch occurs when salary weight rises from `0.35` to approximately `0.8435903603`; beyond that threshold Stable corporation leads.

The `98.76%` simulated win probability is the fraction of modeled Monte Carlo scenarios in which Remote startup ranked first. It is not the probability that the job will succeed in real life.

This is conditional decision support, not an objectively correct career choice.

Report: `reports/job-choice-report.html`
