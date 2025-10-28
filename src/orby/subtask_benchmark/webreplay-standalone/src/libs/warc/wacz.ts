import { getWarcFileOnGcs } from '../storage/cloud_storage';
import Protocol from 'devtools-protocol';
import AdmZip from 'adm-zip';
import { promisify } from 'node:util';
import { unzip } from 'node:zlib';
import { createWarcIndex, WarcIndex } from './warc-record';

export interface WarcMetadata {
  mainPageUrl?: string;
  browserState?: {
    localStorage?: Record<string, Record<string, string>>;
    sessionStorage?: Record<string, Record<string, string>>;
    cookies?: Protocol.Network.Cookie[];
  };
}

async function readWarcFileByte(
  warcFilePath: string,
  filePath: string,
): Promise<Buffer> {
  if (warcFilePath.startsWith('gs://')) {
    warcFilePath = await getWarcFileOnGcs(warcFilePath);
  }
  const zip = new AdmZip(warcFilePath);
  return zip.getEntry(filePath)!.getData();
}

/**
 * Read WARC file content in a wacz file format. Handles both local files as well
 * as files on GCS.
 */
async function getWarcIndex(warcFilePath: string): Promise<WarcIndex> {
  const compressed = await readWarcFileByte(
    warcFilePath,
    'archive/data.warc.gz',
  );
  const warcContent = await promisify(unzip)(new Uint8Array(compressed));
  return await createWarcIndex(warcContent);
}

async function getWarcMetadata(warcFilePath: string): Promise<WarcMetadata> {
  const bytes = await readWarcFileByte(warcFilePath, 'datapackage.json');
  return JSON.parse(bytes.toString('utf-8'));
}

export async function readWarcData(
  warcFilePath: string,
): Promise<[WarcMetadata, WarcIndex]> {
  const warcIndex = await getWarcIndex(warcFilePath);
  const metadata = await getWarcMetadata(warcFilePath);
  return [metadata, warcIndex];
}

export function getArchiveUrl(warcFile: string): string {
  const zip = new AdmZip(warcFile);
  const entry = zip.getEntry('pages/pages.jsonl');
  if (!entry) {
    throw new Error(`no pages/pages.jsonl is found in file ${warcFile}`);
  }
  const lines = entry.getData().toString().split('\n');
  const firstPageLine = lines[1];
  if (!firstPageLine) {
    throw new Error(`No line is found in pages/pages.jsonl`);
  }
  return JSON.parse(firstPageLine)['startUrl'] as string;
} 