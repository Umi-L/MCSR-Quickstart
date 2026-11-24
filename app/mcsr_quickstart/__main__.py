"""Entry point: wires model, effects, infra and view together."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from .domain.sites import load_sites
from .game.monitor import GameMonitor
from .infra.config import ConfigStore
from .infra.keyboard import PynputKeySender
from .infra.window import create_focuser
from .mvi.effects import EffectHandler
from .mvi.state import AppState
from .mvi.store import Store
from .ui.icon import app_icon
from .ui.main_window import MainWindow, load_stylesheet
from .ui.tray import Tray


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="mcsr-quickstart")
    parser.add_argument("--dev", action="store_true", help="debug logging, local config dir")
    parser.add_argument("--config-dir", type=Path, help="override the settings directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        level=logging.DEBUG if args.dev else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    config_dir: Path | None = args.config_dir
    if config_dir is None and args.dev:
        config_dir = Path.cwd() / ".dev-config"
    config = ConfigStore(config_dir)
    settings = config.load()

    app = QApplication(sys.argv[:1])
    app.setApplicationName("MCSR Quickstart")
    app.setWindowIcon(app_icon())
    app.setStyleSheet(load_stylesheet())

    store = Store(AppState(settings=settings, sites=load_sites()))

    tray_available = QSystemTrayIcon.isSystemTrayAvailable()
    window = MainWindow(store, hide_on_close=tray_available)
    tray: Tray | None = Tray(store, window) if tray_available else None
    if tray is not None:
        tray.show()
        app.setQuitOnLastWindowClosed(False)

    def notify(title: str, message: str) -> None:
        if tray is not None:
            tray.notify(title, message)

    # The monitor needs the handler's callbacks and vice versa; bind via closures.
    handler: EffectHandler | None = None
    monitor = GameMonitor(
        create_focuser(),
        on_target=lambda t: handler.on_target(t) if handler else None,
        on_state=lambda s: handler.on_game_state(s) if handler else None,
    )
    handler = EffectHandler(store, config, PynputKeySender(), monitor, notify)
    store.set_effect_handler(handler)
    handler.start()

    if not (settings.start_in_tray and tray is not None):
        window.show()

    try:
        return app.exec()
    finally:
        handler.stop()


if __name__ == "__main__":
    raise SystemExit(main())
