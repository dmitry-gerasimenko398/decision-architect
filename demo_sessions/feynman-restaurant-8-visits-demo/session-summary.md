# Model review: Try a new dish or order the best-known dish

- Model version: `1.0`
- Model type: `sequential_exploration`
- Decision ID: `restaurant-dish-exploration`
- Decision description: Choose whether to order the best-known dish or try one untried dish on each remaining restaurant visit.
- Time horizon: Exactly 8 remaining restaurant visits, including the next visit
- Notes: The 0-10 values are personal ratings of dining experiences, not objective dish quality.

## Proposed state

- Remaining opportunities (including now): 8
- Unseen options remaining: 10
- Best known value: 6.5
- Utility scale: 0 to 10 net rating points
- Utility scale meaning: 0 means the worst meaningful dining experience; 10 means the best realistically imaginable dining experience.
- New-option estimate: 2 / 6 / 10
- Quadrature points: 101

## Assumptions

- Ratings are net utility, so there is no separate penalty for experimenting.
- Each action consumes exactly one remaining visit.
- A newly tried dish's rating is received immediately on that visit and remains known for later visits.
- The reusable best-known rating updates to the maximum of its old value and the newly observed rating.
- There is no discounting of later visits.
- Each untried dish is an independent draw from one fixed triangular rating distribution.
- Observing one dish does not update the rating distribution of the remaining untried dishes.

Explicitly confirmed. The model is ready for deterministic analysis.
