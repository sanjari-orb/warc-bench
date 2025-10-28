import { getReplayActions } from '../libs/utils/txtproto';
import path from 'path';
import { uploadWarcFile } from '../libs/storage/cloud_storage';
import fs from 'fs';

/**
 * Upload the WARC file found in the replay file to GCS, and modify the path to
 * use the GCS path.
 */
export async function uploadWarcFileForReplay(
  replayFile: string,
  override = false,
) {
  // convert to absolute path
  replayFile = path.resolve(replayFile);
  const replay = getReplayActions(replayFile, false);
  const warcFilePath = replay.env?.warcFilePath;
  if (!warcFilePath) {
    throw new Error('No WARC file is found in the replay file');
  }
  if (!warcFilePath.startsWith('.')) {
    throw new Error('WARC file should be a relative path in local file system');
  }
  // convert to absolute path
  const absoluteWarcFilePath = path.join(
    path.dirname(replayFile),
    warcFilePath,
  );

  let gcsFileName = path.basename(absoluteWarcFilePath);
  // use the folder name as the uploaded WARC file name
  if (gcsFileName.endsWith('archive.wacz')) {
    gcsFileName = path.basename(path.dirname(absoluteWarcFilePath)) + '.wacz';
  }

  const gcsFilePath = await uploadWarcFile(
    absoluteWarcFilePath,
    gcsFileName,
    override,
  );

  const originalFileContent = fs.readFileSync(replayFile).toString();
  const updatedFileContent = originalFileContent.replace(
    warcFilePath,
    gcsFilePath,
  );
  fs.writeFileSync(replayFile, updatedFileContent);
}
