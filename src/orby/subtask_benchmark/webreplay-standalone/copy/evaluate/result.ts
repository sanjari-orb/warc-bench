import { sheets_v4 } from '@googleapis/sheets';
import {
  booleanCell,
  EVAL_SHEET_ID,
  EVAL_SPREADSHEET_ID,
  numberCell,
  sheets,
  stringCell,
} from '../libs/storage/sheets';
import { Replay } from 'protos/pb/v1alpha1/orbot_replay';
import { EnvType, EvalEntry } from '../types';
import path from 'path';
import { replaysPath } from '../constants';
import { logger } from '../logger';

export function createEvalEntry(replayFile: string, replay: Replay): EvalEntry {
  const relativePath = path.relative(replaysPath, replayFile);
  let env: EnvType = 'live';
  if (replay.env?.staticPages?.length) {
    env = 'html';
  } else if (replay.env?.warcFilePath) {
    env = 'warc';
  }

  return {
    path: relativePath,
    env,
    description: replay.description,
    numEvents: replay.events?.length ?? 0,
    numActions: replay.actions?.length ?? 0,
    applications: replay.applications ?? [],
    isSkipped: !!replay.skipReason,
    skipReason: replay.skipReason,
    expectGenerationFailureDetail: replay.expectGenerationFailureDetail!,
    expectRecordingFailure: !!replay.expectGenerationFailureDetail?.description,
    expectExecutionFailure: !!replay.expectExecutionFailure,
    slowMo: replay.slowMo,
  };
}

const columnNames: (keyof EvalEntry)[] = [
  'path',
  'description',
  'env',
  'numEvents',
  'numActions',
  'applications',
  'isSkipped',
  'skipReason',
  'expectRecordingFailure',
  'recordingSuccess',
  'executionSuccess',
];

function convertHeaderRow(columnNames: string[]): sheets_v4.Schema$RowData {
  return {
    values: columnNames.map((columnName) => stringCell(columnName)),
  };
}

function convertToEvalRow(entry: EvalEntry): sheets_v4.Schema$RowData {
  const values = [
    stringCell(entry.path),
    stringCell(entry.description),
    stringCell(entry.env),
    numberCell(entry.numEvents),
    numberCell(entry.numActions),
    stringCell(entry.applications.join(', ')),
    booleanCell(entry.isSkipped),
    booleanCell(entry.expectRecordingFailure),
    booleanCell(entry.recordingSuccess === true),
    booleanCell(entry.executionSuccess === true),
  ];
  return { values };
}

const maxNumRows = 300;
const numColumns = columnNames.length;

export async function writeEvalResultToSheets(entries: EvalEntry[]) {
  try {
    await sheets.spreadsheets.batchUpdate({
      spreadsheetId: EVAL_SPREADSHEET_ID,
      requestBody: {
        requests: [
          {
            updateCells: {
              fields: 'userEnteredValue,dataValidation',
              range: {
                sheetId: EVAL_SHEET_ID,
                startRowIndex: 0,
                endRowIndex: maxNumRows,
                startColumnIndex: 0,
                endColumnIndex: numColumns,
              },
              rows: [
                convertHeaderRow(columnNames),
                ...entries.map((entry) => {
                  return convertToEvalRow(entry);
                }),
              ],
            },
          },
        ],
      },
    });
  } catch (e) {
    logger.error(`Failed to write to Google Sheets: ${e}`);
  }
}
