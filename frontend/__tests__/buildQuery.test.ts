import { describe, it, expect } from "vitest";
import { buildQuery, PAGE_SIZES, SORT_OPTIONS } from "@/lib/buildQuery";

describe("buildQuery", () => {
  it("builds query string from params", () => {
    const result = buildQuery({ host: "web01", severity: "high" }, {});
    expect(result).toContain("host=web01");
    expect(result).toContain("severity=high");
  });

  it("prepends ? to query string", () => {
    const result = buildQuery({ host: "web01" }, {});
    expect(result).toMatch(/^\?/);
  });

  it("skips undefined and null values", () => {
    const result = buildQuery({ host: "web01", severity: undefined, risk: null }, {});
    expect(result).toContain("host=web01");
    expect(result).not.toContain("severity");
    expect(result).not.toContain("risk");
  });

  it("skips empty string values", () => {
    const result = buildQuery({ host: "web01", q: "" }, {});
    expect(result).toContain("host=web01");
    expect(result).not.toContain("q=");
  });

  it("includes time params", () => {
    const result = buildQuery({ host: "web01" }, { from: "2025-01-01", to: "2025-12-31" });
    expect(result).toContain("from=2025-01-01");
    expect(result).toContain("to=2025-12-31");
  });

  it("returns empty string for no params", () => {
    const result = buildQuery({}, {});
    expect(result).toBe("");
  });
});

describe("constants", () => {
  it("PAGE_SIZES contains expected values", () => {
    expect(PAGE_SIZES).toContain(25);
    expect(PAGE_SIZES).toContain(50);
    expect(PAGE_SIZES).toContain(100);
  });

  it("SORT_OPTIONS has required fields", () => {
    SORT_OPTIONS.forEach((opt) => {
      expect(opt).toHaveProperty("value");
      expect(opt).toHaveProperty("label");
      expect(typeof opt.value).toBe("string");
      expect(typeof opt.label).toBe("string");
    });
  });
});
