import { matchesPattern } from '../core/match';
import { SITES } from '../generated/sites';
import type { SiteAdapter, SiteId } from '../types';
import { gapcheck } from './gapcheck';
import { seedbank } from './seedbank';

/**
 * Every id in shared/sites.json must have an adapter here — `Record<SiteId, …>` makes a
 * missing one a type error.
 */
export const ADAPTERS: Record<SiteId, SiteAdapter> = {
  gapcheck,
  seedbank,
};

/** Returns the adapter whose sites.json match patterns cover `url`. */
export function adapterForUrl(url: string): SiteAdapter | undefined {
  const site = SITES.find((s) => s.matches.some((pattern) => matchesPattern(pattern, url)));
  return site ? ADAPTERS[site.id] : undefined;
}
