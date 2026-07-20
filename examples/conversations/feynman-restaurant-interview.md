# Demonstration conversation: explore or exploit at a restaurant

The 8-visit and 2-visit outputs below were produced from the released example models and existing deterministic engine.

**User:** I will visit this restaurant several more times. Should I try a new dish or order the best one I already know?

**Decision Architect:** Will trying a dish reveal how much you like it, and could a good discovery become your repeat order on later visits?

**User:** Yes. I have eight visits left including today, and about ten genuinely untried dishes.

**Decision Architect:** This fits `sequential_exploration`: the choice repeats over a finite horizon and exploration creates reusable information. I’ve started a draft decision model. I won’t calculate a recommendation until you review and confirm it. Let’s use a provisional personal 0–10 net-enjoyment scale unless you prefer another. What does the scale mean, how good is your current favorite, and what is a plausible minimum / most likely / maximum for an unseen dish?

**User:** Use 0 for wholly unsatisfying and 10 for the best realistically imaginable visit. My favorite is 6.5. A new dish could plausibly be 2, is most likely 6, and could be 10.

**Decision Architect:** I’ll interpret those as net utility, so any cost or disappointment is already included. Please confirm these MVP assumptions: each action uses one visit; a better discovery remains available; there is no discounting; unseen dishes are independent draws from one unchanged triangular distribution; observing one dish does not teach us that distribution. I’ll also use the deterministic default of 101 quadrature points.

**User:** Confirmed.

**Decision Architect:** Your model is ready for review. No recommendation has been calculated yet. Complete review: 8 visits including now, 10 unseen dishes, best known 6.5 on the confirmed 0–10 scale, new option 2 / 6 / 10, the assumptions above, and 101 quadrature points. Please reply **CONFIRM** to run this exact model, or tell me what should be changed.

**User:** CONFIRM

**Decision Architect:** Model confirmed. I’ve now run the deterministic analysis and generated your report. Under the recorded scale, estimates, and 8-visit horizon, **EXPLORE** is preferable. Stored explore value is `57.5381807524`, exploit value is `56.2532719836`, and explore advantage is `1.2849087689`. The policy changes from EXPLOIT to EXPLORE at 3 remaining opportunities.

Report: `reports/feynman-restaurant-report.html`

**User:** What if I only have two visits remaining? Keep everything else the same.

**Decision Architect:** That materially changes the horizon, so I created a revised proposal rather than editing the confirmed result. Revised review: 2 visits including now; every other recorded value and assumption is unchanged. Please reply **CONFIRM** to analyze this revised model.

**User:** CONFIRM

**Decision Architect:** Model confirmed. I’ve now run the deterministic analysis and generated your revised report. With 2 remaining visits, **EXPLOIT** is preferable. Stored exploit value is `13.0`, explore value is `12.9462685899`, and explore advantage is `-0.0537314101`. The changed action comes from the confirmed shorter horizon, not from a hand-written rule.

Report: `reports/feynman-restaurant-short-horizon-report.html`

Both recommendations are conditional on the user's utility scale, estimates, horizon, and assumptions. This is Feynman-inspired; it does not claim to reproduce every detail of Feynman’s historical notes.
