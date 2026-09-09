export const SEED = 1234567890;

interface RandomGenerator {
  get seed(): number;
  next(): number;
}

export class LCGGenerator implements RandomGenerator {
  private _seed: number;

  constructor(seed: number) {
    this._seed = seed;
  }

  get seed(): number {
    return this._seed;
  }

  next(): number {
    // LCG parameters from "Numerical Recipes"
    this._seed = (1664525 * this._seed + 1013904223) % 0x100000000;
    return this._seed / 0x100000000;
  }
} 