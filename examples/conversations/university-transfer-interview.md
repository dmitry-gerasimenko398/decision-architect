# Sanitized acceptance-test conversation: university faculty transfer

This is a condensed, sanitized account of the successful live human multi-criteria acceptance test. It contains no working-session path or personal identity. The stored model is `examples/university-transfer.json`; the exact engine output is `outputs/university-transfer-result.json`.

**User:** I need to decide whether and when to transfer university faculty.

**Decision Architect:** This provisionally fits `multi_criteria`: one choice among known alternatives with several competing considerations. I’ve started a draft decision model. I won’t calculate a recommendation until you review and confirm it. What alternatives belong in the comparison, and what time horizon matters?

**User:** Stay in my current faculty, transfer now, or postpone for one semester while I gather more information. Compare the rest of my studies and the first three years after graduation.

**Decision Architect:** Does remaining near home eliminate an option completely, or is it a preference that another benefit could compensate for?

**User:** It is mandatory. Eliminate an option if it requires relocation, regular overnight stays away, or placements that prevent regular returns home. All three current alternatives pass.

**Decision Architect:** I’ll keep that as a hard constraint, not a weighted preference. Which distinct considerations should score the eligible alternatives?

**User:** Compatibility with family responsibilities, subject interest, career prospects, time until graduation, and the value of additional information and reversibility.

**Decision Architect:** Schedule flexibility and workload predictability could double-count family compatibility. Should they be separate criteria, or parts of one family-compatibility judgment?

**User:** Combine them into family compatibility. Information and reversibility should include only residual value not already counted elsewhere.

**Decision Architect:** Using confirmed 0–10 anchors for the four subjective criteria and 7-to-4 semesters for time until graduation, rank the worst-to-best swings and allocate 100 importance points.

**User:** Family compatibility 30, subject interest 25, career prospects 20, time until graduation 15, and information and reversibility 10.

**Decision Architect:** I then collected and repeated back the minimum / most likely / maximum estimates for all three alternatives and five weighted criteria. The full confirmed ranges are preserved in `examples/university-transfer.json`. I proposed the fixed seed `314159`, 10,000 Monte Carlo samples, utility clamping, and independent criterion sampling.

**User:** Those values and settings reflect my estimates. I understand that postponing is approximated as one full-horizon strategy; this model does not solve it as a genuinely staged future decision.

**Decision Architect:** Your model is ready for review. No recommendation has been calculated yet. The near-home indicator appears only with the hard constraint and contributes no preference weight. Please reply **CONFIRM** to run this exact model, or tell me what should be changed.

**User:** CONFIRM

**Decision Architect:** Model confirmed. I’ve now run the deterministic analysis and generated your report.

Under the confirmed preferences, estimates, constraint, horizon, and assumptions, **Postpone for one semester** is preferable:

- Postpone: mean utility `0.6899506869`; simulated win probability `85.49%`.
- Transfer now: mean utility `0.6368200306`; simulated win probability `14.35%`.
- Stay: mean utility `0.5786658304`; simulated win probability `0.16%`.

Simulated win probability is the fraction of modeled Monte Carlo scenarios in which an alternative ranked first. It is not the probability that the real-life decision will succeed.

The closest reported winner switch occurs when the information-and-reversibility weight falls from `0.10` to approximately `0.02618`; below that verified boundary, Transfer now leads. The result remains conditional, and the postponement option remains a full-horizon approximation rather than a staged sequential solution.

Sanitized report: `reports/university-transfer-report.html`
