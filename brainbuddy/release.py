"""Version discovery. The only code in brainbuddy that opens a socket.

A socket opens on exactly three paths, all consented: `update`, `doctor
--check`, and, only for users who set `update_check` on, the background
refresh's once-a-day `maybe_refresh_latest`. A pet that phoned home from the
statusline would be checking a few times a second and reading as spyware, so
the render path only ever reads the cache those three write. One request per
invocation, no retries; the daily check caches under a 24h stamp.
"""

import json

from . import __version__

PYPI_URL = "https://pypi.org/pypi/brainbuddy/json"
TIMEOUT = 4.0


def _parts(version):
    """Dotted version as a comparable tuple. Junk in a field reads as 0."""
    out = []
    for chunk in str(version).split("."):
        digits = ""
        for ch in chunk:
            if not ch.isdigit():
                break
            digits += ch
        out.append(int(digits) if digits else 0)
    return tuple(out)


def fetch_latest(url=PYPI_URL, timeout=TIMEOUT):
    """One request to pypi. Returns (status, version), never raises.

    status is ok, unpublished (nothing under that name yet) or unreachable.
    """
    try:
        # kept off module import so `from . import release` stays cheap, and
        # inside the try because a python built without ssl can't import
        # urllib.request at all, which is still just "unreachable" to us
        import urllib.error
        import urllib.request

        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return "ok", data["info"]["version"]
    except urllib.error.HTTPError as e:
        return ("unpublished", None) if e.code == 404 else ("unreachable", None)
    except Exception:
        # timeouts, dns, proxies, tls, a body that isn't the json we expect. an
        # update check is never worth an exit code, so every one of them is calm
        return "unreachable", None


def status_line(status, latest, current=__version__):
    if status == "unpublished":
        return "brainbuddy isn't on pypi yet, so there's nothing to compare against. you're on %s." % current
    if status == "unreachable":
        return "couldn't reach pypi just now. you're on %s, try again when it's back." % current
    if _parts(latest) > _parts(current):
        return "brainbuddy %s is out, you're on %s; re-run your installer, pipx upgrade brainbuddy, or take the plugin update. (brainbuddy is becoming terminalcreature; the installer handles the move.)" % (
            latest, current)
    if _parts(latest) < _parts(current):
        return "you're on %s and pypi has %s, so you're ahead of the release." % (current, latest)
    return "brainbuddy %s is the latest under this name, and the last: it's now terminalcreature. re-run your bootstrap, or pipx install terminalcreature." % current


def check():
    status, latest = fetch_latest()
    # the chip reads this cache, so a manual check and the statusline agree.
    # a cache that can't be written is not worth failing the answer over
    try:
        from . import state as state_mod
        state_mod.write_latest(latest if status == "ok" else "")
    except Exception:
        pass
    return status_line(status, latest)


def maybe_refresh_latest(settings):
    """The once-a-day check the background refresh carries. Opt-in only.

    Failures stamp the cache too, so an offline machine retries tomorrow
    rather than on every refresh, and never more than once per TTL.
    """
    if not settings.get("update_check"):
        return
    from . import state as state_mod
    cached = state_mod.read_latest()
    if cached is not None and cached[1] < state_mod.UPDATE_TTL:
        return
    status, latest = fetch_latest()
    state_mod.write_latest(latest if status == "ok" else "")


def update_available(settings, current=__version__):
    """True when the cached check says a newer version exists. Reads a file,
    never the network: the render path calls this on every draw."""
    if not settings.get("update_check"):
        return False
    from . import state as state_mod
    cached = state_mod.read_latest()
    if not cached or not cached[0]:
        return False
    return _parts(cached[0]) > _parts(current)
