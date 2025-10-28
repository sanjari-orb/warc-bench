import fs from 'fs';
import os from 'os';
import path from 'path';
import { archiveWebExtensionDist, archivesFolderPath } from '../constants';
import { launchBrowser } from '../libs/controller/browser';
import { logger } from '../libs/logger';

interface RecordOptions {
  fixDate?: boolean;
}

export async function record(
  archiveName: string,
  options: RecordOptions = { fixDate: true },
) {
  // create folder if not exists
  const archiveFolderPath = path.join(archivesFolderPath, archiveName);
  if (!fs.existsSync(archiveFolderPath)) {
    fs.mkdirSync(archiveFolderPath);
  }

  // provide custom downloads path when launch Playwright browsers, where we
  // can look up and save the generated WARC files. This is a workaround to deal
  // with the limitation that we cannot capture downloads from extension's popup
  // page in Playwright.
  let downloadsPath = '/tmp/playwright-downloads';
  if (os.platform() === 'win32') {
    downloadsPath = path.join(process.env.TEMP!, 'playwright-downloads');
  }

  const context = await launchBrowser(archiveWebExtensionDist, {
    downloadsPath,
    // webrecorder service worker won't be ready until it receives the first message
    waitForWorker: true,
  });

  // use the existing page instead of creating new ones.
  const page = context.pages()[0]!;

  // pin the extension to the toolbar to easily start/stop archiving
  await page.goto('chrome://extensions/?id=cooimhkfbdmjglbfeokfjmngjlahpmpp');
  await page.locator('#pin-to-toolbar #crToggle').click();

  // navigates to a blank page for user to start recording.
  await page.goto('https://orby.ai');

  // set the recording timestamp
  let timestamp: string | undefined;
  if (options.fixDate) {
    // set the recording timestamp
    timestamp = Date.now().toString();
    logger.info(
      `Recording timestamp: ${new Date(Number(timestamp)).toISOString()} (${timestamp})`,
    );

    // Set localStorage values for timestamp and fixed date flag
    await page.evaluate((timestamp) => {
      localStorage.setItem('__orby_recording_timestamp', timestamp);
    }, timestamp);
  }

  logger.info(`Please start record page`);
  logger.info(`After you are done, download the WARC and close the page`);

  // look up and save the downloaded file when user closes the tab.
  return new Promise<{ archiveFile?: string; timestamp?: string }>(
    (resolve) => {
      page.on('close', async () => {
        const warcFile = findLatestDownloads(downloadsPath);
        if (!warcFile) {
          resolve({ timestamp });
        } else {
          const archiveFile = path.join(archiveFolderPath, 'archive.wacz');
          fs.copyFileSync(warcFile, archiveFile);
          resolve({ archiveFile, timestamp });
        }
        context.close();
      });
    },
  );
}

function findLatestDownloads(downloadsFolder: string): string | undefined {
  const files = fs
    .readdirSync(downloadsFolder)
    .map((f) => path.join(downloadsFolder, f));

  if (files.length === 0) {
    return undefined;
  }

  let latestFile = files[0]!;
  let latestFileModified = fs.lstatSync(latestFile).mtime;
  for (let i = 1; i < files.length; i++) {
    const file = files[i]!;
    const fileModified = fs.lstatSync(file).mtime;
    if (fileModified > latestFileModified) {
      latestFile = file;
      latestFileModified = fileModified;
    }
  }
  return latestFile;
}
