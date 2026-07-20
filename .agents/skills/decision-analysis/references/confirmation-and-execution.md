# Confirmation and execution

Run commands from the repository root. Follow the Python fallback in `docs/QUICKSTART_WINDOWS.md` when `py` is unavailable.

## Persist and check

```powershell
py -m decision_architect session-init "Decision name" --model-type multi_criteria
py -m decision_architect session-stage <slug> sessions\<slug>\proposed-model.json --source-type system_proposal --source-map <source-map.json>
py -m decision_architect session-check <slug>
```

Keep `confirmed_by_user: false` in the proposal. `session-stage` records field status and provenance. The optional source-map JSON maps exact material paths such as `$.state.best_known_value` to `user_estimate`; unmapped fields use `--source-type`. Use `system_proposal` as the safe default for Skill-authored labels, IDs, assumptions, and settings, then map only values actually supplied by the user. `session-check` calculates nothing, prints every material value, and persists fingerprints proving which review was generated for display.

After initialization, tell the user: “I’ve started a draft decision model. I won’t calculate a recommendation until you review and confirm it.”

## Enforce the gate

End with:

> Your model is ready for review. No recommendation has been calculated yet.
>
> Please reply CONFIRM to run this exact model, or tell me what should be changed.

Do not accept “okay,” “continue,” silence, or earlier general agreement. After any change, restage, recheck, redisplay, and request fresh confirmation.

Only after exact `CONFIRM`, run:

```powershell
py -m decision_architect session-finalize <slug> --confirmation CONFIRM
```

This creates `confirmed-model.json` and sets its confirmation flag only if the current proposal matches the displayed review fingerprints. It still performs no calculation. Direct finalization after staging is rejected.

## Calculate and report

```powershell
py -m decision_architect analyze sessions\<slug>\confirmed-model.json --output sessions\<slug>\result.json
py -m decision_architect report sessions\<slug>\result.json --output sessions\<slug>\report.html
```

The report command validates saved result JSON. Stop on any non-zero command and create no later artifact.

Explain only stored output. For multi-criteria report leader/tie, uncertainty, exclusions, closest weight switch, and robust interval. For sequential report action, values, advantage, horizon, and first policy switch. Give `report.html` and repeat conditionality.

After analysis and report generation both succeed, say: “Model confirmed. I’ve now run the deterministic analysis and generated your report.” Explain simulated win probability as the percentage of modeled Monte Carlo scenarios in which an alternative ranked first, never as the chance that the real-life choice will succeed.
