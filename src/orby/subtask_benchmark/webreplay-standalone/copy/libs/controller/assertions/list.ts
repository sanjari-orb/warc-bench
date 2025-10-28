import { ListResult } from 'extension/src/workflow/types/data-table';
import { ActionVerificationListAssertion } from 'protos/pb/v1alpha1/orbot_action';
import { logger } from '../../logger';

const LENGTH_SCORE = 5;
const COLUMNS_SCORE = 5;
const KEY_SCORE = 2;
const VALUE_SCORE = 1;

/**
 * This function will check if all assertions are met.
 * The reason we use score is that in the future, we will return reward score [0, 1] for each expect.
 * This can help us better understand the performance of getList.
 * @param listAssertion list assertion
 * @param output getList output
 * @returns if all assertions are met
 */
export async function expectListAssertions(
  listAssertion: ActionVerificationListAssertion,
  output: ListResult,
): Promise<boolean> {
  const totalScore = getTotalScore(listAssertion);
  let score = 0;
  const list = output.data;
  if (listAssertion.length !== undefined) {
    if (list.length !== listAssertion.length.equal) {
      logger.error(
        `List length assertion failed, expected: ${listAssertion.length.equal}, actual: ${list.length}`,
      );
    } else {
      score += LENGTH_SCORE;
    }
  }
  if (listAssertion.columns !== undefined) {
    if (list[0].values.length !== listAssertion.columns.equal) {
      logger.error(
        `List columns assertion failed, expected: ${listAssertion.columns.equal}, actual: ${list[0].values.length}`,
      );
    } else {
      score += COLUMNS_SCORE;
    }
  }
  if (listAssertion.values !== undefined) {
    listAssertion.values.forEach((value) => {
      const index = value.index;
      if (index === undefined) {
        throw new Error('index is required');
      }
      const fields = value.fields;
      if (fields === undefined) {
        throw new Error('fields is required');
      }
      const row = list[index];
      fields.forEach((field) => {
        const key = field.key;
        const text = field.text;
        if (text === undefined) {
          throw new Error('text is required');
        }
        const value = row.values.find((v) => {
          if (v.key === key) {
            score += KEY_SCORE;
            return true;
          }
          return false;
        })?.value;
        if (value === undefined) {
          logger.error(
            `List value assertion failed, expected key: ${key}, actual value: ${value}`,
          );
        }
        if (!text.equal && !text.contains) {
          throw new Error(
            'text.equal or text.contains is required and at least one of them must be truthy (empty string is not allowed)',
          );
        }
        if (text.equal) {
          if (value !== text.equal) {
            logger.error(
              `List value assertion failed, expected key: ${key}, value equal: ${text.equal}, actual value: ${value}`,
            );
          } else {
            score += VALUE_SCORE;
          }
        }
        if (text.contains) {
          if (!value?.includes(text.contains)) {
            logger.error(
              `List value assertion failed, expected key: ${key}, value contains: ${text.contains}, actual value: ${value}`,
            );
          } else {
            score += VALUE_SCORE;
          }
        }
      });
    });
  }
  // For now, we still return boolean, but in the future, we will return score [0, 1].
  if (score === totalScore) {
    return true;
  }
  logger.error(`List assertion failed, output: ${JSON.stringify(output)}`);
  return false;
}

/**
 * This assume all assertions are met, and return maximum score.
 */
function getTotalScore(listAssertion: ActionVerificationListAssertion): number {
  let score = 0;
  if (listAssertion.length?.equal !== undefined) {
    score += LENGTH_SCORE;
  }
  if (listAssertion.columns?.equal !== undefined) {
    score += COLUMNS_SCORE;
  }
  if (listAssertion.values !== undefined) {
    listAssertion.values.forEach((value) => {
      if (value.fields) {
        score += value.fields.length * KEY_SCORE;
        score += value.fields.length * VALUE_SCORE;
      }
    });
  }
  return score;
}
