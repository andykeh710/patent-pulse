/**
 * Tests for SourceAttribution component (L5).
 */

import { render, screen } from "@testing-library/react";
import { SourceAttribution } from "@/components/ui/SourceAttribution";

describe("SourceAttribution", () => {
  it("renders USPTO attribution with link", () => {
    render(<SourceAttribution office="USPTO" />);
    const link = screen.getByText("U.S. Patent and Trademark Office (uspto.gov)");
    expect(link).toBeInTheDocument();
    expect(link.closest("a")).toHaveAttribute("href", "https://www.uspto.gov");
  });

  it("renders EPO attribution with link", () => {
    render(<SourceAttribution office="EPO" />);
    const link = screen.getByText("European Patent Office (epo.org)");
    expect(link).toBeInTheDocument();
    expect(link.closest("a")).toHaveAttribute("href", "https://www.epo.org");
  });

  it("renders fallback for null/unknown office", () => {
    render(<SourceAttribution office={null} />);
    expect(screen.getByText("Patent office data")).toBeInTheDocument();
    // No link for generic fallback.
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("extracts office from docId", () => {
    render(<SourceAttribution docId="WIPO:PCT123" />);
    expect(
      screen.getByText("World Intellectual Property Organization (wipo.int)")
    ).toBeInTheDocument();
  });
});
