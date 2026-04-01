import { render, screen } from "@testing-library/react";
import { PatentCard } from "./PatentCard";
import type { PatentListItem } from "@/lib/types";

const mockPatent: PatentListItem = {
  id: "test-uuid",
  doc_id: "USPTO:12345678",
  publication_number: "12345678",
  title: "Test Patent Title",
  assignees: ["Test Corporation"],
  cpc: ["G06F 21/00", "H04L 9/32"],
  publication_date: "2024-03-15",
  grant_date: "2024-03-15",
  legal_status: "GRANTED",
  interesting_score: 0.75,
  summary_what_it_is: "A test invention for testing purposes",
  estimated_expiry_date: "2044-01-15",
};

describe("PatentCard", () => {
  it("renders patent title", () => {
    render(<PatentCard patent={mockPatent} />);
    expect(screen.getByText("Test Patent Title")).toBeInTheDocument();
  });

  it("renders summary when available", () => {
    render(<PatentCard patent={mockPatent} />);
    expect(
      screen.getByText("A test invention for testing purposes")
    ).toBeInTheDocument();
  });

  it("renders CPC codes", () => {
    render(<PatentCard patent={mockPatent} />);
    expect(screen.getByText("G06F")).toBeInTheDocument();
    expect(screen.getByText("H04L")).toBeInTheDocument();
  });

  it("renders score badge", () => {
    render(<PatentCard patent={mockPatent} />);
    expect(screen.getByText("75%")).toBeInTheDocument();
  });

  it("renders assignee", () => {
    render(<PatentCard patent={mockPatent} />);
    expect(screen.getByText("Test Corporation")).toBeInTheDocument();
  });

  it("handles missing title gracefully", () => {
    const patentWithoutTitle = { ...mockPatent, title: null };
    render(<PatentCard patent={patentWithoutTitle} />);
    expect(screen.getByText("Untitled Patent")).toBeInTheDocument();
  });

  it("handles null score", () => {
    const patentWithoutScore = { ...mockPatent, interesting_score: null };
    render(<PatentCard patent={patentWithoutScore} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
