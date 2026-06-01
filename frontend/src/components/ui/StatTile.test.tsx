import { render, screen } from "@testing-library/react";
import { StatTile } from "./StatTile";

// Mock Counter since it uses IntersectionObserver
jest.mock("./Counter", () => ({
  Counter: ({ value }: { value: number }) => <span>{value.toLocaleString()}</span>,
}));

describe("StatTile", () => {
  it("renders label, value, and subtext", () => {
    render(<StatTile label="Index size" value={64231} subtext="USPTO · EPO · WIPO" />);
    expect(screen.getByText("Index size")).toBeInTheDocument();
    expect(screen.getByText("64,231")).toBeInTheDocument();
    expect(screen.getByText("USPTO · EPO · WIPO")).toBeInTheDocument();
  });

  it("uses tabular-nums for the value", () => {
    const { container } = render(<StatTile label="x" value={100} />);
    expect(container.querySelector(".tabular-nums")).toBeInTheDocument();
  });

  it("applies signal accent border when accent=signal", () => {
    const { container } = render(<StatTile label="x" value={1} accent="signal" />);
    expect(container.firstChild).toHaveClass("border-[var(--signal-blue)]/40");
  });

  it("applies warning accent border when accent=warning", () => {
    const { container } = render(<StatTile label="x" value={1} accent="warning" />);
    expect(container.firstChild).toHaveClass("border-[var(--warning)]/40");
  });
});
