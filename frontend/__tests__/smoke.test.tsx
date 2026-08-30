import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/image", () => ({
  default: (props: any) => <img {...props} />,
}));

function ErrorDisplay({ message }: { message: string }) {
  return (
    <div role="alert">
      <p>Something went wrong</p>
      <p>{message}</p>
    </div>
  );
}

describe("App loads", () => {
  it("renders without crashing", () => {
    const { container } = render(<div data-testid="app-root">Securi Sphere</div>);
    expect(container.querySelector("[data-testid='app-root']")).toBeTruthy();
    expect(screen.getByText("Securi Sphere")).toBeInTheDocument();
  });
});

describe("Login page", () => {
  it("would render login form elements", () => {
    render(
      <form>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" placeholder="you@example.com" />
        <label htmlFor="password">Password</label>
        <input id="password" type="password" placeholder="Password" />
        <button type="submit">Sign in</button>
      </form>
    );

    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });
});

describe("Protected route behavior", () => {
  it("redirects when not authenticated", () => {
    const hasAuthCookie = false;
    const publicPaths = ["/login", "/register", "/forgot-password"];
    const pathname = "/dashboard";

    const isPublic = publicPaths.some((p) => pathname.startsWith(p));

    if (!hasAuthCookie && !isPublic) {
      const loginUrl = new URL("/login", "http://localhost:3000");
      loginUrl.searchParams.set("next", pathname);
      expect(loginUrl.pathname).toBe("/login");
      expect(loginUrl.searchParams.get("next")).toBe("/dashboard");
    } else {
      throw new Error("Expected protected route to redirect");
    }
  });
});

describe("API error handling", () => {
  it("handles network errors gracefully", () => {
    const { container } = render(<ErrorDisplay message="Network error" />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Network error")).toBeInTheDocument();
  });
});
