import {
  formatDate,
  getScoreLabel,
  getScoreColor,
  truncate,
  formatNumber,
  pluralize,
} from "./utils";

describe("formatDate", () => {
  it("formats valid date string", () => {
    expect(formatDate("2024-03-15")).toBe("Mar 15, 2024");
  });

  it("returns dash for null", () => {
    expect(formatDate(null)).toBe("—");
  });

  it("returns original string for invalid date", () => {
    expect(formatDate("invalid")).toBe("invalid");
  });
});

describe("getScoreLabel", () => {
  it("returns high for scores >= 0.7", () => {
    expect(getScoreLabel(0.9)).toBe("high");
    expect(getScoreLabel(0.7)).toBe("high");
  });

  it("returns medium for scores >= 0.4 and < 0.7", () => {
    expect(getScoreLabel(0.5)).toBe("medium");
    expect(getScoreLabel(0.4)).toBe("medium");
  });

  it("returns low for scores < 0.4", () => {
    expect(getScoreLabel(0.3)).toBe("low");
    expect(getScoreLabel(0.1)).toBe("low");
  });

  it("returns unknown for null", () => {
    expect(getScoreLabel(null)).toBe("unknown");
  });
});

describe("getScoreColor", () => {
  it("returns green for high scores", () => {
    expect(getScoreColor(0.9)).toBe("#22c55e");
  });

  it("returns yellow for medium scores", () => {
    expect(getScoreColor(0.5)).toBe("#eab308");
  });

  it("returns gray for low scores", () => {
    expect(getScoreColor(0.2)).toBe("#6b7280");
  });

  it("returns gray for null", () => {
    expect(getScoreColor(null)).toBe("#6b7280");
  });
});

describe("truncate", () => {
  it("truncates long strings", () => {
    expect(truncate("Hello World", 5)).toBe("Hello...");
  });

  it("returns original if shorter than length", () => {
    expect(truncate("Hi", 10)).toBe("Hi");
  });

  it("handles null", () => {
    expect(truncate(null, 10)).toBe("");
  });
});

describe("formatNumber", () => {
  it("formats large numbers with commas", () => {
    expect(formatNumber(1000000)).toBe("1,000,000");
  });

  it("handles small numbers", () => {
    expect(formatNumber(42)).toBe("42");
  });
});

describe("pluralize", () => {
  it("returns singular for count of 1", () => {
    expect(pluralize(1, "patent")).toBe("patent");
  });

  it("returns plural for count > 1", () => {
    expect(pluralize(5, "patent")).toBe("patents");
  });

  it("uses custom plural if provided", () => {
    expect(pluralize(5, "person", "people")).toBe("people");
  });
});
