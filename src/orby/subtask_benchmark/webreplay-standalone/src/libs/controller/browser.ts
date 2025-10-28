import { BrowserContext, chromium, ConsoleMessage, Page } from 'playwright';
import fs from 'fs';
import path from 'path';
import { extensionId } from '../../constants';
import { logger } from '../logger';

// Allow headless mode to be configurable
const isHeadless = () => process.env.HEADLESS === 'true';

interface BrowserLaunchOptions {
  /**
   * Specify the browser user data directory. If not specified, new empty
   * directory would be created and used.
   */
  userDataDir?: string;

  /**
   * Provides explicit downloads path, so we can read the downloaded files.
   */
  downloadsPath?: string;

  /**
   * Whether to wait for the worker service to be ready.
   */
  waitForWorker?: boolean;
  
  /**
   * The debugging port for the browser. When specified, allows external
   * clients (like Python Playwright) to connect to the same browser instance.
   */
  debuggingPort?: number;

  /**
   * Additional Chrome arguments to pass to the browser.
   * This can be used to load extensions, modify browser behavior, etc.
   */
  browserArgs?: string[];

  /**
   * Set the viewport size for the browser window.
   * Format: { width: number, height: number }
   */
  viewport?: { width: number; height: number };
}

export async function launchBrowser(
  // extensionDist: string,
  options?: BrowserLaunchOptions,
): Promise<BrowserContext> {
  const userDataDir = options?.userDataDir || '';
  let browserContext: BrowserContext | null = null;
  
  // Delete the service worker folder
  await clearServiceWorkerFolder(userDataDir);
  
  // Check if the extension path exists
  // if (!fs.existsSync(extensionDist)) {
  //   logger.error(`Extension directory not found: ${extensionDist}`);
  //   throw new Error(`Extension directory not found: ${extensionDist}`);
  // } else {
  //   logger.info(`Using extension from: ${extensionDist}`);
  // }
  
  // Check if user data directory exists or can be created
  if (userDataDir) {
    if (!fs.existsSync(userDataDir)) {
      try {
        fs.mkdirSync(userDataDir, { recursive: true });
        logger.info(`Created user data directory: ${userDataDir}`);
      } catch (error) {
        logger.error(`Failed to create user data directory: ${userDataDir}`);
        throw error;
      }
    } else {
      logger.info(`Using existing user data directory: ${userDataDir}`);
    }
  }
  
  let maxRetries = 3;
  while (maxRetries--) {
    try {
      if (browserContext) {
        await browserContext.close();
      }
      
      // Prepare args for browser launch
      const args = [
        // `--disable-extensions-except=${extensionDist}`,
        // `--load-extension=${extensionDist}`,
      ];

      // Add any custom browser arguments if provided
      if (options?.browserArgs && options.browserArgs.length > 0) {
        args.push(...options.browserArgs);
      }

      // If in headless mode, add appropriate flag
      if (isHeadless()) {
        args.push('--headless=new');
      }
      
      // If debugging port is specified, add it to the launch arguments
      if (options?.debuggingPort) {
        // Use a specific port for debugging
        args.push(`--remote-debugging-port=${options.debuggingPort}`);
        // Disable the pipe which can conflict with the port
        args.push('--no-remote-debugging-pipe');
        logger.info(`Browser will be accessible via debugging port: ${options.debuggingPort}`);
      }
      
      logger.info(`Launching browser with args: ${args.join(' ')}`);
      
      // A more reliable approach for browser launch
      const executablePath = process.env.CHROME_PATH || undefined;
      if (executablePath) {
        logger.info(`Using custom Chrome path: ${executablePath}`);
      }
      
      // Launch with more explicit timeout
      const launchOptions = {
        args,
        headless: isHeadless(),
        downloadsPath: options?.downloadsPath,
        timeout: 60000, // 1 minute timeout
        executablePath,
        viewport: options?.viewport,
        bypassCSP: true,
      };
      
      logger.info(`Launching browser with options: ${JSON.stringify(launchOptions, null, 2)}`);
      
      // extension only works with a persistent context
      browserContext = await chromium.launchPersistentContext(userDataDir, launchOptions);
      logger.info('Browser successfully launched');

      if (logger.isForwardingBrowserConsole) {
        browserContext.on('page', (page) => {
          page.on('console', (msg) => {
            forwardConsoleLogs(msg);
          });
        });
      }
      
      await closeExtensionTab(browserContext);
      break;
    } catch (e) {
      logger.error(
        `Failed to launch browser context. Error: ${e}. Retrying ${maxRetries + 1} more time(s).`,
      );
      
      // Add more diagnostic information
      if (e instanceof Error) {
        logger.error(`Error stack: ${e.stack}`);
      }
      
      // Delay between retries
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // On the last retry, try without the extension if that was the issue
      if (maxRetries === 0) {
        logger.warn('Last retry: attempting to launch without extension requirements');
        try {
          browserContext = await chromium.launchPersistentContext(userDataDir, {
            headless: isHeadless(),
            timeout: 60000,
            viewport: options?.viewport,
          });
          logger.info('Browser launched without extension - limited functionality will be available');
          break;
        } catch (lastError) {
          logger.error(`Final attempt failed: ${lastError}`);
          throw new Error(`Could not launch browser after multiple attempts: ${e}`);
        }
      }
    }
  }
  
  if (!browserContext) {
    throw new Error('Failed to launch browser after multiple attempts');
  }
  
  return browserContext;
}

export function forwardConsoleLogs(msg: ConsoleMessage) {
  if (msg.type() === 'error') {
    logger.error('Page console error: ', msg.text());
    return;
  }
  if (msg.type() === 'warning') {
    logger.warn('Page console warning: ', msg.text());
    return;
  }
  if (msg.type() === 'info') {
    logger.info('Page console log: ', msg.text());
    return;
  }
}

export async function closeExtensionTab(browserContext: BrowserContext) {
  try {
    const extensionLandingPage = await browserContext.waitForEvent('page', {
      timeout: 5 * 1000,
    });
    await extensionLandingPage.waitForLoadState('domcontentloaded');
    if (extensionLandingPage.url().includes(extensionId)) {
      await extensionLandingPage.close();
    }
  } catch (e) {
    // If no new page event, iterate through all pages in current context to find and close pages with matching URL
    const pages = browserContext.pages();
    for (const page of pages) {
      if (page.url().includes(extensionId)) {
        await page.close();
      }
    }
  }
}

export async function clearServiceWorkerFolder(userDataDir: string) {
  if (userDataDir === '') {
    return;
  }
  const serviceWorkerFolder = path.join(
    userDataDir,
    'Default',
    'Service Worker',
  );
  if (fs.existsSync(serviceWorkerFolder)) {
    fs.rmSync(serviceWorkerFolder, { recursive: true });
  }
} 