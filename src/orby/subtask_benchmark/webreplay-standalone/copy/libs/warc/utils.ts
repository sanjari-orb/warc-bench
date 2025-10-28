import { Request } from 'playwright';
import { WARCRecord } from 'warcio';
import { payload2String } from './http-parser';

type IgnoredParam = string | { key: string; value: string };

/**
 * Filter out some runtime queries like timestamp, etc.
 * e.g
 * - https://example.com/?timestamp=12345 -> https://example.com/?timestamp={timestamp}
 */
export function normalizeUrl(url: string) {
  const keys = ['timestamp', 'amp;timestamp', 'width', 'height', 'r', '_'];
  const urlObj = new URL(url);

  let ignoredParams: IgnoredParam[] = [];

  // TODO: we need a param proceesor to decide whether to keep or ignore a search param
  // for instance, most of google search params aren't useful for us
  // we only need `q` and `start`

  // Ignore search params by key or ignore a key by value
  // e.g.
  // https://www.google.co.uk/search?q=nintendo&start=0
  // search param `start` should only be ignored if its value is 0
  const ignoreKeysByHost: {
    [host: string]: { path: string; keys: IgnoredParam[] };
  } = {
    // google search could have different TLDs e.g. google.com.hk, google.co.uk
    // so we can't match the exact host to filter runtime queries
    google: {
      path: '/search',
      keys: [
        'source',
        'iflsig',
        'uact',
        'gs_lp',
        'sclient',
        'sca_esv',
        'sei',
        'ei',
        'sa',
        'oq',
        'sstk',
        'ved',
        'biw',
        'bih',
        'dpr',
        { key: 'start', value: '0' },
      ],
    },
  };

  Object.keys(ignoreKeysByHost).forEach((host) => {
    const ignored = ignoreKeysByHost[host];
    if (urlObj.host.includes(host) && urlObj.pathname === ignored.path) {
      ignoredParams = ignoredParams.concat(ignored.keys);
    }
  });

  const searchParams = urlObj.searchParams;
  for (const [key, value] of searchParams.entries()) {
    if (keys.includes(key)) {
      searchParams.set(key, `{${key}}`);
    }
  }

  ignoredParams.forEach((param) => {
    if (typeof param === 'string') {
      searchParams.delete(param);
    } else {
      const value = searchParams.get(param.key);
      if (value === param.value) {
        searchParams.delete(param.key);
      }
    }
  });

  return urlObj.toString();
}

export function matchPayload(req: Request, reqRecord: WARCRecord): boolean {
  // Both are empty
  if (
    req.postDataBuffer() === null &&
    (!reqRecord.payload || reqRecord.payload!.length === 0)
  ) {
    return true;
  }
  // Exact match
  if (
    req.postDataBuffer() !== null &&
    reqRecord.payload !== null &&
    req.postDataBuffer()!.equals(reqRecord.payload)
  ) {
    return true;
  }

  // Fuzzy match
  const contentType =
    reqRecord.httpHeaders?.headers.get('content-type') ??
    'no content-type header';
  const recordPayloadStr = payload2String(reqRecord.payload, contentType);
  const reqPayloadStr = req.postData() || '';

  // Normalize externalToken only for JIRA create issue
  if (
    req.url() ===
      'https://orby-ai.atlassian.net/rest/api/3/issue?updateHistory=true&applyDefaultValues=false' ||
    req.url() ===
      'https://orby-ai.atlassian.net/rest/api/3/issue?updateHistory=true&applyDefaultValues=false&skipAutoWatch=true'
  ) {
    const normalizedRecordPayload = recordPayloadStr.replaceAll(
      /"externalToken":"[^"]*"/g,
      '"externalToken":"{externalToken}"',
    );
    const normalizedReqPayload = reqPayloadStr.replaceAll(
      /"externalToken":"[^"]*"/g,
      '"externalToken":"{externalToken}"',
    );

    if (normalizedRecordPayload === normalizedReqPayload) {
      return true;
    }
  }

  // filter out some runtime params like timestamp, etc.
  if (contentType.includes('application/x-www-form-urlencoded')) {
    const normalizedRecordPayload = recordPayloadStr.replaceAll(
      /timestamp=\d+/g,
      'timestamp={timestamp}',
    );
    const normalizedReqPayload = reqPayloadStr.replaceAll(
      /timestamp=\d+/g,
      'timestamp={timestamp}',
    );
    if (normalizedRecordPayload === normalizedReqPayload) {
      return true;
    }
  }

  // Special case match
  // For JDE1 search PO Number case, the payload will contain user action event (mouse position, keyboard actions, etc), we have to extract the PO Number from the payload
  // 0_ctrlVal=12345&event=click&x=123&y=456 -> 12345
  if (
    req.url() ===
    'https://py.e1.jll.com/jde/E1VirtualClient.mafService?e1UserActInfo=true&e1.mode=view&e1.namespace=&RENDER_MAFLET=E1Menu&e1.state=maximized&e1.service=E1VirtualClient'
  ) {
    const reqPONumber = reqPayloadStr.match(/_ctrlVal=(\d+)/)?.[1];
    const recordPONumber = recordPayloadStr.match(/_ctrlVal=(\d+)/)?.[1];
    if (reqPONumber === recordPONumber) {
      return true;
    }
  }

  // Special case match
  // For Samsara aura components lib, they loaded in different order, r represents this order
  if (
    req.url().includes('https://samsara--uat.sandbox.lightning.force.com/aura')
  ) {
    return true;
    // "id":"681;a" -> ""
    const normalizedRecordPayload = recordPayloadStr.replaceAll(
      /%22id%22%3A%22\d+%3B\w%22/g,
      '',
    );
    const normalizedReqPayload = reqPayloadStr.replaceAll(
      /%22id%22%3A%22\d+%3B\w%22/g,
      '',
    );
    if (normalizedRecordPayload === normalizedReqPayload) {
      return true;
    }
  }

  return false;
}
