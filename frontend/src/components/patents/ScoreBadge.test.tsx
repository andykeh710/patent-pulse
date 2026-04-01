import { render, screen } from "@testing-library/react";
import { ScoreBadge } from "./ScoreBadge";

describe("ScoreBadge", () => {
  it("renders high score correctly", () => {
    render(<ScoreBadge score={0.85} />);
    expect(screen.getByText("85%")).toBeInTheDocument();
    expect(screen.getByText("(high)")).toBeInTheDocument();
  });

  it("renders medium score correctly", () => {
    render(<ScoreBadge score={0.55} />);
    expect(screen.getByText("55%")).toBeInTheDocument();
    expect(screen.getByText("(medium)")).toBeInTheDocument();
  });

  it("renders low score correctly", () => {
    render(<ScoreBadge score={0.25} />);
    expect(screen.getByText("25%")).toBeInTheDocument();
    expect(screen.getByText("(low)")).toBeInTheDocument();
  });

  it("renders null score with dash", () => {
    render(<ScoreBadge score={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("hides label when showLabel is false", () => {
    render(<ScoreBadge score={0.85} showLabel={false} />);
    expect(screen.getByText("85%")).toBeInTheDocument();
    expect(screen.queryByText("(high)")).not.toBeInTheDocument();
  });
});
