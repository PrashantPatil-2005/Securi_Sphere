import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import SortSelect from "@/components/SortSelect";

describe("SortSelect", () => {
  it("renders all sort options", () => {
    render(<SortSelect value="newest" onChange={() => {}} />);
    expect(screen.getByText("Newest First")).toBeInTheDocument();
    expect(screen.getByText("Oldest First")).toBeInTheDocument();
    expect(screen.getByText("Severity")).toBeInTheDocument();
    expect(screen.getByText("Risk Score")).toBeInTheDocument();
    expect(screen.getByText("Host Name")).toBeInTheDocument();
    expect(screen.getByText("Alert Count")).toBeInTheDocument();
  });

  it("sets the correct value", () => {
    render(<SortSelect value="severity" onChange={() => {}} />);
    const select = screen.getByRole("combobox");
    expect(select).toHaveValue("severity");
  });

  it("calls onChange when selection changes", () => {
    const onChange = vi.fn();
    render(<SortSelect value="newest" onChange={onChange} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "oldest" } });
    expect(onChange).toHaveBeenCalledWith("oldest");
  });
});
