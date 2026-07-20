# Model review: Choose between three job offers

- Model version: `1.0`
- Model type: `multi_criteria`
- Decision ID: `job-choice-example`
- Decision description: Compare three realistic job options under confirmed personal priorities.
- Time horizon: One-time choice with an expected two-year stay
- Notes: Example data is fictional and is not career advice.

## Alternatives

- Stable corporation (`stable-corp`): Established company with moderate growth and a hybrid commute.
- Remote startup (`remote-startup`): Fully remote role with greater upside and uncertainty.
- Local nonprofit (`local-nonprofit`): Mission-oriented local role with strong balance and lower salary.

## Criteria and weights

- Annual salary: 0.35 (EUR per year); maximize; Gross annual base salary.; anchors 45000 to 100000
- Work-life balance: 0.25 (rating from 0 to 10); maximize; Expected sustainability of hours, flexibility, and recovery time.; anchors 3 to 9
- Learning and growth: 0.25 (rating from 0 to 10); maximize; Expected opportunities to learn, gain responsibility, and improve future options.; anchors 2 to 10
- Weekly commute time: 0.15 (minutes per week); minimize; Total expected commuting time per week.; anchors 120 to 0

## Hard constraints

- Minimum viable salary (`minimum_salary`): Every supported gross annual base salary must be at least EUR 50000. Rule: salary >= 50000
  - Stable corporation: passes
  - Remote startup: passes
  - Local nonprofit: fails

## Three-point estimates

### Stable corporation

- Annual salary (EUR per year): 70000 / 75000 / 82000 (minimum / most likely / maximum)
- Work-life balance (rating from 0 to 10): 5 / 6 / 7 (minimum / most likely / maximum)
- Learning and growth (rating from 0 to 10): 5 / 6 / 8 (minimum / most likely / maximum)
- Weekly commute time (minutes per week): 45 / 60 / 75 (minimum / most likely / maximum)
### Remote startup

- Annual salary (EUR per year): 60000 / 70000 / 90000 (minimum / most likely / maximum)
- Work-life balance (rating from 0 to 10): 4 / 6 / 8 (minimum / most likely / maximum)
- Learning and growth (rating from 0 to 10): 7 / 9 / 10 (minimum / most likely / maximum)
- Weekly commute time (minutes per week): 0 / 0 / 0 (minimum / most likely / maximum)
### Local nonprofit

- Annual salary (EUR per year): 48000 / 52000 / 58000 (minimum / most likely / maximum)
- Work-life balance (rating from 0 to 10): 7 / 8 / 9 (minimum / most likely / maximum)
- Learning and growth (rating from 0 to 10): 4 / 6 / 7 (minimum / most likely / maximum)
- Weekly commute time (minutes per week): 15 / 25 / 40 (minimum / most likely / maximum)

## Reproducibility settings

- Monte Carlo samples: 10000
- Random seed: 20260720
- Clamp utility to anchors: True

## Assumptions

- All salary values are gross annual euros.
- Criterion estimates are treated as independent in the MVP Monte Carlo model.
- The minimum salary constraint applies conservatively to the full triangular salary range.
- Weights and utility anchors have been reviewed and confirmed by the user.

Explicitly confirmed. The model is ready for deterministic analysis.
