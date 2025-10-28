import AdmZip from 'adm-zip';
import path from 'path';
import fs from 'fs';
import { createGunzip } from 'node:zlib';

export async function unzip(warcFilePath: string): Promise<void> {
  const outputDir = path.dirname(warcFilePath);
  const zip = new AdmZip(warcFilePath);
  zip.extractAllTo(outputDir);

  const gzipFilePath = path.join(outputDir, 'archive/data.warc.gz');
  const input = fs.createReadStream(gzipFilePath);
  const output = fs.createWriteStream(path.join(outputDir, 'data.warc'));
  const gunzip = createGunzip();

  return new Promise((resolve, reject) => {
    input
      .pipe(gunzip)
      .pipe(output)
      .on('finish', () => {
        resolve();
      })
      .on('error', (error) => {
        reject(error);
      });
  });
}
