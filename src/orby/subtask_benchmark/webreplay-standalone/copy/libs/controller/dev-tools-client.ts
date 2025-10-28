import {
  BrowserContext,
  CDPSession,
  ConsoleMessage,
  Page,
  Request,
} from 'playwright';
import { logger } from '../logger';
import {
  ActionVerification,
  ActionVerificationElementAssertion,
  ActionVerificationEvaluateScriptContext,
  ActionVerificationOutgoingRequest,
  ActionVerificationOutgoingRequestMethod,
  ClickType,
} from 'protos/pb/v1alpha1/orbot_action';
import { Modifier } from 'protos/pb/v1alpha1/orbot_replay';
import { extensionId } from '../../constants';
import { sleep } from 'extension/src/utils/timer';
import { debuggerClick } from 'extension/src/workflow/actions/mouse/cdp-mouse';
import { ListResult } from 'extension/src/workflow/types/data-table';
import { expectListAssertions } from './assertions/list';
import { getModifierBits } from 'extension/src/workflow/actions/cdp-utils';
const delayBetweenKeystrokes = 40;
const delayBetweenClicks = 200;

/**
 * Provides wrappers for Chrome DevTools Protocol methods in page context, such
 * as:
 * - evaluate JavaScript
 * - simulate click/type in the page
 */
export class DevToolsClient {
  private readonly context: BrowserContext;
  private readonly page: Page;
  private contextId: number | undefined;
  private client: CDPSession | undefined;

  constructor(context: BrowserContext, page: Page) {
    this.context = context;
    this.page = page;
  }

  /**
   * Evaluate a JavaScript expression in the main frame of the page.
   *
   * Caution: expression has to be a valid javascript expression, or it won't be evaluated
   *
   */
  // TODO: We can still use it, but when we add eval to service-worker, we have to refactor this.
  public async eval<R = any>(
    expression: string,
    context: ActionVerificationEvaluateScriptContext = ActionVerificationEvaluateScriptContext.CONTENT_SCRIPT,
  ): Promise<R> {
    if (context === ActionVerificationEvaluateScriptContext.CONTENT_SCRIPT) {
      this.contextId = await this.connectToExtension();
    } else {
      await this.connectToMainWorld();
      this.contextId = undefined;
    }
    const cb = (msg: ConsoleMessage) => {
      if (msg.type() === 'error') {
        logger.error('Page console error:' + msg.text());
      }
    };
    this.page.on('console', cb);
    let evaluationResult;
    try {
      evaluationResult = await this.client!.send('Runtime.evaluate', {
        expression,
        contextId: this.contextId,
        awaitPromise: true,
      });
    } catch (e: any) {
      // When send CDP command while navigating, this error will be thrown.
      if (e?.message?.includes('Cannot find context with specified id')) {
        // This is a hack to bypass the limitation of networkidle will only check 500ms
        await this.page.waitForLoadState('networkidle');
        await this.page.waitForTimeout(1000);
        await this.page.waitForLoadState('networkidle');

        this.contextId = await this.connectToExtension(true);
        evaluationResult = await this.client!.send('Runtime.evaluate', {
          expression,
          contextId: this.contextId,
          awaitPromise: true,
        });
      } else {
        logger.error(e);
        throw e;
      }
    }
    if (evaluationResult.exceptionDetails) {
      logger.error(JSON.stringify(evaluationResult));
      throw new Error(evaluationResult.exceptionDetails.text);
    }
    this.page.off('console', cb);

    // Process the evaluation result based on its type
    const result = evaluationResult.result;
    switch (result.type) {
      case 'undefined':
        return undefined as R;
      case 'boolean':
        return result.value as R;
      case 'number':
        return result.value as R;
      case 'string':
        return result.value as R;
      case 'object':
        if (result.subtype === 'null') {
          return null as R;
        } else if (result.subtype === 'array') {
          const arrayProperties = await this.getProperties(result.objectId);
          return Object.values(arrayProperties) as R;
        } else {
          return this.getProperties(result.objectId) as R;
        }
      default:
        throw new Error(`Unsupported result type: ${result.type}`);
    }
  }

  public async mouseMoved(position: { x: number; y: number }) {
    await this.connectToExtension();
    await this.client!.send('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      x: position.x,
      y: position.y,
    });
  }

  /**
   * Simulate a user click event.
   */
  public async clickPosition(
    position: { x: number; y: number },
    options?: { type?: ClickType; modifiers?: Modifier[] },
  ) {
    await this.connectToExtension();
    await debuggerClick(
      (method, params) => this.client!.send(method, params),
      position,
      {
        type: options?.type,
        modifiers: options?.modifiers,
      },
    );
    await sleep(delayBetweenClicks);
  }

  /**
   * Send a type command with Chrome DevTools Protocol.
   */
  public async type(text: string, modifierKeys: Modifier | Modifier[] = []) {
    await this.connectToExtension();

    for (const char of text) {
      await this.client!.send('Input.dispatchKeyEvent', {
        type: 'keyDown',
        text: char,
        modifiers: getModifierBits(modifierKeys),
      });
      await sleep(delayBetweenKeystrokes / 2);
      await this.client!.send('Input.dispatchKeyEvent', {
        type: 'keyUp',
        text: char,
        modifiers: getModifierBits(modifierKeys),
      });
      await sleep(delayBetweenKeystrokes / 2);
    }
  }

  public async expect<R>(
    performAction: () => Promise<R>,
    verification: ActionVerification | undefined,
    timeout: number = 8000,
  ): Promise<{ success: boolean; output: R }> {
    // Expect outgoing requests
    let reqPromise = Promise.resolve(true);
    if (verification?.outgoingRequests?.length) {
      reqPromise = this.expectRequests(verification.outgoingRequests, timeout);
    }

    let success = true;
    const output = await performAction();

    // Expect element assertions
    let assertionPromise = Promise.resolve(true);
    if (verification?.elementAssertions?.length) {
      assertionPromise = this.expectElementAssertions(
        verification.elementAssertions,
        timeout,
      );
    }

    // Expect list assertions
    let listAssertionPromise = Promise.resolve(true);
    if (verification?.listAssertion) {
      listAssertionPromise = expectListAssertions(
        verification.listAssertion,
        output as ListResult,
      );
    }

    // Expect evaluate scripts
    for (const script of verification?.evaluateScripts || []) {
      const context =
        script.context || ActionVerificationEvaluateScriptContext.MAIN_WORLD;

      // wait for a bit for the events to be propagated through
      await sleep(100);

      const scriptCode = `
        globalThis.actionContext = {
          output: ${JSON.stringify(output)},
        };
        ${script.script || ''}
      `;
      if (!(await this.eval(scriptCode, context))) {
        let maskedOutput = undefined;
        if (output) {
          maskedOutput = output as Record<string, string>;
          if (maskedOutput['screenshot']) {
            maskedOutput['screenshot'] = '${screenshot data}';
          }
        }
        logger.error(
          `Evaluate script failed, script: ${script.script}, context: ${context}, output: ${JSON.stringify(maskedOutput)}`,
        );
        await this.page.pause();
        success = false;
      }
    }

    const results = await Promise.all([
      reqPromise,
      assertionPromise,
      listAssertionPromise,
    ]);
    if (results[0] === false) {
      success = false;
      logger.error('expect outgoing requests failed');
    }
    if (results[1] === false) {
      success = false;
      logger.error('expect element assertions failed');
    }
    if (results[2] === false) {
      success = false;
      logger.error('expect list assertions failed');
    }
    return { success, output };
  }

  async close() {
    if (this.client) {
      await this.client.send('Runtime.disable');
      await this.client.detach();
      this.contextId = undefined;
    }
  }

  /**
   * Find the contextId for the main frame of the page.
   */
  private connectToExtension(force = false): Promise<number> {
    // eslint-disable-next-line no-async-promise-executor
    return new Promise(async (resolve) => {
      if (!this.client || !this.contextId || force) {
        this.client = await this.context.newCDPSession(this.page);

        const frameTreeResult = await this.client.send('Page.getFrameTree');
        const mainFrameId = frameTreeResult.frameTree.frame.id;

        // We don't store contextId because in some cases, contextId will expire and stored contextId will be invalid.
        this.client.on('Runtime.executionContextCreated', (event) => {
          const context = event.context;
          if (
            context.origin == `chrome-extension://${extensionId}` &&
            context.auxData?.['frameId'] === mainFrameId
          ) {
            resolve(context.id);
          }
        });
        await this.client.send('Runtime.enable');
      }
      resolve(this.contextId!);
    });
  }

  private async connectToMainWorld() {
    if (!this.client) {
      this.client = await this.context.newCDPSession(this.page);
      await this.client.send('Runtime.enable');
    }
  }

  // Function to handle array or object properties
  private async getProperties(objectId: string | undefined | null) {
    if (!this.client) {
      throw new Error('CDPSession not connected');
    }
    if (!objectId) {
      throw new Error('objectId is required');
    }
    const propertiesResult = await this.client.send('Runtime.getProperties', {
      objectId: objectId,
    });

    const properties: Record<string, object> = {};
    for (const prop of propertiesResult.result) {
      if (prop.enumerable) {
        if (prop.value?.type === 'object') {
          const property = await this.getProperties(prop.value?.objectId);
          if (prop.value?.subtype === 'array') {
            properties[prop.name] = Object.values(property);
          } else {
            properties[prop.name] = property;
          }
        } else {
          properties[prop.name] = prop.value?.value;
        }
      }
    }
    return properties;
  }

  // expectRequests should be the subset of the requests
  private async expectRequests(
    expectedRequests: ActionVerificationOutgoingRequest[],
    timeout: number,
  ): Promise<boolean> {
    return new Promise((resolve, reject) => {
      let count = expectedRequests.length;
      const timer = setTimeout(() => {
        this.page.off('request', listener);
        logger.error(`Did not find the expected request within ${timeout}ms`);
        resolve(false);
      }, timeout);
      const listener = (request: Request) => {
        const method = getMethod(request.method());
        const isMatch = expectedRequests.find((r) => {
          // We only verify url and method for now, in the future we can add payload.
          return r.url === request.url() && r.method === method;
        });

        if (isMatch) {
          count--;
        }
        if (count === 0) {
          this.page.off('request', listener);
          clearTimeout(timer);
          resolve(true);
        }
      };
      this.page.on('request', listener);
    });
  }

  private async expectElementAssertions(
    elementAssertions: ActionVerificationElementAssertion[],
    timeout: number,
  ): Promise<boolean> {
    return new Promise((resolve, reject) => {
      const assertions = elementAssertions.map((a) => {
        return this.eval(
          `window.default.getElementAction(${JSON.stringify(a.locator)})`,
        );
      });
      if (assertions.length === 0) {
        resolve(true);
      }
      setTimeout(() => {
        reject('expect element assertion timeout');
      }, timeout);
      Promise.all(assertions).then((results) => {
        resolve(results.every((r) => !!r));
      });
    });
  }
}

function getMethod(method: string): ActionVerificationOutgoingRequestMethod {
  switch (method) {
    case 'GET':
      return ActionVerificationOutgoingRequestMethod.GET;
    case 'POST':
      return ActionVerificationOutgoingRequestMethod.POST;
    case 'PUT':
      return ActionVerificationOutgoingRequestMethod.PUT;
    case 'DELETE':
      return ActionVerificationOutgoingRequestMethod.DELETE;
    default:
      return ActionVerificationOutgoingRequestMethod.UNRECOGNIZED;
  }
}

function sendToContentScript() {}
