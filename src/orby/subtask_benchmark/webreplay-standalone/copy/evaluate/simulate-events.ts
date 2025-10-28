import { Replay, SimulateEvent } from 'protos/pb/v1alpha1/orbot_replay';
import { recordingOverrideMainPath } from '../constants';
import { Controller } from '../libs/controller/controller';
import { logger } from '../libs/logger';
import { BrowserContext } from 'playwright';
import { performPrecedingActions } from './utils';
import { Action } from 'protos/pb/v1alpha1/orbot_action';
import { sleep } from 'extension/src/utils/timer';

export async function simulateEvents(
  replay: Replay,
  browserContext: BrowserContext,
  slowMo: number,
) {
  logger.info('Simulating recording events');
  const page = await browserContext.newPage();
  const controller = new Controller(browserContext, page, slowMo);
  await page.addInitScript({
    path: recordingOverrideMainPath,
  });
  await performPrecedingActions(controller, replay);
  const generatedActions = await simulateRecordingEvents(
    replay.events ?? [],
    controller,
  );
  await page.close();
  return generatedActions;
}

/**
 * Simulate recording process and return the generated {@link Action}s
 */
async function simulateRecordingEvents(
  events: SimulateEvent[],
  controller: Controller,
): Promise<Action[]> {
  await controller.extensionProxy.startTestRecorder();
  for (const event of events) {
    await controller.simulateEvent(event);

    // This is the delay to make sure the event is recorded correctly
    await sleep(500);
  }
  // give it some time for the event buffer to clear (such as input and click)
  await sleep(5000);
  const recordingActions = await controller.extensionProxy.stopTestRecorder();
  return recordingActions.map((rc) => Action.fromJSON(rc));
}
