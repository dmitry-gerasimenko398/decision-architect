# Windows quickstart

This guide assumes you have Codex and a downloaded or cloned copy of Decision Architect. You do not need to understand Git or JSON to use the Skill.

## 1. Open the project in Codex

1. In Codex, choose the folder containing `README.md` and `decision_architect/`.
2. Confirm that the project name is `decision-architect`.
3. Keep the conversation in this project so generated working files remain under its ignored `sessions/` directory.

## 2. Start the Skill

Type:

```text
$decision-analysis
```

Then describe the choice normally. For example:

```text
I will visit this restaurant eight more times. Should I try a new dish or order the best one I already know?
```

or:

```text
I’m not sure which of three job options to choose.
```

The Skill should invite ordinary language, not ask you to write JSON.

## 3. What the Skill does automatically

Codex will:

1. Explain whether the decision fits `multi_criteria` or `sequential_exploration`.
2. Ask one to three related questions at a time.
3. Separate facts, uncertain estimates, preferences, hard constraints, assumptions, and settings.
4. Create a draft model inside ignored local working storage.
5. Validate the draft and show a complete review.
6. Wait for exact confirmation.
7. Run deterministic Python analysis only after confirmation.
8. Validate the saved result and generate a local HTML report.
9. Explain the stored result conditionally.

## 4. Confirmation gate

Before confirmation, expect:

> Your model is ready for review. No recommendation has been calculated yet.

Read the alternatives, criteria, constraints, weights, estimates, horizon, settings, and assumptions. Ask for changes if anything is wrong.

Only this exact reply authorizes calculation:

```text
CONFIRM
```

“Okay,” “continue,” silence, or an earlier agreement is not enough. Any later model change requires a new review and fresh `CONFIRM`.

## 5. Open the released demonstrations

No Python command is needed to view the checked-in reports. In File Explorer, open the `reports` folder and double-click:

```text
index.html
```

The reports are standalone files. They do not need a web server, API key, or internet connection.

## 6. Run Python commands manually

Manual commands are separate from the Codex interview. Open PowerShell in the repository folder and try:

```powershell
py --version
```

If that works, verify the complete release:

```powershell
py -m decision_architect verify-release
```

Run only the tests:

```powershell
py -m unittest discover -s tests -v
```

Regenerate one result and report:

```powershell
py -m decision_architect analyze examples\job-choice.json --output outputs\job-choice-result.json
py -m decision_architect report outputs\job-choice-result.json --output reports\job-choice-report.html
```

## 7. If `py` is unavailable

Try:

```powershell
python --version
```

If that works, replace `py` with `python` in every command.

If neither command works, do not copy a machine-specific path from someone else. In Codex, ask:

```text
Please locate the Python runtime configured for this workspace and run the release verifier without installing anything.
```

Codex environments may provide a bundled runtime at a path that varies by computer. If no compatible runtime is available, manual CLI calculation cannot run until Python 3.12 is made available by the user or administrator. The checked-in reports can still be opened.

## 8. Privacy and local files

- No API key is required.
- No external backend receives the model.
- Working sessions are stored locally under `sessions/` and ignored by Git.
- Do not enter unnecessary names, addresses, account data, health details, or other sensitive information.
- Sanitized release examples live under `examples/`, `outputs/`, `reports/`, and `demo_sessions/`.

For the contest walkthrough, continue with [Contest Demo](CONTEST_DEMO.md).
