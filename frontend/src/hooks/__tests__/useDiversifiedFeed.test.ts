import { diversify } from "@/hooks/useDiversifiedFeed";

interface TestItem {
  id: string;
  type: string;
}

const typeOf = (item: TestItem) => item.type;

function make(type: string, n: number): TestItem[] {
  return Array.from({ length: n }, (_, i) => ({
    id: `${type}-${i + 1}`,
    type,
  }));
}

describe("diversify", () => {
  it("returns empty for empty input", () => {
    expect(diversify([], typeOf)).toEqual([]);
  });

  it("passes through single-type items (nothing to interleave)", () => {
    const items = make("opportunity", 3);
    const result = diversify(items, typeOf);
    expect(result).toHaveLength(3);
    expect(result.map(typeOf)).toEqual([
      "opportunity",
      "opportunity",
      "opportunity",
    ]);
  });

  it("interleaves two types so no >2 consecutive same", () => {
    const items = [...make("opportunity", 5), ...make("trend", 3)];
    const result = diversify(items, typeOf, 2);

    // Count consecutive runs
    let maxRun = 1;
    let run = 1;
    for (let i = 1; i < result.length; i++) {
      if (typeOf(result[i]) === typeOf(result[i - 1])) {
        run++;
        maxRun = Math.max(maxRun, run);
      } else {
        run = 1;
      }
    }
    expect(maxRun).toBeLessThanOrEqual(2);
    expect(result).toHaveLength(8);
  });

  it("enforces maxShareOfType as best-effort (impossible when one type dominates)", () => {
    // 8/10 = 80% one type — mathematically impossible to interleave at ≤40%
    // after the other 2 types are exhausted.
    const items = [
      ...make("opportunity", 8),
      ...make("trend", 1),
      ...make("company", 1),
    ];
    const result = diversify(items, typeOf, 2, 0.4);
    expect(result).toHaveLength(10);
    // Verify the first few items are interleaved (before minority types run out)
    const firstFour = result.slice(0, 4).map(typeOf);
    const uniqueInFirstFour = new Set(firstFour);
    expect(uniqueInFirstFour.size).toBeGreaterThanOrEqual(2);
  });

  it("is deterministic — same input → same output", () => {
    const items = [
      ...make("opportunity", 5),
      ...make("trend", 3),
      ...make("company", 2),
    ];
    const r1 = diversify(items, typeOf);
    const r2 = diversify(items, typeOf);
    expect(r1.map((i) => i.id)).toEqual(r2.map((i) => i.id));
  });

  it("interleaves 3 same-type items with others (Image-1 scenario)", () => {
    const items: TestItem[] = [
      { id: "e1", type: "expiry_opportunity" },
      { id: "e2", type: "expiry_opportunity" },
      { id: "e3", type: "expiry_opportunity" },
      { id: "t1", type: "filing_trend" },
      { id: "c1", type: "company_signal" },
    ];
    const result = diversify(items, typeOf, 2);
    const types = result.map(typeOf);

    const firstThree = types.slice(0, 3);
    const allSame = firstThree.every((t) => t === "expiry_opportunity");
    expect(allSame).toBe(false);
  });

  it("backfills when diversification thins the feed", () => {
    const items = make("opportunity", 10);
    const fallback = make("trend", 5);
    const result = diversify(items, typeOf, 2, 0.4, fallback);

    const types = result.map(typeOf);
    expect(types).toContain("trend");
  });
});
