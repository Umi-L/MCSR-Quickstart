import browser from 'webextension-polyfill';
import type { ResponseFor, RuntimeMessage } from './types';

/** Typed wrapper around `runtime.sendMessage`: the response type follows the message type. */
export async function sendToBackground<M extends RuntimeMessage>(message: M): Promise<ResponseFor<M>> {
  // The background is part of this extension and answers per `MessageResponses`.
  return (await browser.runtime.sendMessage(message)) as ResponseFor<M>;
}
