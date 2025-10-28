import { program } from 'commander';
import { serve } from './commands/serve';
import { LoggingFlag, logger } from './libs/logger';
import path from 'path';
import { getBrowseContext } from './env/setup';
import { glob } from 'glob';
import os from 'os';

/**
 * Parse JSON browser arguments into Chrome command line flags.
 * 
 * @param jsonArg JSON string containing browser arguments
 * @returns Array of Chrome command line arguments or undefined if input is empty
 */
function parseBrowserArgs(jsonArg?: string): string[] | undefined {
  if (!jsonArg) {
    return undefined;
  }

  try {
    const browserArgObj = JSON.parse(jsonArg);
    const browserArgs: string[] = [];
    
    // Convert JSON object to Chrome argument format
    for (const [key, value] of Object.entries(browserArgObj)) {
      // Use single dash for single-letter flags, double dash for multi-letter flags
      const prefix = key.length === 1 ? '-' : '--';
      
      if (value === true) {
        // For boolean true values, just add the flag
        browserArgs.push(`${prefix}${key}`);
      } else if (value === false) {
        // Skip false values
        continue;
      } else {
        // For string/number values, add key=value
        browserArgs.push(`${prefix}${key}=${value}`);
      }
    }
    
    if (browserArgs.length > 0) {
      logger.info(`Using browser arguments: ${browserArgs.join(' ')}`);
    }
    
    return browserArgs;
  } catch (error) {
    logger.error(`Failed to parse browser arguments JSON: ${error}`);
    throw new Error(`Invalid browser arguments JSON: ${error}`);
  }
}

program
  .name('webreplay-standalone')
  .description('CLI to serve webreplay archives')
  .version('1.0.0');

program
  .command('serve')
  .argument('[warc_file]')
  .argument('[start_url]')
  .description('Serve a replay file containing WARC archives')
  .option(
    '-l, --logging <flag...>',
    'configure debug output to console, available flags: forward_browser_console, warc',
  )
  .option(
    '-d, --debugging-port <number>',
    'expose a debugging port that allows Python Playwright to directly connect to the browser instance',
    '9222'
  )
  .option(
    '--headless',
    'run browser in headless mode',
    false
  )
  .option(
    '--chrome-path <path>',
    'specify custom Chrome executable path',
  )
  .option(
    '--debug',
    'enable additional debug output',
    false
  )
  .option(
    '--browser-arg <json>',
    'JSON string of Chrome browser arguments as key-value pairs. Example: \'{"load-extension":"/path/to/extension","disable-web-security":true,"v":true}\'',
  )
  .option(
    '--width <width>',
    'set browser window width in pixels',
    (width) => parseInt(width, 10)
  )
  .option(
    '--height <height>',
    'set browser window height in pixels',
    (height) => parseInt(height, 10)
  )
  .option(
    '--timestamp <timestamp>',
    'override the current date/time in the browser context with a fixed timestamp. The timestamp is in milliseconds since Unix epoch (JS Date.now() format).',
    (timestamp: string) => {
      return parseInt(timestamp, 10);
    }
  )
  .option(
    '--task-id <taskId>',
    'task ID for online task detection and user data directory management'
  )
  .action(async (warc_file, start_url, options: { 
    logging?: LoggingFlag[], 
    debuggingPort?: string, 
    headless?: boolean,
    chromePath?: string,
    debug?: boolean,
    browserArg?: string,
    width?: number,
    height?: number,
    timestamp?: number,
    taskId?: string
  }) => {
    // Set environment variables based on options
    if (options.headless) {
      process.env.HEADLESS = 'true';
    }
    if (options.chromePath) {
      process.env.CHROME_PATH = options.chromePath;
    }
    if (options.debug) {
      logger.isForwardingBrowserConsole = true;
      logger.enableWARCLogging = true;
    }

    if (options.logging?.includes(LoggingFlag.FORWARD_BROWSER_CONSOLE)) {
      logger.info('Forwarding browser console');
      logger.isForwardingBrowserConsole = true;
    }
    if (options.logging?.includes(LoggingFlag.WARC)) {
      logger.info('Logging WARC');
      logger.enableWARCLogging = true;
    }

    // Parse browser arguments
    let browserArgs: string[] | undefined;
    try {
      browserArgs = parseBrowserArgs(options.browserArg);
    } catch (error) {
      // Error already logged in parseBrowserArgs
      process.exit(1);
    }

    const debuggingPort = options.debuggingPort ? parseInt(options.debuggingPort, 10) : 9222;
    
    // Create viewport object if dimensions are provided
    const viewport = options.width && options.height 
      ? { width: options.width, height: options.height }
      : undefined;
    
    if (viewport) {
      logger.info(`Setting viewport size to ${viewport.width}x${viewport.height}`);
    }
    
    // Print system information for debugging
    logger.info(`OS: ${os.type()} ${os.release()}`);
    logger.info(`Node version: ${process.version}`);
    logger.info(`Headless mode: ${options.headless ? 'enabled' : 'disabled'}`);
    
    logger.info(`Will expose browser debugging on port ${debuggingPort}`);
    logger.info('Python Playwright connection command:');
    logger.info(`from playwright.sync_api import sync_playwright\nwith sync_playwright() as p:\n    browser = p.chromium.connect_over_cdp('http://localhost:${debuggingPort}')`);
    
    // For server command, we don't care about the mode
    try {
      const { browserContext, userDataDir } = await getBrowseContext(warc_file, debuggingPort, browserArgs, viewport, options.taskId);
      await serve(warc_file, start_url, browserContext, options.timestamp).catch(logger.error);
    } catch (error) {
      logger.error(`Failed to start browser: ${error}`);
      process.exit(1);
    }
  });

program.parse();
