import { LCGGenerator, SEED } from './generator';

const randomGenerator = new LCGGenerator(SEED);
export const random = (): number => {
  return randomGenerator.next();
}; 