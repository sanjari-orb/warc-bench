import { execSync } from 'child_process';
import {
  rootPath,
  protoRootPath,
  protocPath,
  replaysPath,
} from '../../constants';
import { Replay } from 'protos/pb/v1alpha1/orbot_replay';
import path from 'path';
import { glob } from 'glob';
import fs from 'fs';
import { logger } from '../logger';
import { Mode, SkipOption } from '../../types';

export function getReplayActions(filePath: string, resolvePath = true): Replay {
  // execute protoc once to make sure it is installed. Otherwise, we'll get an
  // output like `@protobuf-ts/protoc installed protoc v27.2.` for the first run.
  execSync(`${protocPath} --version`);
  const output = execSync(
    `${protocPath} --encode=pb.v1alpha1.Replay --proto_path=${protoRootPath} pb/v1alpha1/orbot_replay.proto < ${filePath}`,
    { cwd: rootPath },
  );
  const uint8Array = new Uint8Array(
    output.buffer,
    output.byteOffset,
    output.byteLength,
  );
  const replay = Replay.decode(uint8Array);

  // replace relative WARC file path to absolute one.
  if (
    resolvePath &&
    replay.env?.warcFilePath &&
    replay.env.warcFilePath.startsWith('.')
  ) {
    replay.env.warcFilePath = path.resolve(
      path.join(path.dirname(filePath), replay.env?.warcFilePath),
    );
  }
  return replay;
}

export interface ReasonCategorization {
  antiBot: number;
  knownIssue: number;
  vmRequired: number;
  modeIgnore: number;
  other: number;
}

type ApplicationName = string;
export interface ReplayFile {
  filePath: string;
  replay: Replay;
}
export interface ApplicationGroup {
  application: ApplicationName;
  replayFiles: ReplayFile[];
}

export interface GroupResult {
  replayFileGroups: Map<ApplicationName, ApplicationGroup>;
  skipReasonCategorize: ReasonCategorization;
}

export function groupCasesByApplication(
  patterns: string[],
  mode: Mode,
  skipOption: SkipOption,
): GroupResult {
  const replayFileGroups: Map<ApplicationName, ApplicationGroup> = new Map();
  const skipReasonCategorize: ReasonCategorization = {
    antiBot: 0,
    knownIssue: 0,
    vmRequired: 0,
    modeIgnore: 0,
    other: 0,
  };
  // Find all matching files using glob patterns
  const matchedFiles = patterns.flatMap((pattern) =>
    glob.sync(`**/${pattern}*`, {
      cwd: replaysPath,
      absolute: true,
      ignore: ['**/node_modules/**', '**/.*/**'],
    }),
  );
  logger.info(`Matched ${matchedFiles.length} files`);

  function processDirectory(dirPath: string) {
    if (dirPath.includes('node_modules')) {
      // Skip the modules folder
      return;
    }
    if (fs.existsSync(dirPath)) {
      const stats = fs.statSync(dirPath);
      if (path.basename(dirPath).startsWith('.')) {
        // Skip hidden directories and files
        return;
      }
      if (stats.isFile() && path.extname(dirPath) === '.txtpb') {
        // If the input is a txtpb file, add it to the corresponding group
        const replay = getReplayActions(dirPath);
        if (skipOption === SkipOption.None) {
          // If skip option is none, we should not skip the replay
          replay.skipReason = undefined;
        }
        if (!isReplayCompatibleWithMode(replay, mode)) {
          skipReasonCategorize.modeIgnore++;
        } else if (shouldEvaluateReplay(replay, path.basename(dirPath))) {
          // Only add the replay file to the group if it is not marked to be skipped
          const env = replay.env;
          const application =
            env?.setupModule || path.basename(path.dirname(dirPath));
          if (!replayFileGroups.has(application)) {
            replayFileGroups.set(application, {
              application,
              replayFiles: [],
            } as ApplicationGroup);
          }
          replayFileGroups.get(application)!.replayFiles.push({
            filePath: dirPath,
            replay,
          });
        } else {
          const reason = replay.skipReason;
          if (reason?.antiBot) {
            skipReasonCategorize.antiBot++;
          } else if (reason?.knownIssue) {
            skipReasonCategorize.knownIssue++;
          } else {
            skipReasonCategorize.other++;
          }
        }
      } else if (stats.isDirectory()) {
        // If the input is a directory, recursively process its subdirectories
        const subPaths = fs.readdirSync(dirPath);
        subPaths.forEach((subPath) => {
          const subDirPath = path.join(dirPath, subPath);
          processDirectory(subDirPath);
        });
      }
    } else {
      logger.error(`Directory ${dirPath} does not exist`);
    }
  }
  matchedFiles.forEach((filePath) => {
    processDirectory(filePath);
  });
  if (mode === Mode.Offline) {
    // For local mode, each replay has its own group
    return reOrganizeGroup({
      replayFileGroups,
      skipReasonCategorize,
    });
  }
  return {
    replayFileGroups: replayFileGroups,
    skipReasonCategorize: skipReasonCategorize,
  };
}

function shouldEvaluateReplay(replay: Replay, fileName: string): boolean {
  if (replay.skipReason) {
    logger.info(`Skipping evaluation ${fileName} because skipReason is set`);
    return false;
  }
  if (replay.events?.length === 0 && replay.actions?.length === 0) {
    logger.info(
      `Skipping evaluation ${fileName} because no events and actions`,
    );
    return false;
  }
  return true;
}

function isReplayCompatibleWithMode(replay: Replay, mode: Mode): boolean {
  if (mode === Mode.Both) {
    return true;
  }
  // If use local mode, run the warc cases under application and components cases when PR check
  if (
    mode === Mode.Offline &&
    (replay.env?.warcFilePath ||
      (replay.env?.staticPages && replay.env?.staticPages?.length > 0))
  ) {
    return true;
  }
  if (mode === Mode.Live && replay.env?.setupModule) {
    return true;
  }
  return false;
}

function reOrganizeGroup(groupResult: GroupResult): GroupResult {
  const newReplayFileGroups = new Map<string, ApplicationGroup>();
  let groupIndex = 0;
  for (const [
    applicationName,
    group,
  ] of groupResult.replayFileGroups.entries()) {
    for (let i = 0; i < group.replayFiles.length; i++) {
      const replayFile = group.replayFiles[i];
      const newGroupKey = `${applicationName}_${groupIndex}`;
      if (!newReplayFileGroups.has(newGroupKey)) {
        newReplayFileGroups.set(newGroupKey, {
          application: newGroupKey,
          replayFiles: [],
        });
      }
      newReplayFileGroups.get(newGroupKey)!.replayFiles.push(replayFile);
      groupIndex++;
    }
  }
  return {
    replayFileGroups: newReplayFileGroups,
    skipReasonCategorize: groupResult.skipReasonCategorize,
  };
}
