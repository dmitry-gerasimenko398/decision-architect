# Known limitations

- The MVP supports only `multi_criteria` and `sequential_exploration`.
- Utility anchors, weights, estimates, and constraint choices remain subjective user inputs.
- Multi-criteria uncertainties use triangular distributions and are sampled independently.
- Simulated win probability is modeled first-place frequency, not real-life success probability.
- One-at-a-time sensitivity preserves other weight proportions and does not vary several preferences simultaneously.
- The sequential model assumes independent new-option draws from one fixed distribution, no learning, no discounting, and exploration cost already included in net utility.
- The university postponement example approximates postponement as a full-horizon alternative; it is not a genuinely staged sequential solution.
- Correlation matrices, copulas, Bayesian networks, and influence diagrams are possible future research directions but are **not implemented**.
- Conversational judgment still requires care around double counting, vague estimates, meaningful anchors, hard constraints, and privacy.
- This is decision support, not authoritative medical, legal, financial, educational, or safety advice.

See [Mathematical Methods](docs/MATHEMATICAL_METHODS.md) for formulas and assumptions.
