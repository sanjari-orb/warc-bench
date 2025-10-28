import path from 'path';
import { createWarcIndex } from './warc-record';
import { archivesFolderPath } from '../../constants';

// For some reason jest/ts-jest raises error `ReferenceError: Headers is not defined`
// so using the one from the node-fetch for temporary fix.
// @ts-expect-error TS7016
import { Headers } from 'node-fetch';
import fs from 'fs';
global.Headers = Headers;

describe('warc-record.ts', () => {
  // the test passes on macOS, but fails on linux GitHub Actions.
  // TODO: fix and enable this test in GitHub Actions.
  it.skip('should parse a warc file', async () => {
    const warcFile = path.join(archivesFolderPath, 'tests/test.warc');
    const warcIndex = await createWarcIndex(fs.readFileSync(warcFile));
    expect(warcIndex.size).toBe(3);
  });
});
