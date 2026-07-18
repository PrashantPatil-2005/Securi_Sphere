import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import PaginationBar from "@/components/PaginationBar";

describe("PaginationBar", () => {
  it("renders nothing when total is 0", () => {
    const { container } = render(
      <PaginationBar page={1} pageSize={25} total={0} onPage={() => {}} onPageSize={() => {}} />
    );
    expect(container.innerHTML).toBe("");
  });

  it("shows range text", () => {
    render(
      <PaginationBar page={1} pageSize={25} total={100} onPage={() => {}} onPageSize={() => {}} />
    );
    expect(screen.getByText("1–25 of 100")).toBeInTheDocument();
  });

  it("shows correct range for page 2", () => {
    render(
      <PaginationBar page={2} pageSize={25} total={100} onPage={() => {}} onPageSize={() => {}} />
    );
    expect(screen.getByText("26–50 of 100")).toBeInTheDocument();
  });

  it("shows correct page indicator", () => {
    render(
      <PaginationBar page={3} pageSize={50} total={200} onPage={() => {}} onPageSize={() => {}} />
    );
    expect(screen.getByText("3 / 4")).toBeInTheDocument();
  });

  it("calls onPage with page-1 when Prev is clicked", () => {
    const onPage = vi.fn();
    render(
      <PaginationBar page={2} pageSize={25} total={100} onPage={onPage} onPageSize={() => {}} />
    );
    fireEvent.click(screen.getByText("Prev"));
    expect(onPage).toHaveBeenCalledWith(1);
  });

  it("calls onPage with page+1 when Next is clicked", () => {
    const onPage = vi.fn();
    render(
      <PaginationBar page={1} pageSize={25} total={100} onPage={onPage} onPageSize={() => {}} />
    );
    fireEvent.click(screen.getByText("Next"));
    expect(onPage).toHaveBeenCalledWith(2);
  });

  it("disables Prev on first page", () => {
    render(
      <PaginationBar page={1} pageSize={25} total={100} onPage={() => {}} onPageSize={() => {}} />
    );
    expect(screen.getByText("Prev")).toBeDisabled();
  });

  it("disables Next on last page", () => {
    render(
      <PaginationBar page={4} pageSize={25} total={100} onPage={() => {}} onPageSize={() => {}} />
    );
    expect(screen.getByText("Next")).toBeDisabled();
  });

  it("calls onPageSize when rows per page changes", () => {
    const onPageSize = vi.fn();
    render(
      <PaginationBar page={1} pageSize={25} total={100} onPage={() => {}} onPageSize={onPageSize} />
    );
    fireEvent.change(screen.getByLabelText("Rows per page"), { target: { value: "50" } });
    expect(onPageSize).toHaveBeenCalledWith(50);
  });

  it("clamps end to total for partial last page", () => {
    render(
      <PaginationBar page={4} pageSize={25} total={80} onPage={() => {}} onPageSize={() => {}} />
    );
    expect(screen.getByText("76–80 of 80")).toBeInTheDocument();
  });
});
