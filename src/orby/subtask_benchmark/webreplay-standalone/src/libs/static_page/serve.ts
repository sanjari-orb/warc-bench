import { BrowserContext } from 'playwright';
import path from 'path';
import { readFile } from 'node:fs/promises';
import fs from 'fs';
import { ReplayEnvStaticPage } from '../../types';

export async function serveStaticPages(
  browserContext: BrowserContext,
  replayFile: string,
  pages: ReplayEnvStaticPage[],
) {
  const replayFolder = path.dirname(replayFile);
  
  for (const page of pages) {
    // serve the main HTML
    const url = page.serveAtUrl || 'https://orbot.test/';
    
    await browserContext.route(url, async (route) => {
      let body: string;
      
      if (page.html) {
        body = page.html;
      } else if (page.filePath) {
        body = await readFile(path.join(replayFolder, page.filePath), {
          encoding: 'utf8',
        });
      } else {
        throw new Error('html and file_path are not defined');
      }
      
      await route.fulfill({ 
        body, 
        headers: { 'content-type': 'text/html' } 
      });
    });

    // serve resources defined for the HTML
    if (page.resources) {
      for (const resource of page.resources) {
        if (!resource.filePath) continue;
        
        let resourceContent: string;
        const resourceFile = path.join(replayFolder, resource.filePath);
        
        resourceContent = fs.readFileSync(resourceFile, 'utf-8');

        let resourcePath = resource.serveAtPath || resource.filePath;
        if (resourcePath.startsWith('./')) {
          resourcePath = url + resourcePath.substring(2);
        }
        
        let resourceType = '';
        if (resourcePath.endsWith('.js')) {
          resourceType = 'text/javascript';
        } else if (resourcePath.endsWith('.css')) {
          resourceType = 'text/css';
        }

        await browserContext.route(resourcePath, async (route) => {
          await route.fulfill({
            body: resourceContent,
            headers: { 'content-type': resourceType },
          });
        });
      }
    }
  }
} 