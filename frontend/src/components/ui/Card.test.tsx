import { render, screen } from "@testing-library/react";
import { Card } from "./Card";

describe("Card", () => {
  it("renders children", () => {
    render(<Card>hello</Card>);
    expect(screen.getByText("hello")).toBeInTheDocument();
  });

  it("applies glass variant by default", () => {
    const { container } = render(<Card>x</Card>);
    expect(container.firstChild).toHaveClass("backdrop-blur-md");
  });

  it("adds scan-hover class when interactive", () => {
    const { container } = render(<Card interactive>x</Card>);
    expect(container.firstChild).toHaveClass("scan-hover");
  });

  it("applies elevated variant when passed", () => {
    const { container } = render(<Card variant="elevated">x</Card>);
    expect(container.firstChild).toHaveClass("bg-[var(--bg-elevated)]");
  });
});
