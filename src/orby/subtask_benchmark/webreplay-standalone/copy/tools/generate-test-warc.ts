import path from 'path';
import fs from 'fs';
import { archivesFolderPath } from '../constants';
import { createWarcIndex } from '../libs/warc/warc-record';
import { WARCRecord, WARCSerializer, WARCType } from 'warcio';

async function writeRecord(
  record: WARCRecord,
  writer: fs.WriteStream,
): Promise<void> {
  const headers: { [key: string]: string } = {};
  record.httpHeaders!.headers.forEach((value: any, key: string) => {
    headers[key] = value;
  });
  const newRecord = WARCRecord.create(
    {
      url: record.warcTargetURI!,
      date: record.warcDate!,
      type: record.warcType as WARCType,
      warcVersion: 'WARC/1.1',
      httpHeaders: headers,
    },
    {
      async *[Symbol.asyncIterator]() {
        yield record.payload!;
      },
    },
  );
  writer.write(await WARCSerializer.serialize(newRecord));
}

/**
 * This function writes a WARC file with the given digests.
 */
async function writeToWarcFile(testWarcFile: string, urls: string[]) {
  const warcVersion = 'WARC/1.1';
  const info = {
    software: 'warcio.js in node',
  };
  const filename = testWarcFile.split('/').pop()!;
  const stream = fs.createWriteStream(testWarcFile);

  const warcinfo = WARCRecord.createWARCInfo({ filename, warcVersion }, info);
  stream.write(await WARCSerializer.serialize(warcinfo));

  const warcIndex = await createWarcIndex(
    fs.readFileSync(
      path.join(
        archivesFolderPath,
        'tmp_orby-website-test-archive/archive/data.warc',
      ),
    ),
  );
  for (const [_, requests] of warcIndex) {
    for (const [request, response] of requests) {
      if (urls.includes(request.warcTargetURI!)) {
        await writeRecord(request, stream);
        await writeRecord(response, stream);
      }
    }
  }
  stream.end();
}

async function main() {
  await writeToWarcFile(path.join(archivesFolderPath, 'tests/test.warc'), [
    'https://www.orby.ai/',
    'https://www.orby.ai/case-studies',
    'https://www.orby.ai/company',
  ]);
}

main();
