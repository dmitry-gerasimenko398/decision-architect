# Windows quickstart

This guide is for first-time users. You need the Codex app and Python 3.12 or a compatible Python 3 installation. You do not need Git, JSON knowledge, an API key, an external backend, or additional Python packages.

## 1. Download the complete project

### Option A — Download ZIP without Git

1. Open the Decision Architect repository page on GitHub.
2. Select **Code**.
3. Select **Download ZIP**.
4. Extract the downloaded archive to a folder you can find again.
5. Keep the complete extracted folder structure intact.

### Option B — Clone with Git

Open PowerShell and run:

```powershell
git clone https://github.com/dmitry-gerasimenko398/decision-architect.git
```

The complete repository is required. The Skill uses the included deterministic Python engine, schemas, validation, and report generator; downloading only `.agents/skills/decision-analysis/` is not the supported complete workflow.

## 2. Open the repository root in Codex

1. In Codex, open the extracted or cloned `decision-architect` folder.
2. Confirm that this repository root—the folder containing `README.md`, `.agents/`, and `decision_architect/`—is the current project.
3. Keep the conversation in this project so generated working files stay under its ignored `sessions/` directory.

No separate Skill installation is required for the supported repository-scoped workflow. Codex discovers `.agents/skills/decision-analysis/` when the complete repository root is opened as the project. The Skill is not globally installed by this process.

## 3. Start the Skill

Type:

```text
$decision-analysis
```

Then describe the decision in natural language. For example:

```text
I will visit this restaurant eight more times. Should I try a new dish or order the best one I already know?
```

or:

```text
I’m not sure which of three job options to choose.
```

The Skill should invite ordinary language; you do not need to write JSON.

## 4. What happens before calculation

Codex will:

1. Explain whether the decision fits `multi_criteria` or `sequential_exploration`.
2. Ask one to three related questions at a time.
3. Separate facts, uncertain estimates, preferences, hard constraints, assumptions, and settings.
4. Create a draft model in ignored local working storage.
5. Validate the draft and show a complete proposed-model review.
6. Wait for exact confirmation without calculating a recommendation.

Before confirmation, expect:

> Your model is ready for review. No recommendation has been calculated yet.

Read the alternatives, criteria, constraints, weights, estimates, horizon, settings, and assumptions. Ask for changes if anything is wrong.

Only this exact reply authorizes calculation:

```text
CONFIRM
```

“Okay,” “continue,” silence, or earlier agreement is not enough. Any model change requires a revised review and a fresh `CONFIRM`.

## 5. Calculation and generated report

After exact confirmation, deterministic Python validates the confirmed model, performs the numerical analysis, saves result JSON, and generates a self-contained HTML report. A normal working report is saved under:

```text
sessions\<decision-name>\report.html
```

Codex gives you the exact local path when generation succeeds. Open the report in a browser; it needs no server or external resource.

To browse the checked-in demonstrations without running Python, open `reports\index.html` in File Explorer. Sanitized end-to-end examples are also available in `demo_sessions\`.

## 6. Optional Python CLI usage

Ordinary Skill users do not need to run Python commands manually. The CLI is available for developers, reviewers, and manual verification of existing JSON files.

Open PowerShell in the repository root and check Python:

```powershell
py --version
```

Verify the complete release:

```powershell
py -m decision_architect verify-release
```

Run only the tests:

```powershell
py -m unittest discover -s tests -v
```

Regenerate one released result and report:

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
- No additional Python package is required.
- No external backend receives the model.
- Working sessions are stored locally under `sessions/` and ignored by Git.
- Do not enter unnecessary names, addresses, account data, health details, or other sensitive information.
- Sanitized release examples live under `examples/`, `outputs/`, `reports/`, and `demo_sessions/`.

For the contest walkthrough, continue with [Contest Demo](CONTEST_DEMO.md).
