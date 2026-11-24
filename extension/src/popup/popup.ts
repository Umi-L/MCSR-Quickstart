import './popup.css';
import { SITES } from '../generated/sites';
import { sendToBackground } from '../messaging';
import { isValidPort, loadSettings, saveSettings } from '../settings';
import type { StatusResult } from '../types';

function el<T extends HTMLElement>(id: string, type: new () => T): T {
  const node = document.getElementById(id);
  if (!(node instanceof type)) throw new Error(`popup.html is missing #${id}`);
  return node;
}

const ui = {
  status: el('status', HTMLElement),
  statusTitle: el('status-title', HTMLElement),
  statusDetail: el('status-detail', HTMLElement),
  refresh: el('refresh', HTMLButtonElement),
  form: el('settings', HTMLFormElement),
  port: el('port', HTMLInputElement),
  token: el('token', HTMLInputElement),
  toggleToken: el('toggle-token', HTMLButtonElement),
  saveNote: el('save-note', HTMLElement),
  sites: el('sites', HTMLUListElement),
};

type StatusView = StatusResult['kind'] | 'checking';

function renderStatus(kind: StatusView, title: string, detail = ''): void {
  ui.status.dataset['kind'] = kind;
  ui.statusTitle.textContent = title;
  ui.statusDetail.textContent = detail;
}

async function refreshStatus(): Promise<void> {
  renderStatus('checking', 'Checking…');
  let result: StatusResult;
  try {
    result = await sendToBackground({ type: 'status' });
  } catch (err: unknown) {
    result = { kind: 'error', message: err instanceof Error ? err.message : String(err) };
  }
  switch (result.kind) {
    case 'online':
      renderStatus('online', 'Connected', `App v${result.version} · ${result.running ? 'creating a world' : 'ready'}`);
      break;
    case 'offline':
      renderStatus('offline', 'App not running', `Nothing answering on 127.0.0.1:${ui.port.value}`);
      break;
    case 'unauthorized':
      renderStatus('unauthorized', 'Token rejected', 'Copy the token from the Quickstart app');
      break;
    case 'error':
      renderStatus('error', 'Error', result.message);
      break;
  }
}

function renderSites(): void {
  for (const site of SITES) {
    const li = document.createElement('li');
    const name = document.createElement('span');
    name.textContent = site.name;
    const host = document.createElement('span');
    host.className = 'host';
    host.textContent = site.matches.map((m) => m.replace(/^https?:\/\//, '').replace(/\/\*$/, '')).join(', ');
    li.append(name, host);
    ui.sites.append(li);
  }
}

let noteTimer: number | undefined;
function showNote(text: string, isError = false): void {
  window.clearTimeout(noteTimer);
  ui.saveNote.textContent = text;
  ui.saveNote.classList.toggle('error', isError);
  noteTimer = window.setTimeout(() => (ui.saveNote.textContent = ''), 2500);
}

async function init(): Promise<void> {
  renderSites();

  const settings = await loadSettings();
  ui.port.value = String(settings.port);
  ui.token.value = settings.token;

  ui.form.addEventListener('submit', (event) => {
    event.preventDefault();
    const port = Number(ui.port.value);
    if (!isValidPort(port)) {
      showNote('Port must be 1–65535', true);
      return;
    }
    saveSettings({ port, token: ui.token.value })
      .then(() => {
        showNote('Saved');
        return refreshStatus();
      })
      .catch((err: unknown) => showNote(err instanceof Error ? err.message : String(err), true));
  });

  ui.toggleToken.addEventListener('click', () => {
    const show = ui.token.type === 'password';
    ui.token.type = show ? 'text' : 'password';
    ui.toggleToken.title = show ? 'Hide token' : 'Show token';
    ui.toggleToken.setAttribute('aria-label', ui.toggleToken.title);
  });

  ui.refresh.addEventListener('click', () => void refreshStatus());

  await refreshStatus();
}

void init();
