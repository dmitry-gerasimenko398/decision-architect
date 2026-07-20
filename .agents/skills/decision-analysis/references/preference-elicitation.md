# Preference elicitation

Use guided swing weighting. Do not begin by demanding arbitrary percentages.

## Rank value swings

Say:

> Imagine every criterion is currently at its worst meaningful level. Which single improvement from worst to best would matter most?

Ask the user to rank worst-to-best improvements, not criterion names in isolation.

## Allocate points

Invite 100 relative importance points across the swings. If exact points are difficult, propose a clearly labeled provisional allocation from the ranking and ask the user to adjust it.

Convert confirmed points with `weight = criterion points / total points`. Show points and percentages. Require non-negative values, at least one positive value, and final weights summing to 1.

Never silently normalize numbers intended as final weights; first ask whether they are swing points or weights. Check whether a very high weight reflects true importance or poorly chosen anchor ranges, and check overlapping criteria.

Weights are the user's confirmed preference representation, not objective or statistically inferred facts.
