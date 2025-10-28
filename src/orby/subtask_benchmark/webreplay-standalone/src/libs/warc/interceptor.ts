import { BrowserContext } from 'playwright';
import { extensionId } from '../../constants';
import { findMatchingResponse } from './warc-record';
import { initBrowserState } from './auth';
import { logger } from '../logger';
import { readWarcData } from './wacz';
import path from 'path';

export async function intercept(
  browserContext: BrowserContext,
  warcFilePath: string,
) {
  if (!warcFilePath) {
    throw new Error('warcFilePath is required');
  }
  
  // Log the absolute paths to help with debugging
  const absoluteWarcPath = path.resolve(warcFilePath);
  logger.info(`Loading WARC file: ${absoluteWarcPath}`);

  if (!absoluteWarcPath.endsWith('.wacz') && !absoluteWarcPath.endsWith('.warc') && !absoluteWarcPath.endsWith('.warc.gz')) {
    logger.error(`WARC file does not have a supported extension (.wacz, .warc, .warc.gz): ${absoluteWarcPath}`);
  }
  
  try {
    const [metadata, warcIndex] = await readWarcData(warcFilePath);
    
    // Log information about what we loaded
    logger.info(`WARC metadata main page URL: ${metadata.mainPageUrl || 'not set'}`);
    logger.info(`Number of indexed URLs: ${warcIndex.size}`);
    
    if (warcIndex.size === 0) {
      logger.error('No URLs were indexed from the WARC file. Make sure the file is valid and contains records.');
    }
    
    await initBrowserState(metadata, browserContext);
    
    // Debug - print the first few URLs from the index
    let counter = 0;
    for (const url of warcIndex.keys()) {
      if (counter < 5) {
        logger.info(`Indexed URL: ${url}`);
        counter++;
      } else {
        break;
      }
    }
  
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
  } catch (error) {
    logger.error(`Error setting up WARC interception: ${error}`);
    throw error;
  }
} 