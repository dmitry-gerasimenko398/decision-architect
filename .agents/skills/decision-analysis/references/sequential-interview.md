# Sequential-exploration interview

Confirm that exploring reveals a value and a good discovery can be reused. Name what is explored and what known option is exploited.

## State

Collect remaining opportunities including now, genuinely unseen options, and the best-known net utility. If unseen options are zero, explain that exploration is unavailable; correct the count if the user expects otherwise.

## Utility scale

Propose 0–10 only as provisional: 0 is the worst meaningful experience and 10 the best realistically imaginable experience. Allow another scale. Record its bounds, unit, and meaning. All values must lie within it.

## New-option uncertainty

Ask for plausible minimum, most likely, and plausible maximum net utility. Explain that the MVP treats unseen options as independent draws from one triangular distribution. Do not manufacture numbers from adjectives.

## Assumptions and setting

Confirm that the horizon is finite; each action consumes one opportunity; exploration receives the new utility now; a better discovery is reusable; there is no discounting; exploration cost is included in net utility; and observations do not update the distribution.

Use `quadrature_points: 101` as a provisional documented default. Avoid early numerical-method detail unless asked.

## Review

Show horizon, unseen count, best-known value, utility scale, three-point distribution, assumptions, and quadrature count. Require exact `CONFIRM`.
