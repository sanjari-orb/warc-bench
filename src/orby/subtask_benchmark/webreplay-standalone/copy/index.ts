import { program } from 'commander';
import { notMatchMsg, replaysPath } from './constants';
import { evaluate } from './commands/evaluate';
import { serve } from './commands/serve';
import { record } from './commands/record';
import { LoggingFlag, logger } from './libs/logger';
import path from 'path';
import fs from 'fs';
import {
  EvalEntry,
  ExpectExecutionFailureOption,
  ExpectGenerationFailureOption,
  SkipOption,
  Mode,
} from './types';
import { getArchiveUrl } from './libs/warc/wacz';
import { uploadWarcFileForReplay } from './commands/upload';
import { writeEvalResultToSheets } from 'webreplay/src/evaluate/result';
import { getBrowseContext, getBrowseContextForRecord } from './env/setup';
import { groupCasesByApplication, ReplayFile } from './libs/utils/txtproto';
import { Concurrent } from './libs/concurrent';
import { unzip } from './commands/unzip';
import {
  calculateMetrics,
  printResultsMetrics,
  calculateSkipCount,
} from './tools/output-metrics';
import { glob } from 'glob';
import { Timestamp } from 'protos/google/protobuf/timestamp';

program
  .name('webreplay')
  .description('CLI to serve/evaluate webreplay archives')
  .version('0.0.1');

program
  .command('evaluate')
  .argument('[files...]')
  .description(
    'Evaluate against one or more file/folder that contain the replay files',
  )
  .option(
    '-s, --slow-mo <number>',
    'slow down the evaluation for better visibility',
    parseInt,
    0,
  )
  .option(
    '-l, --logging <flag...>',
    'configure debug output to console, available flags: forward_browser_console, warc',
  )
  .option(
    '-m, --mode <mode>',
    'specify the mode of running cases available modes: offline, live or both',
    Mode.Both,
  )
  .option(
    '-c, --concurrency <number>',
    'specify the concurrency of running cases',
    (value) => parseInt(value, 10),
    2,
  )
  .option(
    '-g, --generation <expectGenerationFailure>',
    'configure the expect generation failure behavior, available options: default, all, none',
    ExpectGenerationFailureOption.Default,
  )
  .option(
    '-e, --execution <expectExecutionFailure>',
    'configure the expect execution failure behavior, available options: default, all, none',
    ExpectExecutionFailureOption.Default,
  )
  .option(
    '-k, --skip <skip>',
    'configure the skip behavior, available options: default, none',
    SkipOption.Default,
  )
  .action(
    async (
      files: string[],
      options: {
        logging?: LoggingFlag[];
        slowMo: number;
        mode: Mode;
        concurrency: number;
        generation: ExpectGenerationFailureOption;
        execution: ExpectExecutionFailureOption;
        skip: SkipOption;
      },
    ) => {
      logger.info(JSON.stringify(options));
      if (files.length === 0) {
        files.push('**/*.txtpb');
      }
      if (options.logging?.includes(LoggingFlag.FORWARD_BROWSER_CONSOLE)) {
        logger.info('Forwarding browser console');
        logger.isForwardingBrowserConsole = true;
      }
      if (options.logging?.includes(LoggingFlag.WARC)) {
        logger.info('Logging WARC');
        logger.enableWARCLogging = true;
      }
      const maxConcurrency = options.concurrency;
      const concurrent = new Concurrent(maxConcurrency);
      const maxRetries = process.env.CI ? 2 : 1;
      logger.info(`Using ${maxConcurrency} concurrency`);
      const results: EvalEntry[] = [];
      const groupResults = groupCasesByApplication(
        files,
        options.mode,
        options.skip,
      );
      logger.info(
        `Evaluating ${groupResults.replayFileGroups.size} applications`,
      );
      if (options.mode === 'offline') {
        // If use offline mode, we use persistent browser context, not need to create new one for each application
        // Merge all replay files into an array
        const allReplayFiles: ReplayFile[] = [];
        for (const group of groupResults.replayFileGroups.values()) {
          const validFiles = group.replayFiles.filter((file) => file?.filePath);
          allReplayFiles.push(...validFiles);
        }
        allReplayFiles.sort((a, b) => {
          if (a.filePath < b.filePath) return 1;
          if (a.filePath > b.filePath) return -1;
          return 0;
        });
        concurrent.initTasks(allReplayFiles);
        for (let i = 0; i < maxConcurrency; i++) {
          concurrent.append(async () => {
            let browserContext = await getBrowseContext('', options.mode);
            if (browserContext) {
              try {
                let task: ReplayFile | null;
                while ((task = concurrent.getNextTask()) !== null) {
                  const slowMo = Math.max(
                    options.slowMo,
                    task.replay.slowMo || 0,
                  );

                  try {
                    const result = await evaluate(task.filePath, {
                      browserContext,
                      slowMo: slowMo,
                      firstTime: true,
                      maxRetries: maxRetries,
                    });

                    results.push(result);
                    logger.info(
                      `File: ${task}, Click Success: ${result.successfulClickCount}/${result.clickCount}`,
                    );
                  } catch (error) {
                    logger.error(
                      `Error evaluating ${path.relative(replaysPath, task.filePath)}`,
                      error,
                    );
                    //If browser context is crashed
                    if (
                      error.message.includes(
                        'Target page, context or browser has been closed',
                      )
                    ) {
                      browserContext = await getBrowseContext('', options.mode);
                    }
                  }
                }
              } finally {
                await browserContext.close();
              }
            }
          });
        }
      } else {
        // live mode
        for (const [
          application,
          group,
        ] of groupResults.replayFileGroups.entries()) {
          concurrent.append(async () => {
            let browserContext = await getBrowseContext(group, options.mode);
            if (browserContext) {
              logger.info(
                `${application} Evaluating ${group.replayFiles.length} cases`,
              );
              for (const replayFile of group.replayFiles) {
                let result: EvalEntry;
                const slowMo = Math.max(
                  options.slowMo,
                  replayFile.replay.slowMo || 0,
                );
                try {
                  result = await evaluate(replayFile.filePath, {
                    browserContext,
                    slowMo: slowMo,
                    firstTime: group.replayFiles.indexOf(replayFile) === 0,
                    maxRetries: maxRetries,
                  });
                } catch (error) {
                  logger.error(
                    `Unexpected error when evaluating ${path.relative(replaysPath, replayFile.filePath)}`,
                    error,
                  );
                  if (
                    error.message.includes(
                      'Target page, context or browser has been closed',
                    )
                  ) {
                    browserContext = await getBrowseContext('', options.mode);
                  }
                  continue;
                }
                results.push(result);

                // Log the new metrics
                logger.info(
                  `File: ${replayFile.filePath}, Click Success: ${result.successfulClickCount}/${result.clickCount}, SetValue Success: ${result.successfulSetValueCount}/${result.setValueCount}`,
                );
              }
              await browserContext.close();
            } else {
              groupResults.skipReasonCategorize.vmRequired +=
                group.replayFiles.length;
              logger.info(
                `Skipping ${application} ${group.replayFiles.length} replays due to VM required, if you want to run it locally, please set CI=true`,
              );
            }
          });
        }
      }
      await concurrent.waitForCompletion();
      await writeEvalResultToSheets(results);
      if (options.generation === ExpectGenerationFailureOption.All) {
        console.warn(
          'Ignoring all the generation failures whatever the test case is configured to expect generation failure.',
        );
        results.forEach((result) => {
          if (
            result.unexpectedFailure &&
            result.failureReason === notMatchMsg
          ) {
            result.unexpectedFailure = false;
          }
        });
      } else if (options.generation === ExpectGenerationFailureOption.None) {
        console.warn(
          'Throwing all the generation failures whatever the test case is configured to expect generation failure.',
        );
        results.forEach((result) => {
          if (result.failureReason === notMatchMsg) {
            result.unexpectedFailure = true;
          }
        });
      }

      if (options.execution === ExpectExecutionFailureOption.All) {
        console.warn(
          'Ignoring all the execution failures whatever the test case is configured to expect execution failure.',
        );
        results.forEach((result) => {
          if (
            result.unexpectedFailure &&
            result.failureReason &&
            result.failureReason !== notMatchMsg
          ) {
            result.unexpectedFailure = false;
          }
        });
      } else if (options.execution === ExpectExecutionFailureOption.None) {
        console.warn(
          'Throwing all the execution failures whatever the test case is configured to expect execution failure.',
        );
        results.forEach((result) => {
          if (result.failureReason && result.failureReason !== notMatchMsg) {
            result.unexpectedFailure = true;
          }
        });
      }

      const metrics = await calculateMetrics(
        groupResults.skipReasonCategorize,
        results,
      );

      await printResultsMetrics(metrics);

      if (metrics.unexpectedFailures.length > 0) {
        // Force process exit with error code after a short delay to ensure logs are written
        setTimeout(() => process.exit(-1), 100);
      } else {
        const relevantSkippedCount =
          calculateSkipCount(groupResults.skipReasonCategorize) -
          (groupResults.skipReasonCategorize.modeIgnore || 0);

        if (metrics.total === 0) {
          // Handle the case where no tests were run
          const modeSkippedCount =
            groupResults.skipReasonCategorize.modeIgnore || 0;
          if (modeSkippedCount > 0) {
            logger.info(
              `[${new Date().toISOString()}]No tests were executed. ${modeSkippedCount} tests were skipped due to mode configuration.`,
            );
          } else {
            logger.info(
              `[${new Date().toISOString()}]No tests were found or executed.`,
            );
          }
        } else if (
          metrics.expectedFailures.length > 0 ||
          relevantSkippedCount > 0
        ) {
          logger.info(
            `[${new Date().toISOString()}]No unexpected failures! (${metrics.success}/${metrics.total} successful, ${metrics.expectedFailures.length} expected failures, ${relevantSkippedCount} skipped cases)`,
          );
        } else {
          logger.info(
            `[${new Date().toISOString()}]All tests passed! (${metrics.success}/${metrics.total})`,
          );
        }

        // Force process exit with success code after a short delay
        setTimeout(() => process.exit(0), 100);
      }
    },
  );

program
  .command('serve')
  .argument('[file]')
  .option(
    '-l, --logging <flag...>',
    'configure debug output to console, available flags: forward_browser_console, warc',
  )
  .action(async (pattern, options: { logging?: LoggingFlag[] }) => {
    if (!pattern.endsWith('txtpb')) {
      console.error('Invalid file format');
      return;
    }
    if (options.logging?.includes(LoggingFlag.FORWARD_BROWSER_CONSOLE)) {
      logger.info('Forwarding browser console');
      logger.isForwardingBrowserConsole = true;
    }
    if (options.logging?.includes(LoggingFlag.WARC)) {
      logger.info('Logging WARC');
      logger.enableWARCLogging = true;
    }

    const matchedFiles = glob.sync(`**/${pattern}*`, {
      cwd: replaysPath,
      absolute: true,
      ignore: ['**/node_modules/**', '**/.*/**'],
    });
    logger.info(`Matched ${matchedFiles.length} files`);

    // Filter out files in the get-list directory
    const filteredFiles = matchedFiles.filter(
      (file) => !file.includes('/get-list/'),
    );
    logger.info(
      `Running ${filteredFiles.length} files (excluded ${matchedFiles.length - filteredFiles.length} files from get-list directory)`,
    );

    if (filteredFiles.length !== 1) {
      logger.error(
        `Found ${filteredFiles.length} files:\n${filteredFiles.join(
          '\n',
        )}\nPlease specify the file name`,
      );
      return;
    }
    const fullPath = filteredFiles[0];
    // For server command, we doesn't care the mode
    const browserContext = await getBrowseContext(fullPath, Mode.Both);
    await serve(fullPath, browserContext!).catch(logger.error);
  });

program
  .command('record')
  .requiredOption(
    '-n, --name <archive_name>',
    'archive folder name, located in packages/webreplay/replays/applications, will be created if not exists',
  )
  .option(
    '-fd, --fix-date',
    'enables date override for deterministic recording (presence means true)',
    false,
  )
  .action(async (options) => {
    console.log(options);
    const result = await record(options.name, { fixDate: options.fixDate });
    if (result?.archiveFile) {
      const archiveFile = result.archiveFile;
      const url = getArchiveUrl(archiveFile);
      const replayFile = path.join(path.dirname(archiveFile), 'replay.txtpb');

      // Get the timestamp from the record function result
      let timestampString = '';
      if (result.timestamp) {
        const date = new Date(Number(result.timestamp));
        const timestamp = date.getTime();
        const timestampProto = Timestamp.create({
          seconds: Math.floor(timestamp / 1000),
          nanos: (timestamp % 1000) * 1000000,
        });
        timestampString = `
  timestamp: {
    seconds: ${timestampProto.seconds}
    nanos: ${timestampProto.nanos}
  }`;
      } else {
        timestampString = '';
      }

      const replayFileContent = `
# proto-file: protos/pb/v1alpha1/orbot_replay.proto
# proto-message: Replay

env {
  warc_file_path: "./archive.wacz"
  start_url: "${url}"${timestampString}
}
      `.trim();

      fs.writeFileSync(replayFile, replayFileContent);
      const browserContext = await getBrowseContextForRecord(replayFile);
      await serve(replayFile, browserContext!);
    }
  });

program
  .command('upload')
  .argument('[file]')
  .option('--override', 'override existing file on GCS', false)
  .action(async (file, options) => {
    await uploadWarcFileForReplay(path.resolve(file), options.override);
  });

program
  .command('unzip')
  .argument('[file]')
  .description('Unzip the wacz file recursively')
  .action(async (file) => {
    await unzip(path.resolve(file));
  });

program.parse();
