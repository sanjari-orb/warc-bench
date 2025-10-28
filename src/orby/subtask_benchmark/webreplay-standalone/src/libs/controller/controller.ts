import { BrowserContext, Page } from 'playwright';
import { logger } from '../logger';

export class Controller {
  constructor(
    private readonly browserContext: BrowserContext,
    private readonly page: Page,
    private readonly slowMo: number
  ) {}

  async goto(url: string): Promise<void> {
    logger.info(`Navigating to ${url}`);
    await this.page.goto(url);
    if (this.slowMo > 0) {
      await new Promise(resolve => setTimeout(resolve, this.slowMo));
    }
  }

  async click(selector: string): Promise<void> {
    logger.info(`Clicking on ${selector}`);
    await this.page.click(selector);
    if (this.slowMo > 0) {
      await new Promise(resolve => setTimeout(resolve, this.slowMo));
    }
  }

  async fill(selector: string, value: string): Promise<void> {
    logger.info(`Filling ${selector} with "${value}"`);
    await this.page.fill(selector, value);
    if (this.slowMo > 0) {
      await new Promise(resolve => setTimeout(resolve, this.slowMo));
    }
  }
} 