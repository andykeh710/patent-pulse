import { render, screen, act } from "@testing-library/react";
import { UsageWarningBanner } from "../UsageWarningBanner";
import useSWR from "swr";

// Mock SWR
jest.mock("swr", () => ({
  __esModule: true,
  default: jest.fn(),
}));

const mockedUseSWR = useSWR as jest.Mock;

const usageData = (overrides: Record<string, unknown> = {}) => ({
  tier: "free",
  features: {
    views: { used: 0, limit: null, remaining: null, unlimited: true, period: null },
    search: { used: 0, limit: null, remaining: null, unlimited: true, period: null },
    themes: { used: 0, limit: 1, remaining: 1, unlimited: false, period: null },
    companies: { used: 0, limit: 3, remaining: 3, unlimited: false, period: null },
    chat: { used: 0, limit: 5, remaining: 5, unlimited: false, period: "daily" },
  },
  renews_at: null,
  ...overrides,
});

describe("UsageWarningBanner", () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  it("renders nothing when not free tier", () => {
    mockedUseSWR.mockReturnValue({
      data: { ...usageData(), tier: "basic" },
      error: undefined,
    });
    const { container } = render(<UsageWarningBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when usage is below 80%", () => {
    mockedUseSWR.mockReturnValue({
      data: usageData({ features: { ...usageData().features, chat: { used: 2, limit: 5, remaining: 3, unlimited: false, period: "daily" } } }),
      error: undefined,
    });
    const { container } = render(<UsageWarningBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("renders banner at 80% usage threshold", () => {
    mockedUseSWR.mockReturnValue({
      data: usageData({ features: { ...usageData().features, chat: { used: 4, limit: 5, remaining: 1, unlimited: false, period: "daily" } } }),
      error: undefined,
    });
    render(<UsageWarningBanner />);
    expect(screen.getByText(/4\/5/)).toBeInTheDocument();
    expect(screen.getByText("Upgrade →")).toBeInTheDocument();
    expect(screen.getByText("Dismiss")).toBeInTheDocument();
  });

  it("dismisses and writes to localStorage", () => {
    mockedUseSWR.mockReturnValue({
      data: usageData({ features: { ...usageData().features, chat: { used: 4, limit: 5, remaining: 1, unlimited: false, period: "daily" } } }),
      error: undefined,
    });
    render(<UsageWarningBanner />);
    expect(screen.getByText("Dismiss")).toBeInTheDocument();

    act(() => {
      screen.getByText("Dismiss").click();
    });

    // After dismiss, banner should be gone
    expect(screen.queryByText("Dismiss")).not.toBeInTheDocument();

    // localStorage should have dismissal timestamp
    const raw = localStorage.getItem("usage-banner-dismissed-at");
    expect(raw).toBeTruthy();
    const ts = parseInt(raw!, 10);
    expect(ts).toBeGreaterThan(0);
  });

  it("stays hidden when localStorage dismissal is fresh", () => {
    // Pre-set a fresh dismissal
    localStorage.setItem("usage-banner-dismissed-at", String(Date.now()));

    mockedUseSWR.mockReturnValue({
      data: usageData({ features: { ...usageData().features, chat: { used: 5, limit: 5, remaining: 0, unlimited: false, period: "daily" } } }),
      error: undefined,
    });

    const { container } = render(<UsageWarningBanner />);
    // Banner should NOT appear because dismissal is still valid
    expect(container.firstChild).toBeNull();
  });
});
