import browser from 'webextension-polyfill';
import type { Settings } from './types';

export const DEFAULT_SETTINGS: Readonly<Settings> = { port: 47615, token: '' };

export function isValidPort(port: number): boolean {
  return Number.isInteger(port) && port >= 1 && port <= 65535;
}

export async function loadSettings(): Promise<Settings> {
  const stored = await browser.storage.local.get(['port', 'token']);
  const port = typeof stored['port'] === 'number' && isValidPort(stored['port']) ? stored['port'] : DEFAULT_SETTINGS.port;
  const token = typeof stored['token'] === 'string' ? stored['token'] : DEFAULT_SETTINGS.token;
  return { port, token };
}

export async function saveSettings(settings: Settings): Promise<void> {
  if (!isValidPort(settings.port)) throw new Error(`Invalid port: ${settings.port}`);
  await browser.storage.local.set({ port: settings.port, token: settings.token.trim() });
}
