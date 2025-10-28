import { Replay } from 'protos/pb/v1alpha1/orbot_replay';
import { Controller } from '../libs/controller/controller';

export async function performPrecedingActions(
  controller: Controller,
  replay: Replay,
) {
  if (replay.env?.startUrl) {
    await controller.goto(replay.env.startUrl);
  } else if (!replay.actions?.[0]?.goto) {
    await controller.goto('https://orbot.test/');
  }

  if (replay.env?.precedingActions) {
    for (const action of replay.env.precedingActions) {
      await controller.performPrecedingAction(action);
    }
  }
}
