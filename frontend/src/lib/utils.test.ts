import {
  formatDate,
  truncate,
  formatNumber,
  pluralize,
} from "./utils";

describe("formatDate", () => {
  it("formats valid date string", () => {
    expect(formatDate("2024-03-15")).toBe("Mar 15, 2024");
  });

  it("returns 'Unknown' for null", () => {
    expect(formatDate(null)).toBe("Unknown");
  });

  it("returns 'Unknown' for invalid date", () => {
    expect(formatDate("invalid")).toBe("Unknown");
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
