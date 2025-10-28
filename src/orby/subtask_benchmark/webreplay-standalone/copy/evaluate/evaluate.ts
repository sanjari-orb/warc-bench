import { Replay } from 'protos/pb/v1alpha1/orbot_replay';
import { logger } from '../libs/logger';
import { EvalEntry } from '../types';
import { BrowserContext } from 'playwright';
import { simulateEvents } from './simulate-events';
import { compareGeneratedActions } from './compare';
import { execute } from './execute';
import { notMatchMsg } from '../constants';

/**
 * Execute defined actions and verify results if the side effect is defined.
 *
 * We may set up environment and execute a process twice:
 * 1. recording with simulated events
 * 2. execute generated recording events
 */
export async function evaluate(
  browserContext: BrowserContext,
  replay: Replay,
  evalEntry: EvalEntry,
  slowMo: number,
): Promise<void> {
  // recording test and check with the expected action
  if (replay.events?.length) {
    const generatedActions = await simulateEvents(
      replay,
      browserContext,
      slowMo,
    );

    logger.info('Comparing generated actions with expected actions');
    if (replay.actions?.length) {
      // compare the generatedActions
      evalEntry.recordingSuccess = compareGeneratedActions(
        replay.actions,
        generatedActions,
      );

      if (!evalEntry.recordingSuccess) {
        logger.error(
          `${evalEntry.path} Generated actions doesn't match expected ones`,
        );
        evalEntry.failureReason = notMatchMsg;
        if (!evalEntry.expectRecordingFailure) {
          evalEntry.unexpectedFailure = true;
        }
      }
    } else {
      logger.error('Expected actions are not defined');
      logger.error(generatedActions);
    }

    // Initialize counts
    evalEntry.clickCount = 0;
    evalEntry.setValueCount = 0;
    evalEntry.successfulClickCount = 0;
    evalEntry.successfulSetValueCount = 0;

    // execution test and verify result
    if (replay.actions?.length) {
      evalEntry.executionSuccess = await execute(
        replay,
        browserContext,
        replay.actions,
        slowMo,
        evalEntry,
      );
      if (!evalEntry.executionSuccess) {
        evalEntry.unexpectedFailure = true;
        evalEntry.failureReason =
          'An error occurred during the execute action process, causing the verification to fail.';
      }
    } else {
      logger.warn('No evaluation examples found');
    }
  }
}
