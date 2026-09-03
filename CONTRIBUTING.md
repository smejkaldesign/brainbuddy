# Contributing

Small project, short rules.

## Setup

```bash
git clone https://github.com/smejkaldesign/brainbuddy
cd brainbuddy
python3 tests/test_brainbuddy.py
```

That's the whole setup. No virtualenv to make, nothing to install, no build step.
Run the CLI straight out of the clone with `python3 -m brainbuddy.cli card`.

## Stdlib only

Hard rule, not a preference. brainbuddy runs inside a statusline that redraws on
every prompt, and it installs on machines whose Python nobody controls. A PR that
adds a runtime dependency, or a test dependency, will be declined. If something
seems to need a library, the answer is usually a smaller feature.

Python 3.9 is the floor. No walrus-in-comprehension cleverness that only parses on newer.

## The leak guard

`scripts/leak-guard.sh` fails on absolute home paths and vault-shaped filenames.
The project was built against a real private note vault, and a pasted traceback or
a debug line is all it takes to commit somebody's directory layout. CI runs it on
every PR. Run it locally the same way:

```bash
./scripts/leak-guard.sh
```

There's a `pre-push` copy that catches it before the push instead of after. Opt in:

```bash
git config core.hooksPath .githooks
```

## Pull requests

- `python3 tests/test_brainbuddy.py` green. CI runs it on 3.9 through 3.13.
- `./scripts/leak-guard.sh` clean.
- New behavior gets a test. The privacy tests in particular are load-bearing: if you
  touch `metric.py`, the reader trap and the static scan both have to keep passing.
- Match the voice. Lowercase, deadpan, short. No emoji, no em dashes, in code or docs.
- Comments only for constraints the code can't show. Not what the next line does.
- One change per PR. A rename and a feature are two PRs.

## Versions and releases

The version lives in `brainbuddy/__init__.py`, with one echo in
`.claude-plugin/plugin.json` for the plugin cache. Don't bump either in a feature
PR; note the change under `## Unreleased` in `CHANGELOG.md` instead.

Releases are Eric's: bump `__version__` and the plugin.json version together, move
the changelog entries under the new heading, tag `vX.Y.Z`. The tag triggers
`publish.yml`, which tests, checks the tag against both versions, builds, and
publishes to PyPI via trusted publishing. A tag that doesn't match either version
fails the build on purpose.
