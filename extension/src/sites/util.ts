/** Class on every injected Play button; adapters can use it to ignore our own elements. */
export const INJECTED_CLASS = 'mcsrq-btn';

/** Minecraft seeds are signed 64-bit integers written in decimal. */
export function parseSeed(text: string | null | undefined): string | undefined {
  const value = text?.trim() ?? '';
  return /^-?\d{1,20}$/.test(value) ? value : undefined;
}

export function cleanText(text: string | null | undefined): string | undefined {
  const value = text?.replace(/\s+/g, ' ').trim() ?? '';
  return value.length > 0 ? value : undefined;
}
