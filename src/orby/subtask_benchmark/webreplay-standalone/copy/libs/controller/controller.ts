import { BrowserContext, Page } from 'playwright';
import { DevToolsClient } from './dev-tools-client';
import { ExtensionProxy } from './extension-proxy';
import {
  PrecedingAction,
  SimulateEvent,
  SimulateEventInstruction,
  SimulateEventKeyboardShortcut,
} from 'protos/pb/v1alpha1/orbot_replay';
import {
  Action,
  ClickAction,
  SetValueAction,
} from 'protos/pb/v1alpha1/orbot_action';
import { ElementLocator } from 'protos/pb/v1alpha1/element';
import { sleep } from 'extension/src/utils/timer';
import { ActionVariableProvider } from 'extension/src/workflow/execution/executor/action-variable-provider';
import { ListElement } from 'extension/src/workflow/types/data-table';
import { Element as PageElement } from 'protos/pb/v1alpha1/element';

/**
 * Wrapper around the following ways to interact with the browser instance to
 * simplify invocation:
 *
 * - {@link DevToolsClient}
 * - {@link ExtensionProxy}
 * - Playwright {@link Page} methods
 */
export class Controller {
  // slow down the evaluation for better visibility, default to 0 ms
  private readonly slowMo: number;
  private readonly page: Page;
  private readonly devToolsClient: DevToolsClient;
  public readonly extensionProxy: ExtensionProxy;

  constructor(context: BrowserContext, page: Page, slowMo: number) {
    this.page = page;
    this.devToolsClient = new DevToolsClient(context, page);
    this.extensionProxy = new ExtensionProxy(context);
    this.slowMo = slowMo;
  }

  public async goto(url: string) {
    await this.page.goto(url);
  }

  public async pause() {
    await this.page.pause();
  }

  /**
   * Simulate user events using DevTools Protocol.
   */
  public async simulateEvent(event: SimulateEvent) {
    await sleep(this.slowMo);
    if (event.click) {
      /**
       * Send a click event which requires:
       * 1. locate the element, scroll into viewport and get the (x,y) position with
       *    extension service worker;
       * 2. send the command with Chrome DevTools Protocol.
       */
      const element = await this.extensionProxy.getElement(
        event.click.locator!,
      );
      if (!element) {
        throw new Error(
          `Cannot find element with locator ${JSON.stringify(event.click.locator)}`,
        );
      }
      const boundingBox = element.boundingBox;

      if (boundingBox) {
        const position = {
          x: boundingBox.x! + boundingBox.width! / 2 + (element.offsetX ?? 0),
          y: boundingBox.y! + boundingBox.height! / 2 + (element.offsetY ?? 0),
        };

        await this.devToolsClient.clickPosition(position, {
          type: event.click.type,
          modifiers: event.click.modifiers,
        });
      }
    } else if (event.type) {
      await this.devToolsClient.type(event.type.text!, event.type.modifiers);
    } else if (event.keyboardShortcut) {
      if (event.keyboardShortcut === SimulateEventKeyboardShortcut.COPY) {
        // TODO: somehow I couldn't get keyboard shortcut to work so using execCommand for now
        await this.page.evaluate(() => {
          document.execCommand('copy');
        });
        // const isMac = process.platform === 'darwin';
        // const modifier = isMac ? Modifier.COMMAND : Modifier.CTRL;
        // await this.devToolsClient.type('c', modifier);
      } else if (
        event.keyboardShortcut === SimulateEventKeyboardShortcut.PASTE
      ) {
        // TODO: somehow I couldn't get keyboard shortcut to work so using execCommand for now
        await this.page.evaluate(() => {
          document.execCommand('paste');
        });
      } else {
        throw new Error(
          `Unsupported keyboard shortcut: ${event.keyboardShortcut}`,
        );
      }
    } else if (event.instruction) {
      if (event.instruction === SimulateEventInstruction.ITERATE_START) {
        await this.extensionProxy.iterateStart();
      } else if (event.instruction === SimulateEventInstruction.ITERATE_END) {
        // give some additional time for buffered events to be processed
        await sleep(100);
        await this.extensionProxy.iterateEnd();
      } else {
        throw new Error(`Unsupported instruction: ${event.instruction}`);
      }
    } else if (event.selection) {
      if (event.selection.element) {
        const cssSelector = event.selection.element.css;
        if (!cssSelector) {
          throw new Error('Only css selector is supported for selection');
        }
        await this.page.evaluate((cssSelector) => {
          const elements = document.querySelectorAll<HTMLElement>(cssSelector);
          if (elements.length > 1) {
            throw new Error(
              `Multiple elements found for selector ${cssSelector}`,
            );
          } else if (elements.length === 0) {
            throw new Error(`No element is found for selector ${cssSelector}`);
          }
          const element = elements[0]!;
          const content = element.innerText;
          const range = document.createRange();
          range.setStart(element.childNodes[0]!, 0);
          range.setEnd(element.childNodes[0]!, content.length);
          const selection = window.getSelection()!;
          selection.removeAllRanges();
          selection.addRange(range);
        }, cssSelector);
      } else {
        throw new Error(`Unsupported selection type: ${event.selection}`);
      }
    } else {
      throw new Error(`Unsupported event type: ${JSON.stringify(event)}`);
    }
  }

  /**
   * Execute actions with extension's module and return if the verification passes.
   *
   * TODO: right now we only support two actions click and setValue without variable
   *       reference, we should use a {@link ActionExecutor} instance for more
   *       complete implementation with more actions and control flows.
   */
  public async executeAction(
    action: Action,
    variableProvider: ActionVariableProvider,
  ): Promise<{
    result?: ListElement[] | PageElement | boolean | null;
    success: boolean;
  }> {
    await sleep(this.slowMo);
    if (action.click) {
      const { success } = await this.devToolsClient.expect(
        () => executeClickAction(this, action.click!),
        action.verification,
        30000,
      );
      return { success };
    } else if (action.setValue) {
      const { success } = await this.devToolsClient.expect(
        async () => {
          await executeSetValueAction(this, action.setValue!);
        },
        action.verification,
        15000,
      );
      return { success };
    } else if (action.getList) {
      const locator = action.getList.listLocator;
      if (!locator) {
        throw new Error('listLocator is required for getList action');
      }
      const { success, output } = await this.devToolsClient.expect(
        async () => {
          return await this.extensionProxy.getList(locator);
        },
        action.verification,
        5000,
      );
      return { success, result: output.data };
    } else if (action.getElement) {
      let locator = action.getElement.locator;
      if (action.getElement.elementLocator) {
        locator = (
          await variableProvider.parseParam(action.getElement.elementLocator)
        ).getValue();
      }
      const { success, output } = await this.devToolsClient.expect(
        async () => {
          return await this.extensionProxy.getElement(locator!);
        },
        action.verification,
        5000,
      );
      return { success, result: output };
    } else if (action.jsFunction) {
      const paramNames = action.jsFunction!.paramNames || [];
      const parsedArgs = await Promise.all(
        action.jsFunction.params!.map((p) => variableProvider.parseParam(p)),
      );
      const params = parsedArgs.map((arg) => arg.getValue());
      const body = action.jsFunction!.body!;
      const result = new Function(...paramNames, body)(...params);
      return { result, success: true };
    } else if (action.updateList) {
      if (!action.updateList.listLocator) {
        throw new Error('listLocator is required for updateList action');
      }
      if (!action.updateList.updates) {
        throw new Error('updates is required for updateList action');
      }
      const locator = (
        await variableProvider.parseParam(action.updateList.listLocator)
      ).getValue();
      const updates = (
        await variableProvider.parseParam(action.updateList.updates)
      ).getValue();
      const { success, output } = await this.devToolsClient.expect(
        () => this.extensionProxy.updateList(locator!, updates),
        action.verification,
        5000,
      );
      return { success, result: output };
    } else {
      throw new Error(`Unsupported action: ${JSON.stringify(action)}`);
    }
  }

  public async close() {
    await this.devToolsClient.close();
  }

  public async performPrecedingAction(action: PrecedingAction) {
    await sleep(this.slowMo);
    if (action.click) {
      return await executeClickAction(this, action.click);
    } else if (action.setValue) {
      return await executeSetValueAction(this, action.setValue);
    }
  }
}

async function executeClickAction(
  controller: Controller,
  clickAction: ClickAction,
) {
  let locator = clickAction.elementLocator;
  if (clickAction.locator?.jsonValue) {
    locator = ElementLocator.fromJSON(
      JSON.parse(clickAction.locator.jsonValue),
    );
  }
  return controller.extensionProxy.click(locator!);
}

function executeSetValueAction(
  controller: Controller,
  setValueAction: SetValueAction,
) {
  let locator: ElementLocator;
  const fieldLocator = setValueAction!.fieldLocator!;
  if (fieldLocator.jsonValue) {
    locator = ElementLocator.fromJSON(JSON.parse(fieldLocator.jsonValue));
  } else {
    throw new Error(`Not supported fieldLocator: ${fieldLocator}`);
  }

  let value: string;
  const fieldValue = setValueAction.fieldValue!;
  if (fieldValue.jsonValue) {
    value = JSON.parse(fieldValue.jsonValue);
  } else {
    throw new Error(`Unsupported fieldValue: ${fieldValue}`);
  }
  return controller.extensionProxy.setValue(locator, value);
}
