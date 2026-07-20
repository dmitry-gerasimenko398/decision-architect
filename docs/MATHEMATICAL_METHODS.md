# Mathematical methods

Decision Architect supports two version-1 model structures. The user confirms all inputs before deterministic Python analysis begins.

## Multi-criteria model

### Hard constraints

Hard constraints filter alternatives before utility ranking. A lower-bound rule such as `salary >= 50000` inspects the full triangular support conservatively, so the minimum must pass. Upper-bound rules inspect the maximum. The engine recomputes every declared pass/fail value and stops on disagreement.

### Utility anchors and weights

For criterion value `x`, confirmed worst anchor `a`, and best anchor `b`:

```text
u(x) = clamp((x - a) / (b - a), 0, 1)
```

This works for increasing and decreasing preferences because anchor order carries the direction. For criterion weights `w_k` that sum to one:

```text
U(alternative) = Σ w_k × u_k(alternative)
```

Anchors and weights represent the user’s preferences. They are not objectively inferred.

### Triangular uncertainty and Monte Carlo

Every uncertain raw value uses a minimum `l`, most likely value `m`, and maximum `h`. Its analytical mean is:

```text
E[X] = (l + m + h) / 3
```

The engine uses a dedicated seeded `random.Random` instance to draw the confirmed triangular values. It calculates each alternative’s utility in every scenario, then reports distributions and Monte Carlo mean utility. Feasible alternatives are primarily ranked by Monte Carlo mean utility; analytical utility is a transparent cross-check.

**Simulated win probability is the fraction of modeled Monte Carlo scenarios in which an alternative has the highest utility. It is not the probability that the real-life decision will succeed.** Simulation ties split credit equally.

A unique mean-utility leader is classified as `close_call` when its simulated win probability is below `0.60`; otherwise it is `recommended`. Exact mean-utility ties remain explicit.

### Fixed-sample one-at-a-time sensitivity

Sensitivity reuses one fixed Monte Carlo sample. When target weight `w_k` becomes `x`, every other weight changes proportionally:

```text
w_k(x) = x
w_j(x) = original_w_j × (1 - x) / (1 - original_w_k)
```

The fixed-sample mean score is linear in `x`:

```text
mean_U_a(x) = x × target_mean_a + (1 - x) × weighted_other_mean_a
```

The engine solves winner crossings analytically, verifies both sides, and reports the nearest lower and upper switch plus the robust interval around the baseline. This varies one preference at a time; it does not model simultaneous weight changes.

## Sequential exploration model

The state is `(t, u, b)`:

- `t`: remaining opportunities, including the current one
- `u`: genuinely unseen options remaining
- `b`: best known net utility

For new-option draw `X`:

```text
V(0, u, b) = 0
exploit(t, u, b) = b + V(t - 1, u, b)
explore(t, u, b) = E[X + V(t - 1, u - 1, max(b, X))]  when u > 0
V(t, u, b) = max(exploit(t, u, b), explore(t, u, b))
```

Exploration receives the new value immediately, consumes one unseen option, and preserves a better discovery for later. When `u = 0`, exploration is unavailable.

### Deterministic expectation

The engine approximates the expectation with midpoint quantile quadrature. For `N` points:

```text
p_i = (i + 0.5) / N,  i = 0, …, N - 1
```

Each `p_i` is mapped through the triangular inverse CDF. The continuation values are averaged. `N` defaults to `101`, must be positive and odd, and introduces no random sampling. Dynamic programming memoizes best-known values at 12 decimal places and compares actions with tolerance `1e-10`.

The result reports the current action and a policy for every remaining horizon from 1 through the confirmed horizon.

## Assumptions and limitations

- Utility is subjective and user-defined.
- Weights are elicited preferences, not objective facts.
- Triangular distributions approximate uncertain judgments.
- Multi-criteria uncertainties are sampled independently; real criteria can be dependent.
- Correlation matrices, copulas, Bayesian networks, and influence diagrams are not implemented.
- Future versions may investigate those approaches only with validated inputs and explicit contracts.
- One-at-a-time sensitivity does not change several weights simultaneously.
- Sequential unseen options are independent draws from one fixed distribution.
- The sequential MVP has no learning about that distribution, discounting, or separate exploration cost outside net utility.
- The sanitized university postponement option is a full-horizon approximation; it is not solved as a genuinely staged future decision.
- The tool is decision support, not authoritative medical, legal, financial, educational, or safety advice.

Exact implementation rules are recorded in [PROJECT_SPEC.md](../PROJECT_SPEC.md), while the machine-readable contracts are in [schemas](../schemas/README.md).
