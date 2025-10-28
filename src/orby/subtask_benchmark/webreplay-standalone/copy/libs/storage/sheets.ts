import { sheets_v4 } from '@googleapis/sheets';
import { googleAuth } from './auth';

export const sheets = new sheets_v4.Sheets({ auth: googleAuth });

// https://docs.google.com/spreadsheets/d/1JTk1cq7kf-4DuP_FCLJeHkTgweRtrPes2RszXOrHq9E/edit#gid=0
export const EVAL_SPREADSHEET_ID =
  '1JTk1cq7kf-4DuP_FCLJeHkTgweRtrPes2RszXOrHq9E';
export const EVAL_SHEET_ID = 0;

export function stringCell(
  stringValue: string | undefined,
): sheets_v4.Schema$CellData {
  return {
    userEnteredValue: {
      stringValue,
    },
  };
}

export function numberCell(
  numberValue: number | undefined,
): sheets_v4.Schema$CellData {
  return {
    userEnteredValue: {
      numberValue,
    },
  };
}

export function linkCell(link: string | undefined): sheets_v4.Schema$CellData {
  if (!link) {
    return stringCell(link);
  }
  return {
    userEnteredValue: {
      formulaValue: `=HYPERLINK("${link}","link")`,
    },
    hyperlink: link,
  };
}

export function booleanCell(boolValue: boolean): sheets_v4.Schema$CellData {
  if (!boolValue) {
    return stringCell(undefined);
  }

  return {
    userEnteredValue: {
      boolValue,
    },
    dataValidation: {
      condition: {
        type: 'BOOLEAN',
      },
      showCustomUi: true,
    },
  };
}
