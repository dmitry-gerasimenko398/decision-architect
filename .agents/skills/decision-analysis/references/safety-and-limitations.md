# Safety and limitations

- Support only `multi_criteria` and `sequential_exploration`; reject unsupported structure honestly.
- Treat high-stakes choices as decision support, not professional advice.
- Store only model-required information. Avoid unnecessary employer names, addresses, health details, account data, or identifiers.
- Keep session files inside project `sessions/`. Use the safe slug returned by `session-init`, never raw user text as a path.
- Do not access external services, APIs, live data, private files, or networks.
- Do not claim certainty, guaranteed outcomes, causal effects, or an objectively correct decision.
- Preserve uncertainty, ties, infeasibility, warnings, and unavailable actions.
- Explain independent criterion sampling and one-at-a-time weight sensitivity for multi-criteria models.
- Explain simulated win probability as modeled first-place frequency, not real-life success probability.
- Do not imply that correlation matrices, copulas, Bayesian networks, or influence diagrams are implemented.
- Explain independent unchanged new-option draws, no discounting, and no learning for sequential models.
- After material changes, return to proposal review and obtain fresh confirmation.
- Never edit result JSON. Generate reports only from saved validated results.
