import { WARCRecord } from 'warcio';
import { Request, Route } from 'playwright';
import { logger } from '../logger';
import { matchPayload, normalizeUrl } from './utils';
import { payload2String } from './http-parser';

export type WarcIndex = Map<string, Map<WARCRecord, WARCRecord>>;

function* bufferToIterable(buffer: Buffer, chunkSize = 1024) {
  let offset = 0;

  while (offset < buffer.length) {
    yield new Uint8Array(buffer.subarray(offset, offset + chunkSize));
    offset += chunkSize;
  }
}

/**
 * Build a cache between WARC request and response.
 */
export async function createWarcIndex(buffer: Buffer): Promise<WarcIndex> {
  const { WARCParser } = await import('warcio');
  const parser = new WARCParser(bufferToIterable(buffer));

  // 1. associate requests and corresponding responses
  const idToRecords = new Map<string, (WARCRecord | undefined)[]>();
  const responsesWithoutConcurrentTo: WARCRecord[] = [];
  for await (const record of parser) {
    if (record.warcType === 'warcinfo') {
      continue;
    }

    await record.readFully(true);

    if (record.warcType === 'request') {
      const recordId = record.warcHeader('WARC-Record-ID');
      if (!recordId) {
        throw new Error(`Missing WARC-Record-ID header for record: ${record}`);
      }
      const records = idToRecords.get(recordId) || [undefined, undefined];
      records[0] = record;
      idToRecords.set(recordId, records);
    } else {
      const concurrentTo = record.warcHeader('WARC-Concurrent-To');
      if (!concurrentTo) {
        responsesWithoutConcurrentTo.push(record);
        continue;
      }
      const records = idToRecords.get(concurrentTo) || [undefined, undefined];
      records[1] = record;
      idToRecords.set(concurrentTo, records);
    }
  }
  // try to match based on URL for responses without WARC-Concurrent-To
  if (responsesWithoutConcurrentTo.length > 0) {
    if (logger.enableWARCLogging) {
      logger.warn(
        `There are ${responsesWithoutConcurrentTo.length} records without WARC-Concurrent-To header, trying to match based on URLs among ${idToRecords.size} requests`,
      );
    }

    for (const record of responsesWithoutConcurrentTo) {
      // find matching request
      let found = false;
      for (const [requestId, records] of idToRecords) {
        const [request, response] = records;
        if (request?.warcTargetURI === record.warcTargetURI && !response) {
          idToRecords.set(requestId, [request, record]);
          found = true;
          break;
        }
      }
      if (!found) {
        throw new Error(
          `Cannot find request for response record with ID ${record.warcHeader('WARC-Record-ID')}`,
        );
      }
    }
  }

  // 2. group requests by normalized url
  const urlToRequests = new Map<string, Map<WARCRecord, WARCRecord>>();
  for (const [_, records] of idToRecords) {
    const [request, response] = records;
    if (!request || !response) {
      throw new Error(
        `Missing request or response for [${request}, ${response}]`,
      );
    }
    const url = request.warcTargetURI;
    if (!url) {
      throw new Error(`Missing WARC-Target-URI for record ${request}`);
    }

    // Normalize the URL to filter out some runtime parameters such as timestamp, etc.
    const normalizedUrl = normalizeUrl(url);

    const requests =
      urlToRequests.get(normalizedUrl) || new Map<WARCRecord, WARCRecord>();
    requests.set(request, response);
    urlToRequests.set(normalizedUrl, requests);
  }

  // 3. resolve revisit among requests (could be different urls)
  // e.g in JDE1, /jde/share/images/spacer.gif and /jde/img/spacer.gif share the same payload
  const hashToPayload = new Map<string, Uint8Array>();
  for (const [_, reqResMap] of urlToRequests) {
    for (const [_, response] of reqResMap) {
      if (response.warcType === 'response') {
        const hash = excludeAlgorithm(response.warcPayloadDigest!);
        hashToPayload.set(hash, response.payload!);
      }
    }
    for (const [request, response] of reqResMap) {
      if (response.warcType === 'revisit') {
        const hash = excludeAlgorithm(response.warcPayloadDigest!);
        if (!hashToPayload.has(hash)) {
          throw new Error(
            `Cannot find cache for record ${request.warcTargetURI}`,
          );
        }
        response.payload = hashToPayload.get(hash)!;
      }
    }
  }

  return urlToRequests;
}

/**
 * Used for {@link Route.fulfill}
 */
interface PlaywrightResponse {
  body?: string | Buffer;
  contentType?: string;
  headers?: { [key: string]: string };
  status?: number;
}

function convertWarcResponse(
  warcRecord: WARCRecord,
  req: Request,
): PlaywrightResponse {
  const status = Number(warcRecord.httpHeaders!.statusCode);
  const headers: { [key: string]: string } = {};
  warcRecord.httpHeaders!.headers.forEach((value: any, key: string) => {
    headers[key] = value;
  });
  const response: PlaywrightResponse = {
    status,
    headers,
  };

  // Special case for Salesforce
  // Replace the action id from request payload to response payload
  if (
    req
      .url()
      .includes('https://samsara--uat.sandbox.lightning.force.com/aura?r=')
  ) {
    const payload = req.postDataJSON();
    const resp = payload2String(
      warcRecord.payload,
      headers['content-type'] || '',
    );
    const json = JSON.parse(resp);

    const actions = JSON.parse(payload['message']).actions;
    // console.log(actions);
    if (actions.length !== json.actions.length) {
      logger.warn(
        req.url(),
        'Mismatched req actions length: ',
        actions.length,
        'vs WARC response actions length: ',
        json.actions.length,
      );
      // logger.warn(`Mismatched req actions length: ${actions.length} vs WARC response actions length: ${json.actions.length}`);
    }
    // "id":"681;a"
    for (let i = 0; i < actions.length; i++) {
      json.actions[i].id = actions[i].id;
    }
    response.body = JSON.stringify(json);
    return response;
  }

  if (warcRecord.payload) {
    response.body = Buffer.from(warcRecord.payload);
  }
  return response;
}

export function findMatchingResponse(
  req: Request,
  urlToRequest: WarcIndex,
  isLoggingWARC: boolean,
): PlaywrightResponse | undefined {
  const normalizedUrl = normalizeUrl(req.url());
  if (req.url() !== normalizedUrl && isLoggingWARC) {
    logger.info(
      `Finding matching response using normalized url: ${normalizedUrl}`,
    );
  }
  if (
    req
      .url()
      .includes('https://samsara--uat.sandbox.lightning.force.com/aura?r=')
  ) {
    // console.log("normalizedUrl", normalizedUrl);
    // console.log("requests", urlToRequest.get(normalizedUrl)?.size);
  }
  const requests = urlToRequest.get(normalizedUrl);
  if (!requests) {
    return;
  }

  for (const [request, response] of requests) {
    if (request.httpHeaders?.method !== req.method()) {
      continue;
    }

    if (!matchPayload(req, request)) {
      continue;
    }

    return convertWarcResponse(response, req);
  }
  return;
}

/**
 * warcio saves WARC-Payload-Digest inconsistently, sometimes with sha-256 and sometimes with sha256.
 */
function excludeAlgorithm(digest: string): string {
  const splits = digest.split(':');
  if (
    splits.length !== 2 ||
    (splits[0] !== 'sha256' && splits[0] !== 'sha-256') ||
    !splits[1]
  ) {
    throw new Error(`Invalid digest format: ${digest}`);
  }
  return splits[1];
} 