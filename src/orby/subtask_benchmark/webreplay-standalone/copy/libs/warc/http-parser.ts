import { logger } from '../logger';

export function payload2String(
  payload: Uint8Array | null,
  contentType: string,
): string {
  if (
    contentType.includes('application/x-www-form-urlencoded') ||
    contentType.includes('application/json') ||
    contentType.includes('application/javascript') ||
    contentType.includes('application/xml') ||
    contentType.includes('text/html') ||
    contentType.includes('text/plain')
  ) {
    return new TextDecoder().decode(payload || undefined);
  }
  if (contentType.includes('application/x-json-stream')) {
    return payload?.toString() || '';
  }
  if (!process.env.CI) {
    logger.warn(`Unsupported content type: ${contentType}`);
  }
  return '';
}
