"""Development runner.

    python scripts/dev.py app   # run the app with debug logging, restart on .py changes
    python scripts/dev.py ext   # esbuild watch -> extension/dist/{chrome,firefox}
    python scripts/dev.py all   # both (default)
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from _common import APP, EXT, ensure_node_modules, ensure_venv, npm


def start_ext() -> subprocess.Popen[bytes]:
    ensure_node_modules()
    return subprocess.Popen([npm(), "run", "dev"], cwd=EXT)


def run_app_with_reload() -> int:
    python = ensure_venv()
    # watchfiles restarts the process whenever a file in the package changes.
    cmd = [
        str(python), "-m", "watchfiles", "--filter", "python",
        f"{python} -m mcsr_quickstart --dev", "mcsr_quickstart",
    ]
    return subprocess.call(cmd, cwd=APP)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("target", nargs="?", choices=["app", "ext", "all"], default="all")
    target = parser.parse_args().target

    ext_proc = start_ext() if target in ("ext", "all") else None
    try:
        if target in ("app", "all"):
            return run_app_with_reload()
        assert ext_proc is not None
        return ext_proc.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        if ext_proc is not None and ext_proc.poll() is None:
            ext_proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
