import { BrowserContext, Worker } from 'playwright';
import { ServerWorkerTestMethods } from 'extension/src/test-methods';
import { extensionId } from '../../constants';
import { ElementLocator } from 'protos/pb/v1alpha1/element';
import { FieldUpdate } from 'protos/pb/v1alpha1/orbot_action';

/**
 * Proxy to call test methods exposed by the extension's service worker.
 */
export class ExtensionProxy implements ServerWorkerTestMethods {
  private readonly extensionWorker: Worker;

  constructor(browserContext: BrowserContext) {
    const [extensionWorker] = browserContext
      .serviceWorkers()
      .filter((worker) =>
        worker.url().startsWith(`chrome-extension://${extensionId}`),
      );

    if (!extensionWorker) {
      throw new Error('Extension service worker is not ready yet');
    }
    this.extensionWorker = extensionWorker;
  }

  private async executeExtensionMethod<T extends keyof ServerWorkerTestMethods>(
    methodName: T,
    ...args: Parameters<ServerWorkerTestMethods[T]>
  ): Promise<ReturnType<ServerWorkerTestMethods[T]>> {
    const pageFunc = ([methodName, ...args]: [
      T,
      ...Parameters<ServerWorkerTestMethods[T]>,
    ]) => {
      return (self as unknown as ServerWorkerTestMethods)[methodName](
        // @ts-expect-error TS2556: Typescript doesn't like we spread message.payload this way.
        ...args,
      ) as ReturnType<ServerWorkerTestMethods[T]>;
    };
    return await this.extensionWorker.evaluate<
      ReturnType<ServerWorkerTestMethods[T]>,
      any
    >(pageFunc, [methodName, ...args]);
  }

  public async startTestRecorder() {
    return this.executeExtensionMethod('startTestRecorder');
  }
  public async stopTestRecorder() {
    return this.executeExtensionMethod('stopTestRecorder');
  }
  public async iterateStart() {
    return this.executeExtensionMethod('iterateStart');
  }
  public async iterateEnd() {
    return this.executeExtensionMethod('iterateEnd');
  }
  public async getElement(locator: ElementLocator) {
    return this.executeExtensionMethod('getElement', locator);
  }
  public async getList(locator: ElementLocator) {
    return this.executeExtensionMethod('getList', locator);
  }
  public async updateList(locator: ElementLocator, updates: FieldUpdate[]) {
    return this.executeExtensionMethod('updateList', locator, updates);
  }
  public async click(locator: ElementLocator) {
    return this.executeExtensionMethod('click', locator);
  }
  public async setValue(locator: ElementLocator, value: string) {
    return this.executeExtensionMethod('setValue', locator, value);
  }
}
