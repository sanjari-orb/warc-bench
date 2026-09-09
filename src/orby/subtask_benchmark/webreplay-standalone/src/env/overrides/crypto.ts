import { LCGGenerator, SEED } from './generator';

const randomValuesGenerator = new LCGGenerator(SEED);
const uuidGenerator = new LCGGenerator(SEED);

export const getRandomValues = <T extends ArrayBufferView | null>(
  array: T,
): T => {
  if (!array) return array;
  const bytes = new Uint8Array(array.buffer);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = Math.floor(randomValuesGenerator.next() * 256);
  }
  return array;
};

export const randomUUID =
  (): `${string}-${string}-${string}-${string}-${string}` => {
    const hexDigits = '0123456789abcdef';
    let uuid = '';
    for (let i = 0; i < 32; i++) {
      uuid += hexDigits[Math.floor(uuidGenerator.next() * 16)];
    }
    return uuid as `${string}-${string}-${string}-${string}-${string}`;
  }; 