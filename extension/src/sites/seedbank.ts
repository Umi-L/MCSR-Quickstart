import type { InjectionTarget, SiteAdapter } from '../types';
import { parseSeed } from './util';

/**
 * Ranked SeedBank: search results are `.data-list > .data-row` (a fixed-width grid), each with
 * `p.ow-seed` and `p.nether-seed`. The row grid has no spare column, so a compact button goes
 * inside the nether-seed cell, which has room to the right of the (shorter) nether seed.
 * Rows are re-rendered on every search; the injector handles that.
 */
export const seedbank: SiteAdapter = {
  id: 'seedbank',
  find(root) {
    const targets: InjectionTarget[] = [];
    for (const row of root.querySelectorAll<HTMLElement>('.data-list > .data-row')) {
      const netherCell = row.querySelector<HTMLElement>('p.nether-seed');
      const overworld = parseSeed(row.querySelector('p.ow-seed')?.textContent);
      const nether = parseSeed(netherCell?.textContent);
      if (!overworld || !nether || !netherCell) continue;
      targets.push({ anchor: netherCell, placement: 'append', seeds: { overworld, nether }, size: 'compact' });
    }
    return targets;
  },
};
