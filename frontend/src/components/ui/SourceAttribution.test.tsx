/**
 * Tests for SourceAttribution component.
 */

import { render, screen } from "@testing-library/react";
import { SourceAttribution } from "@/components/ui/SourceAttribution";

describe("SourceAttribution", () => {
  it("renders USPTO attribution with link role", () => {
    render(<SourceAttribution office="USPTO" />);
    const el = screen.getByText("U.S. Patent and Trademark Office (uspto.gov)");
    expect(el).toBeInTheDocument();
    expect(el.getAttribute("role")).toBe("link");
  });

  it("renders EPO attribution with link role", () => {
    render(<SourceAttribution office="EPO" />);
    const el = screen.getByText("European Patent Office (epo.org)");
    expect(el).toBeInTheDocument();
    expect(el.getAttribute("role")).toBe("link");
  });

  it("renders fallback for null/unknown office", () => {
    render(<SourceAttribution office={null} />);
    expect(screen.getByText("Patent office data")).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("extracts office from docId", () => {
    render(<SourceAttribution docId="WIPO:PCT123" />);
    expect(
      screen.getByText("World Intellectual Property Organization (wipo.int)")
    ).toBeInTheDocument();
  });
});
