import { describe, it, expect } from '@jest/globals';
import path from 'path';
import { getReplayActions } from './txtproto';
import { archivesFolderPath } from '../../constants';
import { Replay } from 'protos/pb/v1alpha1/orbot_replay';
import { ActionVerificationOutgoingRequestMethod } from 'protos/pb/v1alpha1/orbot_action';

describe('protobuf', () => {
  it('should parse txtpb file', () => {
    const replayActions = getReplayActions(
      path.join(archivesFolderPath, 'orby-website-test/actions.txtpb'),
    );
    expect(replayActions).toEqual(
      Replay.create({
        description: 'navigate to a page',
        env: {
          warcFilePath: 'gs://orby-warc/orby-website-test.wacz',
          startUrl: 'https://www.orby.ai',
        },
        actions: [
          {
            click: {
              locator: {
                jsonValue:
                  '{"css":"body > div.page-wrapper > div.nav.w-nav > div > div.nav-wrapper > div.nav-right > nav > a:nth-child(1)"}',
              },
            },
            verification: {
              outgoingRequests: [
                {
                  url: 'https://www.orby.ai/platform',
                  method: ActionVerificationOutgoingRequestMethod.GET,
                },
              ],
            },
          },
        ],
      }),
    );
  });
});
