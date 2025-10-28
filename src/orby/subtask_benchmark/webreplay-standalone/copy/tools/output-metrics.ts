import { logger } from '../libs/logger';
import { ReasonCategorization } from '../libs/utils/txtproto';
import { EvalEntry } from '../types';

interface ResultMetrics {
  total: number;
  skipReasonCategorize: ReasonCategorization;
  expectedFailures: EvalEntry[];
  unexpectedFailures: EvalEntry[];
  success: number;
  executionCoverage: number;
  passCoverage: number;
  totalClicks: number;
  successfulClicks: number;
  totalSetValues: number;
  successfulSetValues: number;
  totalFailures: number;
}

export async function calculateMetrics(
  skipReasonCategorize: ReasonCategorization,
  results: EvalEntry[],
): Promise<ResultMetrics> {
  // Calculate skipped tests, but exclude those skipped due to mode
  const modeSkippedCount = skipReasonCategorize.modeIgnore || 0;
  const relevantSkippedCount =
    calculateSkipCount(skipReasonCategorize) - modeSkippedCount;

  // Total includes only tests that are relevant for the current mode
  const total = results.length + relevantSkippedCount;
  const expectedFailures = results.filter(
    (f) => f.unexpectedFailure === false && f.failureReason,
  );
  const unexpectedFailures = results.filter((f) => f.unexpectedFailure);

  // Total failures should only include relevant skipped tests, not mode-skipped ones
  const totalFailures =
    expectedFailures.length + unexpectedFailures.length + relevantSkippedCount;
  const success =
    results.length - expectedFailures.length - unexpectedFailures.length;

  const executeCoverage =
    total > 0 ? Math.round((results.length / total) * 100) : 0;

  const passCoverage = total > 0 ? Math.round((success / total) * 100) : 0;

  const totalClicks = results.reduce((sum, r) => sum + (r.clickCount || 0), 0);
  const successfulClicks = results.reduce(
    (sum, r) => sum + (r.successfulClickCount || 0),
    0,
  );
  const totalSetValues = results.reduce(
    (sum, r) => sum + (r.setValueCount || 0),
    0,
  );
  const successfulSetValues = results.reduce(
    (sum, r) => sum + (r.successfulSetValueCount || 0),
    0,
  );

  return {
    total: total,
    skipReasonCategorize: skipReasonCategorize,
    expectedFailures: expectedFailures,
    unexpectedFailures: unexpectedFailures,
    success,
    executionCoverage: executeCoverage,
    passCoverage: passCoverage,
    totalClicks,
    successfulClicks,
    totalSetValues,
    successfulSetValues,
    totalFailures,
  };
}

export async function printResultsMetrics(metrics: ResultMetrics) {
  const totalSkippedCount = calculateSkipCount(metrics.skipReasonCategorize);
  const modeSkippedCount = metrics.skipReasonCategorize.modeIgnore || 0;
  const relevantSkippedCount = totalSkippedCount - modeSkippedCount;

  logger.info('\n📊 Test Execution Summary');
  logger.info('═══════════════════════════════════════');
  logger.info(`📌 Total Cases    : ${metrics.total}`);
  logger.info(
    `🔵 Executed       : ${metrics.success + metrics.expectedFailures.length + metrics.unexpectedFailures.length}`,
  );
  logger.info(`✅ Successful     : ${metrics.success}`);
  logger.info(`❌ Total Failures : ${metrics.totalFailures}`);
  logger.info(`  ├─ ⚠️  Expected Fails : ${metrics.expectedFailures.length}`);
  logger.info(`  ├─ ❌ Unexpected Fails: ${metrics.unexpectedFailures.length}`);
  logger.info(`  └─ ⏩ Relevant Skipped: ${relevantSkippedCount}`);
  logger.info('───────────────────────────────────────');
  logger.info(`⏩ Skipped Breakdown (Relevant for this mode):`);
  logger.info(
    `  ├─ Anti Bot Detection: ${metrics.skipReasonCategorize.antiBot}`,
  );
  logger.info(`  ├─ Known Issue: ${metrics.skipReasonCategorize.knownIssue}`);
  logger.info(`  ├─ VM Required: ${metrics.skipReasonCategorize.vmRequired}`);
  logger.info(`  └─ Other: ${metrics.skipReasonCategorize.other}`);

  if (modeSkippedCount > 0) {
    logger.info('───────────────────────────────────────');
    logger.info(
      `ℹ️ Mode-ignored tests: ${modeSkippedCount} (not counted in metrics)`,
    );
  }

  logger.info('───────────────────────────────────────');
  logger.info(`📈 Execution Coverage  : ${metrics.executionCoverage}%`);
  logger.info(`📈 Pass Coverage       : ${metrics.passCoverage}%`);
  const clickSuccessRate =
    metrics.totalClicks > 0
      ? ((metrics.successfulClicks / metrics.totalClicks) * 100).toFixed(2)
      : '0.00';
  const setValueSuccessRate =
    metrics.totalSetValues > 0
      ? ((metrics.successfulSetValues / metrics.totalSetValues) * 100).toFixed(
          2,
        )
      : '0.00';
  logger.info(
    `Click Success Rate: ${clickSuccessRate}% (${metrics.successfulClicks}/${metrics.totalClicks})`,
  );
  logger.info(
    `SetValue Success Rate: ${setValueSuccessRate}% (${metrics.successfulSetValues}/${metrics.totalSetValues})`,
  );
  logger.info('═══════════════════════════════════════\n');

  if (metrics.expectedFailures.length > 0) {
    logger.warn('\n⚠️  Expected Failures Details:');
    logger.warn('─────────────────────────────');

    for (const failure of metrics.expectedFailures) {
      logger.warn(`Expected Failure: ${failure.path}`);
      logger.warn(`Expected Failure Reason: ${failure.failureReason}`);
      logger.warn('─────────────────────────────');
    }
  }

  if (metrics.unexpectedFailures.length > 0) {
    logger.error('\n❌ Unexpected Failures Details:');
    logger.error('─────────────────────────────');
    for (const failure of metrics.unexpectedFailures) {
      logger.error(`Unexpected Failure: ${failure.path}`);
      logger.error(`Unexpected Failure Reason: ${failure.failureReason}`);
      logger.error('─────────────────────────────');
    }
  }

  if (relevantSkippedCount > 0) {
    logger.info('\n⏩ Skipped Cases Details:');
    logger.info('─────────────────────────────');

    if (metrics.skipReasonCategorize.antiBot > 0) {
      logger.info(
        `Anti-bot detection: ${metrics.skipReasonCategorize.antiBot} cases`,
      );
    }
    if (metrics.skipReasonCategorize.knownIssue > 0) {
      logger.info(
        `Known issues: ${metrics.skipReasonCategorize.knownIssue} cases`,
      );
    }
    if (metrics.skipReasonCategorize.vmRequired > 0) {
      logger.info(
        `VM required: ${metrics.skipReasonCategorize.vmRequired} cases`,
      );
    }
    if (metrics.skipReasonCategorize.other > 0) {
      logger.info(`Other reasons: ${metrics.skipReasonCategorize.other} cases`);
    }
    logger.info('─────────────────────────────────────');
  }
}

export function calculateSkipCount(skipReasonCategorize: ReasonCategorization) {
  return Object.values(skipReasonCategorize).reduce(
    (sum, count) => sum + count,
    0,
  );
}
