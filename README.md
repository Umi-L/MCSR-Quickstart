# MCSR Quickstart

Click **▶ Play** next to a seed on [GapCheck](https://gapcheck.gg/) or the
[Ranked SeedBank](https://awesomedev.site/ranked-seedbank/). The companion app then focuses
your MCSR Ranked client, works out where you are in the game, gets back to the title
screen, and creates a world with that seed set. It uses the keyboard only.

```
browser page ──(content script finds seeds, injects ▶ Play)──► extension background
      └──── POST 127.0.0.1:47615/launch  (X-Quickstart-Token) ────► Python app
                                                                     ├─ reads wpstateout.txt
                                                                     ├─ focuses Minecraft
                                                                     └─ sends key sequences
```

## Requirements
- Python 3.11+ and Node.js 18+.
- MCSR Ranked (1.16.1) with the **State Output** mod, which writes `wpstateout.txt` in the
  instance's `.minecraft` folder.
- On macOS, give your terminal or the app Accessibility permission.
- On Linux, you need X11 and `xdotool`. Wayland is not supported.

## Quick start (development)
```powershell
python scripts/dev.py
```
This creates `app/.venv`, installs everything, runs `npm install`, then:
- runs the app with debug logging. Settings go in `./.dev-config`, and the app restarts when
  you save a `.py` file.
- watches and rebuilds the extension into `extension/dist/chrome` and `extension/dist/firefox`.

Use `python scripts/dev.py app` or `python scripts/dev.py ext` to run only one of them.

Then load the extension:
- **Chrome:** open `chrome://extensions`, turn on Developer mode, choose *Load unpacked*, and
  pick `extension/dist/chrome`.
- **Firefox:** open `about:debugging#/runtime/this-firefox`, choose *Load Temporary Add-on*, and
  pick `extension/dist/firefox/manifest.json`.

Pair them: copy the port and token from the app's **Settings** page into the extension popup.

## Production build
```powershell
python scripts/build.py all --check
```
- `--check` runs `ruff`, `mypy --strict`, `pytest` and `tsc --noEmit` first.
- `ext` creates a minified build and zips it into `release/` for the Chrome Web Store and
  Firefox AMO.
- `app` creates a standalone PyInstaller build in `release/app-<platform>/`.

## How a run works
1. The app finds the Minecraft window using the *Window title regex* setting (default
   `^Minecraft`). It locates the instance folder from that Java process: the `--gameDir`
   argument or the working directory. You can override the folder in Settings.
2. It focuses the window.
3. It repeatedly reads `wpstateout.txt` and decides what to press using
   `app/mcsr_quickstart/game/navigator.py`:

   | State | Action |
   |---|---|
   | menu open in world | Esc |
   | in world | Esc (pause) |
   | paused | Save and Quit sequence |
   | generating / previewing / waiting | wait |
   | title | continue |

   After each input it waits for the state to change, so it never presses blindly.
4. From the title screen it runs `CREATE_WORLD` and checks that world generation starts.

Press **F8** (configurable) at any time to abort a run.

### Calibrating the key sequences
Every hardcoded input is in
[`app/mcsr_quickstart/game/sequences.py`](app/mcsr_quickstart/game/sequences.py):
`SAVE_AND_QUIT` and `CREATE_WORLD`. They are typed `Step` tuples (`Press`, `Type(SeedField.X)`
and `Wait`). Adjust the Tab counts marked `TODO: calibrate` to match your client's
Create World screen, then turn auto-run off in Settings and test with the **Run** button.

## Adding a site
1. Add an entry to [`shared/sites.json`](shared/sites.json) with `id`, `name` and URL
   `matches`. Both the extension manifest and the app read this file.
2. Write `extension/src/sites/<id>.ts` implementing `SiteAdapter`. `find(root)` returns the
   elements to put a button next to, along with their `SeedSet`.
3. Register the adapter in `extension/src/sites/index.ts`. `SiteId` is a union type, so the
   build fails until the adapter is registered.

## Project layout
```
shared/sites.json          supported sites (single source of truth)
extension/                 TypeScript MV3 extension (Chrome + Firefox)
app/mcsr_quickstart/
  domain/                  SeedSet, payload protocol, site list
  game/                    state parsing, navigator, sequences, runner, instance discovery
  mvi/                     state (model), intents, pure reducer, Qt store, effect handlers
  infra/                   localhost bridge, keyboard, window focus, config, abort hotkey
  ui/                      PySide6 view: dashboard, settings, tray
scripts/                   dev.py / build.py
```

**Architecture (MVI):** views only dispatch intents. `reduce(state, intent)` is pure and
returns the new state plus a list of effects. The effect handlers are the only code that
touches the outside world: the run thread, the server, config and notifications. Their
results come back into the store as further intents.
