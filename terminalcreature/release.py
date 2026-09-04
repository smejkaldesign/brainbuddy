"""Version discovery. The only code in terminalcreature that opens a socket.

A socket opens on exactly four paths, all consented: `update`, `update
--apply` (which also downloads the release it found), `doctor --check`, and,
only for users who set `update_check` on, the background refresh's once-a-day
`maybe_refresh_latest`. A pet that phoned home from the
statusline would be checking a few times a second and reading as spyware, so
the render path only ever reads the cache those three write. One request per
invocation, no retries; the daily check caches under a 24h stamp.
"""

import json

from . import __version__

PYPI_URL = "https://pypi.org/pypi/terminalcreature/json"
# the same tarball bootstrap.sh installs from, so `update --apply` and a fresh
# install land the identical tree
TARBALL_URL = "https://api.github.com/repos/smejkaldesign/terminalcreature/tarball/v%s"
TIMEOUT = 4.0
DOWNLOAD_TIMEOUT = 60.0


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
        return "terminalcreature isn't on pypi yet, so there's nothing to compare against. you're on %s." % current
    if status == "unreachable":
        return "couldn't reach pypi just now. you're on %s, try again when it's back." % current
    if _parts(latest) > _parts(current):
        return "terminalcreature %s is out, you're on %s; re-run your installer, pipx upgrade terminalcreature, or take the plugin update." % (
            latest, current)
    if _parts(latest) < _parts(current):
        return "you're on %s and pypi has %s, so you're ahead of the release." % (current, latest)
    return "terminalcreature %s is the latest. nothing to do." % current


def remember(status, latest):
    """Cache what a check found. The chip reads this, so a manual check and
    the statusline agree. A cache that can't be written is not worth failing
    the answer over."""
    try:
        from . import state as state_mod
        state_mod.write_latest(latest if status == "ok" else "")
    except Exception:
        pass


def check():
    status, latest = fetch_latest()
    remember(status, latest)
    return status_line(status, latest)


def fetch_tarball(version, dest, url_template=TARBALL_URL, timeout=DOWNLOAD_TIMEOUT):
    """Download one release tarball to dest. Returns True or False, never raises."""
    try:
        import urllib.request

        with urllib.request.urlopen(url_template % version, timeout=timeout) as response, open(dest, "wb") as out:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                out.write(chunk)
        return True
    except Exception:
        return False


def apply(version, state_dir=None, fetch=fetch_tarball, run=None):
    """Install `version` over this one by running its own installer.

    Downloads the release tarball, unpacks it, and runs the install.sh inside,
    which is what bootstrap.sh does on a fresh machine. The installer keeps
    the roster, the wrapped command and the settings; only the library and
    shim change. Under a plugin install the commands are the plugin's, so the
    installer is told to leave them alone. Returns (ok, message).
    """
    import os
    import shutil
    import subprocess
    import tarfile
    import tempfile

    if state_dir is None:
        from . import state as state_mod
        state_dir = state_mod.STATE_DIR
    run = run or subprocess.run
    work = tempfile.mkdtemp(prefix="terminalcreature-update-")
    try:
        tarball = os.path.join(work, "release.tar.gz")
        if not fetch(version, tarball):
            return False, "github has %s on pypi's word but wouldn't hand over the tarball. check your connection, then run this again." % version
        try:
            with tarfile.open(tarball) as tar:
                try:
                    tar.extractall(work, filter="data")
                except TypeError:
                    # python < 3.12 has no extraction filter
                    tar.extractall(work)
        except (tarfile.TarError, OSError):
            return False, "the %s download didn't unpack as a tarball. try again; if it repeats, re-run the installer from the website." % version
        installers = [os.path.join(work, d, "install.sh") for d in os.listdir(work)
                      if os.path.isfile(os.path.join(work, d, "install.sh"))]
        if len(installers) != 1:
            return False, "the %s tarball has no install.sh where one is expected, so nothing was changed." % version
        cmd = ["bash", installers[0]]
        if os.path.isfile(os.path.join(state_dir, "plugin-root")):
            cmd.append("--no-commands")
        result = run(cmd, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            return False, "the %s installer exited %d. whatever it printed above is the reason; the old version is still wired." % (
                version, result.returncode)
        return True, "terminalcreature %s is installed. the statusline picks it up on its next redraw." % version
    finally:
        shutil.rmtree(work, ignore_errors=True)


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
