import chalk from 'chalk';

export enum LoggingFlag {
  FORWARD_BROWSER_CONSOLE = 'forward_browser_console',
  WARC = 'warc',
}

export class Logger {
  private _isForwardingBrowserConsole = false;
  private _enableWARCLogging = false;

  get isForwardingBrowserConsole() {
    return this._isForwardingBrowserConsole;
  }

  set isForwardingBrowserConsole(value: boolean) {
    this._isForwardingBrowserConsole = value;
  }

  get enableWARCLogging() {
    return this._enableWARCLogging;
  }

  set enableWARCLogging(value: boolean) {
    this._enableWARCLogging = value;
  }

  error(...args: unknown[]) {
    console.error(chalk.red(args));
  }
  info(...args: unknown[]) {
    console.log(chalk.blue(args));
  }
  success(...args: unknown[]) {
    console.log(chalk.green(args));
  }
  warn(...args: unknown[]) {
    console.log(chalk.yellow(args));
  }
  diff(changes: Diff.Change[]) {
    for (const change of changes) {
      if (change.added) {
        console.log(chalk.green(`+ ${change.value}`));
      } else if (change.removed) {
        console.log(chalk.red(`- ${change.value}`));
      } else {
        console.log(chalk.gray(`  ${change.value}`));
      }
    }
  }
}

// TODO: Use instance-based logging instead of singleton
export const logger = new Logger();
