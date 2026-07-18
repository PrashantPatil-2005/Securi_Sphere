import { describe, it, expect } from "vitest";
import { cn } from "@/lib/utils/cn";

describe("cn", () => {
  it("joins class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("handles single class", () => {
    expect(cn("foo")).toBe("foo");
  });

  it("handles no args", () => {
    expect(cn()).toBe("");
  });

  it("handles falsy values", () => {
    expect(cn("a", false, null, undefined, "b")).toBe("a b");
  });

  it("handles conditional classes", () => {
    const isActive = true;
    expect(cn("base", isActive && "active")).toBe("base active");
  });

  it("handles inactive conditional", () => {
    const isActive = false;
    expect(cn("base", isActive && "active")).toBe("base");
  });
});
