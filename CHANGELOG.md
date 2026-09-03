# Changelog

Notable changes, newest first. Versions follow semver; the version lives in
`brainbuddy/__init__.py` and each release is the matching `v*` tag.

## Unreleased

- PyPI packaging: `pipx install brainbuddy` / `uvx brainbuddy` now work; the
  installed entry point is the same `brainbuddy` command the shim calls.
- Release workflow: tagging `vX.Y.Z` tests, builds, and publishes to PyPI via
  trusted publishing.
- `brainbuddy doctor` reports the installed version.

## 0.1.0

Everything before packaging: the creature, the egg-and-hatch flow, three XP
providers, the statusline wrap installer, five slash commands, the leak guard,
and the test suite.
