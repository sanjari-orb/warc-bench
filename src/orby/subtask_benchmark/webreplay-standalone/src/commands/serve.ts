import { setupEnv } from '../env/setup';
import { BrowserContext } from 'playwright';
import { Controller } from '../libs/controller/controller';
import { logger } from '../libs/logger';

/**
 * Serves a replay file and sets up a browser instance for CDP connection.
 * 
 * @param warcFilePath Path to the WARC file
 * @param startUrl Starting URL for playback
 * @param browserContext Playwright browser context
 * @param timestamp Optional timestamp to override the current date/time in the browser context
 * @returns void
 */
export async function serve(
  warcFilePath: string,
  startUrl: string,
  browserContext: BrowserContext,
  timestamp?: number,
) {
  await setupEnv({
    warcFilePath,
    browserContext,
    timestamp,
    hook: async () => {
      const page = await browserContext.newPage();
      const controller = new Controller(browserContext, page, 0);
      await controller.goto(startUrl);
    },
  });
  
  logger.info('Browser instance ready for CDP connection');
} 