import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import CursorPaginationBar from "@/components/CursorPaginationBar";

describe("CursorPaginationBar", () => {
  it("renders nothing when total is 0", () => {
    const { container } = render(
      <CursorPaginationBar
        page={1} pageSize={25} total={0} itemCount={0} hasMore={false}
        onPrev={() => {}} onNext={() => {}} onPageSize={() => {}}
      />
    );
    expect(container.innerHTML).toBe("");
  });

  it("shows range text", () => {
    render(
      <CursorPaginationBar
        page={1} pageSize={25} total={500} itemCount={25} hasMore={true}
        onPrev={() => {}} onNext={() => {}} onPageSize={() => {}}
      />
    );
    expect(screen.getByText("1–25 of 500")).toBeInTheDocument();
  });

  it("shows page indicator", () => {
    render(
      <CursorPaginationBar
        page={3} pageSize={50} total={200} itemCount={50} hasMore={true}
        onPrev={() => {}} onNext={() => {}} onPageSize={() => {}}
      />
    );
    expect(screen.getByText("Page 3")).toBeInTheDocument();
  });

  it("calls onPrev when Prev is clicked", () => {
    const onPrev = vi.fn();
    render(
      <CursorPaginationBar
        page={2} pageSize={25} total={100} itemCount={25} hasMore={true}
        onPrev={onPrev} onNext={() => {}} onPageSize={() => {}}
      />
    );
    fireEvent.click(screen.getByText("Prev"));
    expect(onPrev).toHaveBeenCalled();
  });

  it("calls onNext when Next is clicked", () => {
    const onNext = vi.fn();
    render(
      <CursorPaginationBar
        page={1} pageSize={25} total={100} itemCount={25} hasMore={true}
        onPrev={() => {}} onNext={onNext} onPageSize={() => {}}
      />
    );
    fireEvent.click(screen.getByText("Next"));
    expect(onNext).toHaveBeenCalled();
  });

  it("disables Prev on first page", () => {
    render(
      <CursorPaginationBar
        page={1} pageSize={25} total={100} itemCount={25} hasMore={true}
        onPrev={() => {}} onNext={() => {}} onPageSize={() => {}}
      />
    );
    expect(screen.getByText("Prev")).toBeDisabled();
  });

  it("disables Next when hasMore is false", () => {
    render(
      <CursorPaginationBar
        page={2} pageSize={25} total={50} itemCount={25} hasMore={false}
        onPrev={() => {}} onNext={() => {}} onPageSize={() => {}}
      />
    );
    expect(screen.getByText("Next")).toBeDisabled();
  });

  it("calls onPageSize when rows per page changes", () => {
    const onPageSize = vi.fn();
    render(
      <CursorPaginationBar
        page={1} pageSize={25} total={100} itemCount={25} hasMore={true}
        onPrev={() => {}} onNext={() => {}} onPageSize={onPageSize}
      />
    );
    fireEvent.change(screen.getByLabelText("Rows per page"), { target: { value: "100" } });
    expect(onPageSize).toHaveBeenCalledWith(100);
  });
});
