# Release checklist — 1.0.0-rc1

## Automated

- [x] `py -m decision_architect verify-release` exits with code 0 when run with the available Python runtime.
- [x] Complete unittest suite passes.
- [x] All released models and results validate.
- [x] Regenerated results, reports, report index, and demo sessions match release bytes.
- [x] Privacy, external-resource, placeholder, version, Skill, and release-manifest checks pass.
- [x] Controlled clean-copy verification passes without `sessions/`, caches, network access, or machine paths.

## Human

- [x] Read the first-screen README as a new judge.
- [ ] Follow `docs/QUICKSTART_WINDOWS.md` on Windows.
- [ ] Review reports at normal zoom, mobile width, and print preview.
- [ ] Confirm the contest video follows `docs/CONTEST_DEMO.md` and stays under three minutes.
- [x] Confirm all recommendations remain conditional.
- [x] Confirm the university postponement approximation remains prominent.
- [x] Review the intended Git file list before the first commit.
- [ ] Configure a real Git identity only if the repository owner approves it.
- [ ] Create a remote repository, push, and submit only in a separately approved phase.
