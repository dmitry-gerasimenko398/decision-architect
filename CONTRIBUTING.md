# Contributing

Decision Architect is currently a local release candidate.

Before changing code:

1. Read `AGENTS.md`, `PROJECT_SPEC.md`, and the relevant schema.
2. Preserve the boundary between conversational interviewing and deterministic calculations.
3. Do not add a model type or change approved mathematics without a separately reviewed design phase.
4. Keep runtime code standard-library-only unless a dependency is explicitly approved.
5. Add or update tests and conditional-language documentation.
6. Run:

```powershell
py -m decision_architect verify-release
```

Never include `sessions/`, private context, machine-specific paths, caches, or temporary artifacts in a contribution. Do not edit stored result JSON by hand to manufacture a desired recommendation.
