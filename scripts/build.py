"""Production build.

    python scripts/build.py check      # tsc, mypy --strict, ruff, pytest only
    python scripts/build.py ext        # minified extension + store zips in release/
    python scripts/build.py app        # PyInstaller build in release/app-<platform>/
    python scripts/build.py all        # everything (default)
    add --check to run the checks before building
"""

from __future__ import annotations

import argparse
import shutil
import sys

from _common import APP, EXT, RELEASE, ROOT, ensure_node_modules, ensure_venv, npm, run


def check() -> None:
    python = ensure_venv()
    run([python, "-m", "ruff", "check", ".", ROOT / "scripts"], APP)
    run([python, "-m", "mypy", "mcsr_quickstart", "tests", ROOT / "scripts"], APP)
    run([python, "-m", "pytest", "-q"], APP)
    if EXT.exists():
        ensure_node_modules()
        run([npm(), "run", "typecheck"], EXT)


def build_ext() -> None:
    ensure_node_modules()
    RELEASE.mkdir(exist_ok=True)
    # `package` = minified build + zips of dist/chrome and dist/firefox into release/.
    run([npm(), "run", "package"], EXT)


def build_app() -> None:
    python = ensure_venv()
    platform_name = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
    dist = RELEASE / f"app-{platform_name}"
    work = ROOT / "build" / "pyinstaller"
    shutil.rmtree(dist, ignore_errors=True)
    sep = ";" if sys.platform == "win32" else ":"
    run(
        [
            python, "-m", "PyInstaller",
            "--noconfirm", "--clean", "--windowed",
            "--name", "MCSR Quickstart",
            "--distpath", dist, "--workpath", work, "--specpath", work,
            "--add-data", f"{ROOT / 'shared' / 'sites.json'}{sep}shared",
            "--add-data", f"{APP / 'mcsr_quickstart' / 'ui' / 'theme.qss'}{sep}mcsr_quickstart/ui",
            "--collect-submodules", "pynput",
            APP / "launcher.py",
        ],
        APP,
    )
    print(f"\nApp built into {dist}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("target", nargs="?", choices=["check", "ext", "app", "all"], default="all")
    parser.add_argument("--check", action="store_true", help="run checks before building")
    args = parser.parse_args()

    if args.check or args.target == "check":
        check()
    if args.target in ("ext", "all"):
        build_ext()
    if args.target in ("app", "all"):
        build_app()
    return 0


if __name__ == "__main__":
    sys.exit(main())
