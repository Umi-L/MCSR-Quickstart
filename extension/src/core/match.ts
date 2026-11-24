/**
 * Minimal WebExtension match-pattern support (`<scheme>://<host>/<path>`, `*` wildcards),
 * enough to pick the adapter for the current page from `sites.json` patterns.
 */
export function matchesPattern(pattern: string, url: string): boolean {
  const m = /^(\*|https?):\/\/(\*|\*\.[^/*]+|[^/*]+)(\/.*)$/.exec(pattern);
  if (!m) return false;
  const [, scheme = '', host = '', path = ''] = m;

  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }

  const urlScheme = parsed.protocol.slice(0, -1);
  if (scheme === '*' ? urlScheme !== 'http' && urlScheme !== 'https' : urlScheme !== scheme) return false;

  if (host !== '*') {
    if (host.startsWith('*.')) {
      const base = host.slice(2);
      if (parsed.hostname !== base && !parsed.hostname.endsWith(`.${base}`)) return false;
    } else if (parsed.hostname !== host) {
      return false;
    }
  }

  const escaped = path.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*');
  return new RegExp(`^${escaped}$`).test(parsed.pathname + parsed.search);
}
