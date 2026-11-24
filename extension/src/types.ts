import type { SiteId } from './generated/sites';

export type { SiteId };

/** Seeds needed to start an MCSR Ranked private-room style run. */
export interface SeedSet {
  overworld: string;
  nether: string;
  rng?: string;
}

/** Body POSTed to the local app's `/launch` endpoint. Must match the app's contract. */
export interface LaunchPayload {
  v: 1;
  site: SiteId;
  seeds: SeedSet;
  sourceUrl: string;
  label?: string;
}

/** Where a site adapter wants a Play button, and what it should launch. */
export interface InjectionTarget {
  /** Element the button is placed relative to. */
  anchor: HTMLElement;
  /** `append`: last child of `anchor`; `after`: next sibling of `anchor`. */
  placement: 'append' | 'after';
  seeds: SeedSet;
  label?: string;
  /** `full` (default) is a regular button; `compact` is a small icon button for dense lists. */
  size?: 'full' | 'compact';
}

/** One per supported site. `find` must be pure: it only reads the DOM. */
export interface SiteAdapter {
  id: SiteId;
  find(root: ParentNode): InjectionTarget[];
}

// ---------------------------------------------------------------------------
// Runtime messages (content script / popup -> background)

export type RuntimeMessage =
  | { type: 'launch'; payload: LaunchPayload }
  | { type: 'status' };

export type LaunchResult =
  | { kind: 'sent' }
  | { kind: 'offline' }
  | { kind: 'busy' }
  | { kind: 'unauthorized' }
  | { kind: 'error'; message: string };

export type StatusResult =
  | { kind: 'online'; version: string; running: boolean }
  | { kind: 'offline' }
  | { kind: 'unauthorized' }
  | { kind: 'error'; message: string };

/** Maps each message type to the response the background sends back. */
export interface MessageResponses {
  launch: LaunchResult;
  status: StatusResult;
}

export type ResponseFor<M extends RuntimeMessage> = MessageResponses[M['type']];

/** Persisted in `storage.local`. */
export interface Settings {
  port: number;
  token: string;
}
