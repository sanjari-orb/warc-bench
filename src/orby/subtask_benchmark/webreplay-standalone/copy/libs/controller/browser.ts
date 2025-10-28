import { BrowserContext, chromium, ConsoleMessage, Page } from 'playwright';
import fs from 'fs';
import path from 'path';
import { extensionId } from '../../constants';
import { logger } from '../logger';
import { sleep } from 'extension/src/utils/timer';

const headless = false;

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
}

export async function launchBrowser(
  extensionDist: string,
  options?: BrowserLaunchOptions,
) {
  const userDataDir = options?.userDataDir || '';
  let browserContext: BrowserContext;
  // Delete the service worker folder
  await clearServiceWorkerFolder(userDataDir);
  let maxRetries = 3;
  while (maxRetries--) {
    try {
      if (browserContext!) {
        await browserContext.close();
      }
      // extension only works with a persistent context
      browserContext = await chromium.launchPersistentContext(userDataDir, {
        args: [
          `--disable-extensions-except=${extensionDist}`,
          `--load-extension=${extensionDist}`,
          headless ? '--headless=new' : '',
        ],
        headless,
        downloadsPath: options?.downloadsPath,
      });

      if (options?.waitForWorker) {
        // Can't capture worker service sometimes, so we need to retry
        let [worker] = browserContext.serviceWorkers();
        if (!worker) {
          worker = await browserContext.waitForEvent('serviceworker', {
            timeout: 15 * 1000,
          });
        }
        logger.info('Waiting for service worker activation...');
        await sleep(1000);
        await worker.evaluate(async () => {
          // @ts-expect-error - TS doesn't know about the registration property
          const registration = self.registration;

          if (registration.active) {
            return;
          }

          await new Promise<void>((resolve) => {
            if (registration.installing) {
              registration.installing.addEventListener(
                'statechange',
                (e: any) => {
                  if (e.target.state === 'activated') {
                    resolve();
                  }
                },
              );
            } else if (registration.waiting) {
              registration.waiting.addEventListener('statechange', (e: any) => {
                if (e.target.state === 'activated') {
                  resolve();
                }
              });
            }
          });
        });

        logger.info('Service worker activated');
      }
      await closeExtensionTab(browserContext);
      break;
    } catch (e) {
      logger.error(
        `Failed to launch browser context. Error: ${e}. Retrying ${maxRetries + 1} of ${maxRetries}`,
      );
      await sleep(1000);
    }
  }
  if (logger.isForwardingBrowserConsole) {
    browserContext!.on('backgroundpage', (page) => {
      page.on('console', (msg) => {
        forwardConsoleLogs(msg);
      });
    });
    browserContext!.on('page', (page) => {
      page.on('console', (msg) => {
        forwardConsoleLogs(msg);
      });
    });
  }
  return browserContext!;
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
  if (msg.type() === 'debug') {
    // drop debug info.
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

export async function clearIndexDB(page: Page) {
  return page.evaluate(async () => {
    const dbs = await window.indexedDB.databases();
    dbs.forEach((db) => {
      window.indexedDB.deleteDatabase(db.name || '');
    });
  });
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

async function loginOrby(
  page: Page,
  username: string = 'testing@gmail.com',
  password: string = 'testing',
) {
  await page.locator('input[name="email"]').fill(username);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.locator('input[name="password"]').fill(password!);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.waitForTimeout(5 * 1000);
  await page.waitForURL(new RegExp('dashboard'));
}
