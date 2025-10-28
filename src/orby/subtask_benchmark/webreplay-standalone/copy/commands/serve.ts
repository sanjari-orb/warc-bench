import { setupEnv } from '../env/setup';
import { BrowserContext } from 'playwright';
import { performPrecedingActions } from '../evaluate/utils';
import { Controller } from '../libs/controller/controller';

export async function serve(
  replayFile: string,
  browserContext: BrowserContext,
  firstTime: boolean = true,
) {
  await setupEnv({
    replayFile,
    browserContext,
    firstTime,
    hook: async (replay) => {
      const page = await browserContext.newPage();
      const controller = new Controller(browserContext, page, 0);
      await performPrecedingActions(controller, replay);
      await page.pause();
    },
  });
}
