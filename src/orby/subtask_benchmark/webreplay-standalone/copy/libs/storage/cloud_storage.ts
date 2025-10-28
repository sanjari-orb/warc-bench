import { Storage } from '@google-cloud/storage';
import { logger } from '../logger';
import { googleAuth } from './auth';
import path from 'path';
import { replaysPath } from '../../constants';
import fs from 'fs';

const storage = new Storage({ authClient: googleAuth });

const bucketName = 'orby-warc';

const gcsPathPrefix = `gs://${bucketName}/`;

/**
 * Download a file on GCS to a local destination.
 */
export async function downloadWarcFile(gcsPath: string, destination: string) {
  if (!gcsPath.startsWith(gcsPathPrefix)) {
    throw new Error(`Can only handle files in the orby-warc GCS bucket`);
  }
  gcsPath = gcsPath.substring(gcsPathPrefix.length);

  const folder = path.dirname(destination);
  if (!fs.existsSync(folder)) {
    fs.mkdirSync(folder, { recursive: true });
  }

  logger.info(`Downloading gs://${bucketName}/${gcsPath} to ${destination}`);
  // Downloads the file
  await storage.bucket(bucketName).file(gcsPath).download({
    destination,
  });

  logger.info(`gs://${bucketName}/${gcsPath} downloaded.`);
}

/**
 * Upload the WARC file to the bucket.
 *
 * If the file already exists in the folder, we'll raise an error if override is not set.
 */
export async function uploadWarcFile(
  warcFilePath: string,
  gcsFileName: string,
  override = false,
): Promise<string> {
  const bucket = storage.bucket(bucketName);
  const gcsFile = bucket.file(gcsFileName);
  const [fileExists] = await gcsFile.exists();
  if (fileExists) {
    if (override) {
      await gcsFile.delete();
    } else {
      throw new Error(`File exists for ${gcsFileName}`);
    }
  }
  await bucket.upload(warcFilePath, { destination: gcsFileName });
  return `gs://${bucketName}/${gcsFileName}`;
}

const cacheFolder = path.join(replaysPath, '.warc_cache');

/**
 * Get a file on GCS, caches the files locally after initial download.
 */
export async function getWarcFileOnGcs(gcsPath: string) {
  if (!gcsPath.startsWith(gcsPathPrefix)) {
    throw new Error(`Can only handle files in the orby-warc GCS bucket`);
  }

  const relativePath = gcsPath.substring(gcsPathPrefix.length);
  const cachePath = path.join(cacheFolder, relativePath);
  if (fs.existsSync(cachePath)) {
    return cachePath;
  }

  await downloadWarcFile(gcsPath, cachePath);
  return cachePath;
}
