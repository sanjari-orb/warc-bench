// NOTE: The extension uses global.d.ts to define environment variables.
// webreplay imports the extension code, but ts-node doesn't pick up .d.ts files,
// so we need to manually reference the .d.ts file.
/* eslint-disable @typescript-eslint/triple-slash-reference */
/// <reference path="../../extension/src/global.d.ts" />

import {
  ExpectGenerationFailure,
  SkipReason,
} from 'protos/pb/v1alpha1/orbot_replay';

export type EnvType = 'html' | 'warc' | 'live';

/**
 * Eval entry that would be synced to Google Sheets
 */
export interface EvalEntry {
  // txtpb file path relative to the package/webreplay/replays folder
  path: string;
  env: EnvType;
  description?: string;

  numEvents: number;
  numActions: number;
  applications: string[];

  // whether the evaluation is skipped
  isSkipped: boolean;
  skipReason?: SkipReason;
  expectGenerationFailureDetail: ExpectGenerationFailure;
  expectRecordingFailure: boolean;
  expectExecutionFailure: boolean;

  // whether we encounter any error during env setup
  envSetupFailure?: boolean;

  recordingSuccess?: boolean;
  executionSuccess?: boolean;

  unexpectedFailure?: boolean;

  failureReason?: string;
  slowMo?: number;

  clickCount?: number;
  setValueCount?: number;
  successfulClickCount?: number;
  successfulSetValueCount?: number;
}

export interface ActionMetrics {
  clickCount: number;
  setValueCount: number;
}

// offline = warc + static pages
export enum Mode {
  Offline = 'offline',
  Live = 'live',
  Both = 'both',
}

export enum ExpectGenerationFailureOption {
  // Default behavior: each test case determines whether it expects generation failure based on its own configuration.
  Default = 'default',
  // All test cases expect generation failure, regardless of their individual configurations.
  All = 'all',
  // No test cases expect generation failure, regardless of their individual configurations.
  None = 'none',
}

export enum ExpectExecutionFailureOption {
  // Default behavior: each test case determines whether it expects execution failure based on its own configuration.
  Default = 'default',
  // All test cases expect execution failure, regardless of their individual configurations.
  All = 'all',
  // No test cases expect execution failure, regardless of their individual configurations.
  None = 'none',
}

export enum SkipOption {
  // Default behavior: each test case determines whether it skips based on its own configuration.
  Default = 'default',
  // No test cases skip, regardless of their individual configurations.
  None = 'none',
}
