import { render, screen } from "@testing-library/react";
import { BriefingItem } from "./BriefingItem";

describe("BriefingItem", () => {
  const base = {
    type: "trend" as const,
    label: "Filing trend · momentum",
    title: "G06T image processing",
    reason: "Shown because you follow NVIDIA",
    source: "USPTO direct",
    freshness: { updated_at: "2026-06-01T08:30:00Z", relative: "2h ago" },
  };

  it("renders title and label", () => {
    render(<BriefingItem {...base} />);
    expect(screen.getByText("G06T image processing")).toBeInTheDocument();
    expect(screen.getByText(/Filing trend/)).toBeInTheDocument();
  });

  it("displays the reason field", () => {
    render(<BriefingItem {...base} />);
    expect(screen.getByText(/Shown because you follow NVIDIA/)).toBeInTheDocument();
  });

  it("displays freshness", () => {
    render(<BriefingItem {...base} />);
    expect(screen.getByText("2h ago")).toBeInTheDocument();
  });

  it("applies trend type accent border", () => {
    const { container } = render(<BriefingItem {...base} type="trend" />);
    // CSS variable — JSDOM doesn't resolve these, check border-left-width instead
    const el = container.firstChild as HTMLElement;
    expect(el.style.borderLeftWidth).toBe("3px");
  });

  it("uses dashed border for news type", () => {
    const { container } = render(<BriefingItem {...base} type="news" />);
    expect(container.firstChild).toHaveClass("border-dashed");
  });
});
