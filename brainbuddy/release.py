"""Version discovery. The only code in brainbuddy that opens a socket.

Nothing imports this unless the user asked: `update`, or `doctor --check`. A pet
that phoned home from the statusline would be checking for updates a few times a
second and reading as spyware while it did it, so the check is explicit or it
doesn't happen. One request per invocation, no retries, no caching.
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
    import urllib.error  # kept off module import, so `from . import release` stays cheap
    import urllib.request

    try:
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
        return "brainbuddy %s is out, you're on %s; re-run your installer (or pipx upgrade brainbuddy)." % (
            latest, current)
    if _parts(latest) < _parts(current):
        return "you're on %s and pypi has %s, so you're ahead of the release." % (current, latest)
    return "brainbuddy %s is the latest. nothing to do." % current


def check():
    return status_line(*fetch_latest())
