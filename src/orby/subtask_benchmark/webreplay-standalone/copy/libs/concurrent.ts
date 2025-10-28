export class Concurrent<T = any> {
  maxConcurrency = 0;
  currentConcurrency = 0;

  private indexBuffer: SharedArrayBuffer;
  private indexView: Int32Array;

  private tasks: T[] = [];
  pedding: (() => Promise<void>)[] = [];
  constructor(total: number) {
    this.maxConcurrency = total;
    this.indexBuffer = new SharedArrayBuffer(4);
    this.indexView = new Int32Array(this.indexBuffer);
  }

  public getNextTask(): T | null {
    const baseIndex = Atomics.load(this.indexView, 0);
    const newIndex = Atomics.compareExchange(
      this.indexView,
      0,
      baseIndex,
      baseIndex + 1,
    );
    console.info('Cases index is ', newIndex);
    return newIndex < this.tasks.length ? this.tasks[newIndex] : null;
  }

  initTasks(tasks: T[]) {
    this.tasks = tasks;
    Atomics.store(this.indexView, 0, 0);
  }

  append(fn: () => Promise<void>) {
    this.pedding.push(fn);
    this.run();
  }

  run() {
    if (!this.pedding.length || this.currentConcurrency >= this.maxConcurrency)
      return;
    const fn = this.pedding.shift();
    if (!fn) {
      return;
    }
    this.currentConcurrency++;
    fn().finally(() => {
      this.currentConcurrency--;
      this.run();
    });
  }
  async waitForCompletion(): Promise<void> {
    return new Promise<void>((resolve) => {
      const checkCompletion = () => {
        if (this.currentConcurrency === 0 && this.pedding.length === 0) {
          resolve();
        } else {
          setTimeout(checkCompletion, 5000);
        }
      };
      checkCompletion();
    });
  }
}
