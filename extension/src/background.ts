// Background (service worker on Chrome, event page on Firefox): talks to the local app.

import browser from 'webextension-polyfill';
import { loadSettings } from './settings';
import type { LaunchPayload, LaunchResult, RuntimeMessage, StatusResult } from './types';

const REQUEST_TIMEOUT_MS = 4000;
const TOKEN_HEADER = 'X-Quickstart-Token';

type FetchOutcome = { ok: true; response: Response } | { ok: false; offline: true } | { ok: false; offline: false; message: string };

async function callApp(path: '/launch' | '/status', init: RequestInit = {}): Promise<FetchOutcome> {
  const { port, token } = await loadSettings();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const headers = new Headers(init.headers);
    headers.set(TOKEN_HEADER, token);
    const response = await fetch(`http://127.0.0.1:${port}${path}`, { ...init, headers, signal: controller.signal, cache: 'no-store' });
    return { ok: true, response };
  } catch (err: unknown) {
    // Connection refused and timeouts both mean "app not reachable".
    if (err instanceof TypeError || (err instanceof DOMException && err.name === 'AbortError')) return { ok: false, offline: true };
    return { ok: false, offline: false, message: err instanceof Error ? err.message : String(err) };
  } finally {
    clearTimeout(timer);
  }
}

async function launch(payload: LaunchPayload): Promise<LaunchResult> {
  const outcome = await callApp('/launch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!outcome.ok) return outcome.offline ? { kind: 'offline' } : { kind: 'error', message: outcome.message };

  const { status } = outcome.response;
  if (status === 202 || status === 200) return { kind: 'sent' };
  if (status === 401) return { kind: 'unauthorized' };
  if (status === 409) return { kind: 'busy' };
  if (status === 400) return { kind: 'error', message: 'The app rejected the seeds (400)' };
  return { kind: 'error', message: `Unexpected response ${status}` };
}

function isStatusBody(value: unknown): value is { ok: true; version: string; running: boolean } {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return v['ok'] === true && typeof v['version'] === 'string' && typeof v['running'] === 'boolean';
}

async function status(): Promise<StatusResult> {
  const outcome = await callApp('/status');
  if (!outcome.ok) return outcome.offline ? { kind: 'offline' } : { kind: 'error', message: outcome.message };

  const { response } = outcome;
  if (response.status === 401) return { kind: 'unauthorized' };
  if (!response.ok) return { kind: 'error', message: `Unexpected response ${response.status}` };
  try {
    const body: unknown = await response.json();
    if (!isStatusBody(body)) return { kind: 'error', message: 'Unrecognised /status response' };
    return { kind: 'online', version: body.version, running: body.running };
  } catch {
    return { kind: 'error', message: 'Invalid JSON from /status' };
  }
}

function isRuntimeMessage(value: unknown): value is RuntimeMessage {
  if (typeof value !== 'object' || value === null) return false;
  const type = (value as { type?: unknown }).type;
  if (type === 'status') return true;
  return type === 'launch' && typeof (value as { payload?: unknown }).payload === 'object';
}

browser.runtime.onMessage.addListener((message: unknown, sender: browser.Runtime.MessageSender) => {
  if (sender.id !== browser.runtime.id || !isRuntimeMessage(message)) return undefined;
  switch (message.type) {
    case 'launch':
      return launch(message.payload);
    case 'status':
      return status();
  }
});
