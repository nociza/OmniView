const SAFE_URI_SCHEMES = new Set(['omv-moonlight', 'vnc', 'ssh', 'https']);

export function safeThumbnailUrl(value?: string | null): string | undefined {
  if (!value || value.length > 1_000_000) {
    return undefined;
  }
  return value.startsWith('data:image/') ? value : undefined;
}

export function safeLaunchUri(value?: string | null): string | undefined {
  if (!value || value.length > 512) {
    return undefined;
  }
  const match = value.match(/^([a-z0-9+.-]+):/i);
  if (!match) {
    return undefined;
  }
  return SAFE_URI_SCHEMES.has(match[1].toLowerCase()) ? value : undefined;
}
