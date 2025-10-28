import { payload2String } from './http-parser';

describe('http-parser.ts', () => {
  it('should return empty for null uint8array', async () => {
    const payload = null;
    const contentType = 'application/json';
    expect(payload2String(payload, contentType)).toBe('');
  });

  it('should parse application/x-www-form-urlencoded', async () => {
    const payload = new TextEncoder().encode('name=John&age=30');
    const contentType = 'application/x-www-form-urlencoded';
    expect(payload2String(payload, contentType)).toBe('name=John&age=30');
  });

  it('should parse application/json', async () => {
    const payload = new TextEncoder().encode('{"name":"John","age":30}');
    const contentType = 'application/json';
    expect(payload2String(payload, contentType)).toBe(
      '{"name":"John","age":30}',
    );
  });

  it('should parse application/javascript', async () => {
    const payload = new TextEncoder().encode("console.log('Hello, World!');");
    const contentType = 'application/javascript';
    expect(payload2String(payload, contentType)).toBe(
      "console.log('Hello, World!');",
    );
  });

  it('should parse application/xml', async () => {
    const payload = new TextEncoder().encode(
      '<note><to>Tove</to><from>Jani</from></note>',
    );
    const contentType = 'application/xml';
    expect(payload2String(payload, contentType)).toBe(
      '<note><to>Tove</to><from>Jani</from></note>',
    );
  });

  it('should parse text/html', async () => {
    const payload = new TextEncoder().encode(
      '<html><body><h1>Hello, World!</h1></body></html>',
    );
    const contentType = 'text/html';
    expect(payload2String(payload, contentType)).toBe(
      '<html><body><h1>Hello, World!</h1></body></html>',
    );
  });

  it('should parse text/plain', async () => {
    const payload = new TextEncoder().encode('Hello, World!');
    const contentType = 'text/plain';
    expect(payload2String(payload, contentType)).toBe('Hello, World!');
  });
});
