import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ArtifactPanel } from "../artifact-panel";
import { useAppStore } from "@/lib/store";

describe("ArtifactPanel", () => {
  beforeEach(() => {
    useAppStore.getState().reset();
  });

  it("renders all three tabs", () => {
    render(<ArtifactPanel />);
    
    expect(screen.getByRole("tab", { name: /cv/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /preview/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /reviews/i })).toBeInTheDocument();
  });

  it("renders CVEditor component in cv tab by default", () => {
    useAppStore.setState({ artifactTab: "cv" });
    render(<ArtifactPanel />);
    
    expect(screen.getByText("No CV data yet")).toBeInTheDocument();
  });

  it("changes tab when clicked and updates store", () => {
    render(<ArtifactPanel />);
    
    const previewTab = screen.getByRole("tab", { name: /preview/i });
    fireEvent.click(previewTab);
    
    expect(useAppStore.getState().artifactTab).toBe("preview");
    expect(previewTab).toHaveAttribute("aria-selected", "true");
  });
});
