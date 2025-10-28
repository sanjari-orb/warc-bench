import chalk from 'chalk';

export enum LoggingFlag {
  FORWARD_BROWSER_CONSOLE = 'forward_browser_console',
  WARC = 'warc',
}

class Logger {
  isForwardingBrowserConsole = false;
  enableWARCLogging = false;

  info(...args: any[]) {
    console.log(chalk.blue('[INFO]'), ...args);
  }

  success(...args: any[]) {
    console.log(chalk.green('[SUCCESS]'), ...args);
  }

  warn(...args: any[]) {
    console.log(chalk.yellow('[WARN]'), ...args);
  }

  error(...args: any[]) {
    console.error(chalk.red('[ERROR]'), ...args);
  }
}

export const logger = new Logger(); 