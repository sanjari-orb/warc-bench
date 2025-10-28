import { Action } from 'protos/pb/v1alpha1/orbot_action';
import { Controller } from '../libs/controller/controller';
import { ActionVariableProvider } from 'extension/src/workflow/execution/executor/action-variable-provider';
import { RuntimeVariable } from 'extension/src/workflow/execution/executor/variable';
import { performPrecedingActions } from './utils';
import { BrowserContext } from 'playwright';
import { Replay } from 'protos/pb/v1alpha1/orbot_replay';
import { overrideMainPath } from '../constants';
import { EvalEntry } from '../types';

/**
 * Implement a basic ActionExecutor with variable reference and loop support.
 */
export async function execute(
  replay: Replay,
  browserContext: BrowserContext,
  actions: Action[],
  slowMo: number,
  evalEntry: EvalEntry,
): Promise<boolean> {
  const page = await browserContext.newPage();
  const controller = new Controller(browserContext, page, slowMo);
  await page.addInitScript({
    path: overrideMainPath,
  });
  await performPrecedingActions(controller, replay);
  const variableProvider = new ActionVariableProvider({
    getSecretHandler: () => Promise.resolve(undefined),
  });

  const { clickCount, setValueCount } = countActions(actions);
  const success = await executeActions(
    actions,
    controller,
    variableProvider,
    evalEntry,
  );
  await page.close();

  evalEntry.clickCount = clickCount;
  evalEntry.setValueCount = setValueCount;
  return success;
}

/**
 * Count total click and setValue actions, including those in foreach loops
 */
function countActions(actions: Action[]): {
  clickCount: number;
  setValueCount: number;
} {
  let clickCount = 0;
  let setValueCount = 0;

  for (const action of actions) {
    if (action.click) {
      clickCount++;
    } else if (action.setValue) {
      setValueCount++;
    } else if (action.foreach) {
      // For foreach loops, multiply loop actions by the static length of items if possible
      // Otherwise assume length of 1 for counting purposes
      const loopCount = Array.isArray(action.foreach.items)
        ? action.foreach.items.length
        : 1;

      const { clickCount: nestedClicks, setValueCount: nestedSetValues } =
        countActions(action.foreach.loopActions!);

      clickCount += nestedClicks * loopCount;
      setValueCount += nestedSetValues * loopCount;
    }
  }

  return { clickCount, setValueCount };
}

async function executeActions(
  actions: Action[],
  controller: Controller,
  variableProvider: ActionVariableProvider,
  evalEntry: EvalEntry,
) {
  let hasError = false;
  let successfulClickCount = 0;
  let successfulSetValueCount = 0;

  for (const action of actions) {
    if (action.foreach) {
      const items = (
        await variableProvider.parseParam(action.foreach.items!)
      ).getValue();
      if (!Array.isArray(items)) {
        throw new Error('foreach items should be an array');
      }
      variableProvider.startLoop();

      for (const [index, item] of items.entries()) {
        variableProvider.updateLoopIndex(index);
        variableProvider.setActionOutput(
          action.id!,
          new RuntimeVariable(item, {}),
        );

        const success = await executeActions(
          action.foreach.loopActions!,
          controller,
          variableProvider,
          evalEntry,
        );
        if (!success) {
          return false;
        }
      }
      variableProvider.endLoop(action.foreach);
      continue;
    }

    const { success, result } = await controller.executeAction(
      action,
      variableProvider,
    );
    if (action.id) {
      variableProvider.setActionOutput(
        action.id!,
        new RuntimeVariable(result, {}),
      );
    }

    if (success) {
      if (action.click) {
        successfulClickCount++;
      } else if (action.setValue) {
        successfulSetValueCount++;
      }
    } else {
      hasError = true;
    }
  }

  evalEntry.successfulClickCount = successfulClickCount;
  evalEntry.successfulSetValueCount = successfulSetValueCount;

  return !hasError;
}
