import { evaluate as eval } from '../../../../packages/webreplay/src/evaluate/evaluate';
import { EvalEntry } from 'webreplay/src/types';
import { setupEnv } from '../env/setup';
import { BrowserContext } from 'playwright';
import { logger } from '../libs/logger';
import { notMatchMsg } from '../constants';

/**
 * Options for evaluating a replay file
 * @interface EvaluateOptions
 * @property {BrowserContext} browserContext - Playwright browser context for evaluation
 * @property {number} slowMo - Delay in milliseconds between actions for better visibility
 * @property {boolean} firstTime - Flag indicating if this is the initial evaluation of the replay
 */
export interface EvaluateOptions {
  browserContext: BrowserContext;
  slowMo: number;
  firstTime: boolean;
  maxRetries: number;
}

/**
 * Evaluates a replay file using the provided browser context and options
 * @param {string} replayFile - Path to the replay file to evaluate
 * @param {EvaluateOptions} options - Configuration options for evaluation
 * @returns {Promise<EvalEntry>} Results of the evaluation
 */
export async function evaluate(
  replayFile: string,
  { browserContext, slowMo, firstTime, maxRetries }: EvaluateOptions,
): Promise<EvalEntry> {
  let retries = 0;
  let result: EvalEntry;
  while (retries < maxRetries) {
    logger.info(
      `Evaluating ${replayFile} with slowMo=${slowMo} (attempt ${retries + 1})`,
    );
    retries++;
    result = await setupEnv({
      replayFile,
      browserContext,
      firstTime,
      hook: async (replay, evalEntry) => {
        await eval(browserContext, replay, evalEntry, slowMo);
      },
    });
    // If encounter failure, whatever is expect or unexpect, retry it
    // Or if the failure reason is 'Expect Generation Failure', no need to retry
    // Like in jira create filter cases, use different filter name
    if (result.failureReason === 'Extension service worker is not ready yet') {
      result.unexpectedFailure = false;
    }
    if (
      !result.failureReason ||
      (result.failureReason === notMatchMsg &&
        result.expectGenerationFailureDetail?.skipRetry)
    ) {
      break;
    }
  }
  return result!;
}
