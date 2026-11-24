import type { InjectionTarget, SeedSet, SiteAdapter } from '../types';
import { cleanText, INJECTED_CLASS, parseSeed } from './util';

/**
 * gapcheck.gg match pages (`/m/<id>`): a `<section>` holds one `<button>` per seed.
 * Each button has a label (`Overworld / End`, `Nether`, `RNG`) and the seed in `span.font-mono`.
 */
export const gapcheck: SiteAdapter = {
  id: 'gapcheck',
  find(root) {
    if (!/^\/m\/[^/]+\/?$/.test(location.pathname)) return [];

    const targets: InjectionTarget[] = [];
    for (const section of root.querySelectorAll<HTMLElement>('section')) {
      const seeds = readSeeds(section);
      if (!seeds) continue;
      const label = cleanText(document.querySelector('h1')?.textContent);
      // The section's first child is its header row (description + "View match" link);
      // fall back to the section itself if that layout changes (ignoring our own button).
      const header = section.firstElementChild;
      const headerOk = header instanceof HTMLElement && !header.querySelector(`button:not(.${INJECTED_CLASS})`);
      targets.push({
        anchor: headerOk ? header : section,
        placement: 'append',
        seeds,
        ...(label ? { label } : {}),
      });
    }
    return targets;
  },
};

function readSeeds(section: HTMLElement): SeedSet | undefined {
  let overworld: string | undefined;
  let nether: string | undefined;
  let rng: string | undefined;

  for (const button of section.querySelectorAll('button')) {
    const seedEl = button.querySelector('span.font-mono');
    const seed = parseSeed(seedEl?.textContent);
    if (!seed || !seedEl) continue;
    const label = (button.textContent ?? '').replace(seedEl.textContent ?? '', '').toUpperCase();
    if (label.includes('OVERWORLD')) overworld = seed;
    else if (label.includes('NETHER')) nether = seed;
    else if (label.includes('RNG')) rng = seed;
  }

  if (!overworld || !nether) return undefined;
  return rng ? { overworld, nether, rng } : { overworld, nether };
}
