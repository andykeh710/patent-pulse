// Tests for PatentFiguresPanel — four states and lightbox behavior.

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";

jest.mock("swr", () => ({
  __esModule: true,
  default: jest.fn(),
}));

import useSWR from "swr";

const mockFigures = [
  { ordinal: 1, thumbnail_url: "/thumb/1", full_url: "/full/1", width: 800, height: 600 },
  { ordinal: 2, thumbnail_url: "/thumb/2", full_url: "/full/2", width: 800, height: 600 },
];

describe("PatentFiguresPanel states", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders nothing when figuresStatus is pending", async () => {
    const { PatentFiguresPanel } = await import(
      "@/components/patents/PatentFiguresPanel"
    );
    (useSWR as jest.Mock).mockReturnValue({ data: undefined, isLoading: false, error: undefined });

    const { container } = render(
      <PatentFiguresPanel
        patentId="test-id"
        publicationNumber="US123"
        figuresStatus="pending"
      />
    );

    expect(container.innerHTML).toBe("");
  });

  it("shows skeleton shimmer while loading", async () => {
    const { PatentFiguresPanel } = await import(
      "@/components/patents/PatentFiguresPanel"
    );
    (useSWR as jest.Mock).mockReturnValue({ data: undefined, isLoading: true, error: undefined });

    render(
      <PatentFiguresPanel
        patentId="test-id"
        publicationNumber="US123"
        figuresStatus="complete"
      />
    );

    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders thumbnail strip when figures are available", async () => {
    const { PatentFiguresPanel } = await import(
      "@/components/patents/PatentFiguresPanel"
    );
    (useSWR as jest.Mock).mockReturnValue({
      data: { figures: mockFigures },
      isLoading: false,
      error: undefined,
    });

    render(
      <PatentFiguresPanel
        patentId="test-id"
        publicationNumber="US123"
        figuresStatus="complete"
      />
    );

    expect(screen.getByText(/Patent Figures.*2/)).toBeInTheDocument();
    const buttons = screen.getAllByRole("button", { name: /View figure/ });
    expect(buttons).toHaveLength(2);
  });

  it("renders nothing on fetch error (silent fallback)", async () => {
    const { PatentFiguresPanel } = await import(
      "@/components/patents/PatentFiguresPanel"
    );
    (useSWR as jest.Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("fetch failed"),
    });

    const { container } = render(
      <PatentFiguresPanel
        patentId="test-id"
        publicationNumber="US123"
        figuresStatus="complete"
      />
    );

    expect(container.innerHTML).toBe("");
  });

  it("opens lightbox on thumbnail click and closes on Escape", async () => {
    const { PatentFiguresPanel } = await import(
      "@/components/patents/PatentFiguresPanel"
    );
    (useSWR as jest.Mock).mockReturnValue({
      data: { figures: mockFigures },
      isLoading: false,
      error: undefined,
    });

    render(
      <PatentFiguresPanel
        patentId="test-id"
        publicationNumber="US123"
        figuresStatus="complete"
      />
    );

    const buttons = screen.getAllByRole("button", { name: /View figure/ });
    fireEvent.click(buttons[0]);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute("aria-label", expect.stringContaining("Figure 1"));

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});


describe("PatentCard thumbnail", () => {
  const basePatent = {
    id: "test-id",
    doc_id: "USPTO:123",
    publication_number: "123",
    title: "Test Patent",
    assignees: ["Test Corp"],
    cpc: ["G06F"],
    publication_date: "2024-01-01",
    grant_date: null,
    legal_status: "GRANTED",
    legal_status_confidence: "confirmed" as const,
    interesting_score: 0.75,
    opportunity_score: null,
    tags: null,
    summary_what_it_is: null,
    estimated_expiry_date: null,
    figure_page_url: null,
  };

  it("renders thumbnail when thumbnail_url is provided", async () => {
    const { PatentCard } = await import("@/components/patents/PatentCard");
    const mockPatent = { ...basePatent, thumbnail_url: "/api/v1/patents/test-id/figures/1/thumbnail" };

    render(<PatentCard patent={mockPatent} />);

    const img = screen.getByAltText(/Figure from patent/);
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "/api/v1/patents/test-id/figures/1/thumbnail");
  });

  it("renders no thumbnail when thumbnail_url is null (no layout shift)", async () => {
    const { PatentCard } = await import("@/components/patents/PatentCard");
    const mockPatent = { ...basePatent, thumbnail_url: null };

    render(<PatentCard patent={mockPatent} />);

    expect(screen.queryByAltText(/Figure from patent/)).toBeNull();
    expect(screen.getByText("Test Patent")).toBeInTheDocument();
  });
});
