import { BrowserContext } from 'playwright';
import { closeExtensionTab, launchBrowser } from '../libs/controller/browser';
import { replaysPath } from '../constants';
import { intercept } from '../libs/warc/interceptor';
import path from 'path';
import fs from 'fs';
import os from 'os';
import { logger } from '../libs/logger';
import { LCGGenerator, SEED } from './overrides/generator';
import { getRandomValues, randomUUID } from './overrides/crypto';
import { random } from './overrides/math';
import { createFixedDateConstructor } from './overrides/date';

interface SetupEnvOptions {
  warcFilePath: string;
  browserContext: BrowserContext;
  timestamp?: number;
  hook: () => Promise<void>;
}

/**
 * Set up Playwright context/page according to the Replay.env specification.
 */
export async function setupEnv({
  warcFilePath,
  browserContext,
  timestamp,
  hook,
}: SetupEnvOptions): Promise<void> {
  // If timestamp is provided, use it to override the date
  let dateOverrideScript = '';
  if (timestamp) {
    logger.info(
      `Using recorded timestamp: ${new Date(timestamp).toISOString()} (${timestamp})`,
    );
    // Ensure all time-related methods are consistent
    dateOverrideScript = createFixedDateConstructor(timestamp);
  }

  browserContext.addInitScript({
    content: `
      ${LCGGenerator.toString()}
      const SEED = ${SEED};
      const randomValuesGenerator = new LCGGenerator(SEED);
      const uuidGenerator = new LCGGenerator(SEED);
      const randomGenerator = new LCGGenerator(SEED);
      window.crypto.getRandomValues = ${getRandomValues.toString()};
      window.crypto.randomUUID = ${randomUUID.toString()};
      window.Math.random = ${random.toString()};
      // Apply comprehensive Date overrides to handle all date-related functionality
      ${dateOverrideScript}
    `,
  });
  await closeExtensionTab(browserContext);
  if (warcFilePath) {
    // serve from WARC archive
    await intercept(browserContext, warcFilePath);
  } else {
    throw new Error('warcFilePath is required');
  }

  await hook();
}

/**
 * Create a browser context for replay
 * 
 * @param warcFilePath Path to replay file
 * @param debuggingPort Optional port to expose for debugging (allows external Python clients)
 * @param browserArgs Additional browser arguments to pass to Chrome
 * @param viewport Optional viewport dimensions for the browser window
 * @param taskId Optional task ID to determine if this is an online task requiring temporary user data directory
 * @returns Object containing browser context and user data directory path for cleanup
 */
export async function getBrowseContext(
  warcFilePath: string,
  debuggingPort?: number,
  browserArgs?: string[],
  viewport?: { width: number; height: number },
  taskId?: string,
): Promise<{ browserContext: BrowserContext; userDataDir: string }> {
  const application = path.basename(path.dirname(warcFilePath));
  let userDataDir: string;
  
  // Check if this is an online task that needs a temporary user data directory
  const isOnlineTask = taskId && taskId.startsWith('online');
  
  if (isOnlineTask) {
    // Create a unique temporary directory for online tasks
    const tempDir = os.tmpdir();
    const uniqueId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    userDataDir = path.join(tempDir, 'webreplay-userdata', `${taskId}-${uniqueId}`);
    
    // Create the directory
    fs.mkdirSync(userDataDir, { recursive: true });
    logger.info(`Created temporary user data directory for online task: ${userDataDir}`);
  } else {
    // Use the existing logic for non-online tasks
    userDataDir = path.join(replaysPath, '.user_data_dir', application);
  }
  
  // If debugging port is provided, log it for easier connection
  if (debuggingPort) {
    logger.info(`Starting browser with debugging port ${debuggingPort}`);
    logger.info(`Python can connect using: playwright.chromium.connect_over_cdp('http://localhost:${debuggingPort}')`);
  }
  
  // If viewport is provided, log the dimensions
  if (viewport) {
    logger.info(`Setting browser viewport to ${viewport.width}x${viewport.height}`);
  }
  
  const browserContext = await launchBrowser({
    userDataDir,
    waitForWorker: true,
    debuggingPort,
    browserArgs,
    viewport,
  });
  
  return { browserContext, userDataDir };
} 

