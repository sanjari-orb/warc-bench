import { BrowserContext } from 'playwright';
import { WarcMetadata } from './wacz';

/**
 * This function initializes the browser state including:
 * - cookie, localStorage, sessionStorage.
 *
 * TODO: support IndexDB, etc.
 */
export async function initBrowserState(
  metadata: WarcMetadata,
  context: BrowserContext,
) {
  const { cookies, localStorage, sessionStorage } = metadata.browserState || {};

  // Cookies
  if (cookies) {
    await context.addCookies(cookies);
  }

  // localStorage and sessionStorage
  if (localStorage || sessionStorage) {
    await context.addInitScript(
      ({ localStorage, sessionStorage }) => {
        const local = localStorage?.[window.location.origin];
        if (local) {
          for (const [key, value] of Object.entries(local)) {
            window.localStorage.setItem(key, value);
          }
        }

        const session = sessionStorage?.[window.location.origin];
        if (session) {
          for (const [key, value] of Object.entries(session)) {
            window.sessionStorage.setItem(key, value);
          }
        }
      },
      { localStorage, sessionStorage },
    );
  }
} 