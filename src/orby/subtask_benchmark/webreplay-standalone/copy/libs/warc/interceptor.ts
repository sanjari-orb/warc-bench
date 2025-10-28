import { BrowserContext } from 'playwright';
import { extensionId } from '../../constants';
import { findMatchingResponse } from './warc-record';
import { initBrowserState } from './auth';
import { logger } from '../logger';
import { readWarcData } from './wacz';

export async function intercept(
  browserContext: BrowserContext,
  replayFile: string,
  warcFilePath: string,
) {
  if (!warcFilePath) {
    throw new Error('warcFilePath is required');
  }
  if (!replayFile) {
    throw new Error('replayFile is required');
  }
  const [metadata, warcIndex] = await readWarcData(warcFilePath);
  await initBrowserState(metadata, browserContext);
  await browserContext.route('**/*', async (route, request) => {
    // Skip orbot specific requests even landing page has been closed already.
    // In the future, if we involved some actions which need to send request, we still need it.
    // e.g: getForm, fillForm.
    // Note: there are compliant that service worker requests are not intercepted. Not verified yet.
    if (
      request.url().includes('orby.ai') ||
      request.url().includes(extensionId)
    ) {
      await route.continue();
      return;
    }

    // Skip analytics/logging requests
    if (
      request.url().includes('rum.browser-intake-datadoghq.com') ||
      request.url().includes('ingest.sentry.io')
    ) {
      if (logger.enableWARCLogging) {
        logger.info(`Skipped analytics/logging requests: ${request.url()}`);
      }
      await route.continue();
      return;
    }

    // Check if the navigation URL matches a specific pattern
    const response = findMatchingResponse(
      request,
      warcIndex,
      logger.enableWARCLogging,
    );
    if (!response) {
      // return 404 for all other requests
      if (logger.enableWARCLogging) {
        logger.warn(`Not Found: ${request.url()}, ${request.method()}`);
      }
      await route.fulfill({
        status: 404,
        body: JSON.stringify({
          error: 'UrlKey Not Found',
          originalUrl: request.url(),
        }),
        headers: {
          'content-type': 'text/html; charset=UTF-8',
        },
      });
      return;
    }
    if (logger.enableWARCLogging) {
      logger.success('Matched request', request.url(), request.method());
    }
    await route.fulfill(response);
  });
}
