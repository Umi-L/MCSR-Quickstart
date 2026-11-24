// Content script entry: finds seeds on supported pages and adds Play buttons.

import './styles.css';
import { sendToBackground } from '../messaging';
import { adapterForUrl } from '../sites';
import { INJECTED_CLASS } from '../sites/util';
import type { InjectionTarget, LaunchPayload, LaunchResult, SiteAdapter } from '../types';

const MARKER = 'mcsrq';
const SCAN_DEBOUNCE_MS = 150;
const URL_POLL_MS = 500;
const RESULT_VISIBLE_MS = 2500;

type ButtonState = 'idle' | 'sending' | LaunchResult['kind'];

const STATE_TEXT: Record<ButtonState, string> = {
  idle: 'Play',
  sending: 'Sending…',
  sent: 'Launching',
  offline: 'App offline',
  busy: 'Busy',
  unauthorized: 'Bad token',
  error: 'Error',
};

const STATE_HINT: Record<ButtonState, string> = {
  idle: 'Play this seed in MCSR Ranked',
  sending: 'Sending to the Quickstart app…',
  sent: 'The Quickstart app is creating the world',
  offline: 'The Quickstart app is not running (or the port is wrong)',
  busy: 'The Quickstart app is already creating a world',
  unauthorized: 'Token rejected — set it in the extension popup',
  error: 'Something went wrong',
};

/** Anchor -> the button injected for it, so rescans are idempotent. */
const injected = new WeakMap<HTMLElement, HTMLButtonElement>();

function seedKey(target: InjectionTarget): string {
  const { overworld, nether, rng = '' } = target.seeds;
  return `${overworld}:${nether}:${rng}`;
}

function setState(button: HTMLButtonElement, state: ButtonState, detail?: string): void {
  button.dataset['state'] = state;
  button.disabled = state === 'sending';
  const text = button.querySelector<HTMLElement>('.mcsrq-text');
  if (text) text.textContent = STATE_TEXT[state];
  button.title = detail ? `${STATE_HINT[state]}: ${detail}` : STATE_HINT[state];
  button.setAttribute('aria-label', button.title);
}

function createButton(adapter: SiteAdapter, target: InjectionTarget): HTMLButtonElement {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `${INJECTED_CLASS} ${INJECTED_CLASS}--${target.size ?? 'full'}`;
  button.dataset['key'] = seedKey(target);

  const icon = document.createElement('span');
  icon.className = 'mcsrq-icon';
  icon.setAttribute('aria-hidden', 'true');
  button.append(icon);
  // Compact buttons carry no text nodes (the label lives in aria-label/title), so they don't
  // change the textContent of the host element they sit in.
  if (target.size !== 'compact') {
    const text = document.createElement('span');
    text.className = 'mcsrq-text';
    button.append(text);
  }
  setState(button, 'idle');

  let resetTimer: number | undefined;
  button.addEventListener('click', (event) => {
    // Keep the host page from reacting (row selection, copy-to-clipboard, …).
    event.preventDefault();
    event.stopPropagation();
    if (button.dataset['state'] === 'sending') return;

    window.clearTimeout(resetTimer);
    setState(button, 'sending');
    const payload: LaunchPayload = {
      v: 1,
      site: adapter.id,
      seeds: target.seeds,
      sourceUrl: location.href,
      ...(target.label ? { label: target.label } : {}),
    };
    sendToBackground({ type: 'launch', payload })
      .catch((err: unknown): LaunchResult => ({ kind: 'error', message: err instanceof Error ? err.message : String(err) }))
      .then((result) => {
        setState(button, result.kind, result.kind === 'error' ? result.message : undefined);
        resetTimer = window.setTimeout(() => setState(button, 'idle'), RESULT_VISIBLE_MS);
      });
  });

  return button;
}

function place(target: InjectionTarget, button: HTMLButtonElement): void {
  if (target.placement === 'append') target.anchor.append(button);
  else target.anchor.after(button);
}

function scan(adapter: SiteAdapter): void {
  for (const target of adapter.find(document)) {
    const key = seedKey(target);
    const existing = injected.get(target.anchor);
    if (existing?.isConnected && existing.dataset['key'] === key) continue;

    existing?.remove();
    const button = createButton(adapter, target);
    place(target, button);
    injected.set(target.anchor, button);
    target.anchor.dataset[MARKER] = key;
    if (target.size === 'compact') target.anchor.classList.add('mcsrq-host');
  }
}

function start(): void {
  let timer: number | undefined;
  const scheduleScan = (): void => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      // Re-resolve on every scan: SPA navigation can move between pages of the same site.
      const adapter = adapterForUrl(location.href);
      if (adapter) scan(adapter);
    }, SCAN_DEBOUNCE_MS);
  };

  new MutationObserver(scheduleScan).observe(document.body, { childList: true, subtree: true, characterData: true });

  // SPA route changes (pushState) are invisible to content scripts; poll the URL cheaply.
  let lastUrl = location.href;
  window.setInterval(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      scheduleScan();
    }
  }, URL_POLL_MS);
  window.addEventListener('popstate', scheduleScan);

  scheduleScan();
}

start();
