# MCSR Quickstart — browser extension

Adds a **▶ Play** button next to seeds on MCSR seed sites. Clicking it sends the seeds to the
local Quickstart app (`app/`), which focuses MCSR Ranked and creates the world.

Chrome and Firefox, Manifest V3, TypeScript (strict), bundled with esbuild. No UI framework.

## Scripts

Run in `extension/`:

| Command | What it does |
| --- | --- |
| `npm install` | Install dependencies |
| `npm run dev` | Watch build with inline sourcemaps into `dist/chrome` and `dist/firefox` |
| `npm run build` | Minified production build into `dist/chrome` and `dist/firefox` |
| `npm run typecheck` | Regenerate `src/generated/sites.ts`, then `tsc --noEmit` |
| `npm run package` | Production build, then zip both targets to `../release/mcsr-quickstart-<target>-<version>.zip` |

The version in the manifests comes from `package.json`.

## Loading it

- **Chrome / Edge:** `chrome://extensions` → enable Developer mode → *Load unpacked* → `extension/dist/chrome`.
- **Firefox:** `about:debugging#/runtime/this-firefox` → *Load Temporary Add-on* → `extension/dist/firefox/manifest.json`.
  Firefox may treat host permissions as optional: if the Play button says *App offline* while the app is
  running, allow the extension's site access in `about:addons` → MCSR Quickstart → Permissions.

Then open the extension popup and paste the token shown by the Quickstart app (port defaults to `47615`).

## How it works

```
src/
  types.ts            Shared types: SeedSet, LaunchPayload, SiteAdapter, runtime messages
  generated/sites.ts  Generated from ../shared/sites.json (SITES + SiteId union) — don't edit
  sites/              One adapter per site + the registry (index.ts)
  core/inject.ts      Content script: picks the adapter, watches the DOM, renders buttons
  core/styles.css     Button styles (all classes prefixed `mcsrq-`)
  background.ts       Talks to http://127.0.0.1:<port> (/launch, /status)
  popup/              Status, port + token settings, supported sites
build.mjs             esbuild + manifest generation for both browsers
manifest.base.json    Manifest fields shared by both browsers
```

The content script asks the site's adapter for **injection targets** (an anchor element, where to put
the button, and the seeds). It rescans on DOM mutations (debounced) and SPA URL changes, and is
idempotent: each anchor gets at most one button, replaced only if its seeds change.

Clicking Play sends `{ type: 'launch', payload }` to the background, which POSTs to `/launch` with the
`X-Quickstart-Token` header. The button briefly shows the result: *Launching*, *App offline*, *Busy*
(a run is already in progress), *Bad token*, or *Error* (details in the tooltip).

## Adding a site

1. **Add it to `../shared/sites.json`** (shared with the app):

   ```json
   { "id": "mysite", "name": "My Site", "matches": ["https://mysite.example/*"] }
   ```

   `matches` uses WebExtension match patterns; they become the content-script matches and host
   permissions. `id` must be lowercase letters, digits or `_`.

2. **Write `src/sites/mysite.ts`** exporting a `SiteAdapter`:

   ```ts
   import type { InjectionTarget, SiteAdapter } from '../types';
   import { parseSeed } from './util';

   export const mysite: SiteAdapter = {
     id: 'mysite',
     find(root) {
       const targets: InjectionTarget[] = [];
       for (const card of root.querySelectorAll<HTMLElement>('.seed-card')) {
         const overworld = parseSeed(card.querySelector('.ow')?.textContent);
         const nether = parseSeed(card.querySelector('.nether')?.textContent);
         if (overworld && nether) {
           targets.push({ anchor: card, placement: 'append', seeds: { overworld, nether } });
         }
       }
       return targets;
     },
   };
   ```

   `find` only reads the DOM. Return one target per place a button should appear. Use
   `size: 'compact'` for a small icon button in dense lists (it is absolutely positioned at the right
   edge inside the anchor, so the anchor must have room for it). If your selectors could match the
   injected button itself, exclude it with `INJECTED_CLASS` from `./util`.

3. **Register it in `src/sites/index.ts`**: import it and add it to `ADAPTERS`.
   `ADAPTERS` is a `Record<SiteId, SiteAdapter>`, so `npm run typecheck` fails until every id in
   `sites.json` has an adapter.

4. `npm run build`, reload the extension, and check the page.
