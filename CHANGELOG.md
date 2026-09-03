# Changelog

Notable changes, newest first. Versions follow semver; the version lives in
`brainbuddy/__init__.py` and each release is the matching `v*` tag.

## Unreleased

- One-line install: `bootstrap.sh` fetches the latest tagged release, unpacks it
  to a temp dir and runs its `install.sh` with whatever flags you passed, so the
  usual path is one command instead of a clone. It falls back to the default
  branch until a release exists.
- PyPI packaging: `pipx install brainbuddy` / `uvx brainbuddy` now work; the
  installed entry point is the same `brainbuddy` command the shim calls.
- Release workflow: tagging `vX.Y.Z` tests, builds, and publishes to PyPI via
  trusted publishing.
- `brainbuddy doctor` reports the installed version.

## 0.1.0

Everything before packaging: the creature, the egg-and-hatch flow, three XP
providers, the statusline wrap installer, five slash commands, the leak guard,
and the test suite.
