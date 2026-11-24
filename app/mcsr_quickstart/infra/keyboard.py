"""Synthetic keyboard input."""

from __future__ import annotations

from typing import Protocol

from ..game.sequences import Key


class KeySender(Protocol):
    def press(self, key: Key, *, shift: bool = False, ctrl: bool = False) -> None: ...

    def type_text(self, text: str) -> None: ...


class PynputKeySender:
    """Cross-platform key sender backed by pynput."""

    def __init__(self) -> None:
        from pynput import keyboard

        self._kb = keyboard
        self._controller = keyboard.Controller()
        special = keyboard.Key
        self._map: dict[Key, object] = {
            Key.ESCAPE: special.esc,
            Key.TAB: special.tab,
            Key.ENTER: special.enter,
            Key.SPACE: special.space,
            Key.BACKSPACE: special.backspace,
            Key.UP: special.up,
            Key.DOWN: special.down,
            Key.LEFT: special.left,
            Key.RIGHT: special.right,
            Key.A: "a",
        }

    def press(self, key: Key, *, shift: bool = False, ctrl: bool = False) -> None:
        modifiers = []
        if ctrl:
            modifiers.append(self._kb.Key.ctrl)
        if shift:
            modifiers.append(self._kb.Key.shift)
        for mod in modifiers:
            self._controller.press(mod)
        try:
            self._controller.tap(self._map[key])
        finally:
            for mod in reversed(modifiers):
                self._controller.release(mod)

    def type_text(self, text: str) -> None:
        self._controller.type(text)
