import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { GenerationProgress } from "../generation-progress";
import { useAppStore } from "@/lib/store";

describe("GenerationProgress", () => {
  beforeEach(() => {
    useAppStore.getState().reset();
  });

  it("should not render when runStatus is idle", () => {
    const { container } = render(<GenerationProgress />);
    expect(container).toBeEmptyDOMElement();
  });

  it("should show spinner and active step when running", () => {
    useAppStore.setState({
      runStatus: "running",
      activeStep: "generation",
    });

    render(<GenerationProgress />);
    expect(screen.getByText("generation")).toBeInTheDocument();
    // Spinner is rendered (check for svg with animate-spin)
    const spinner = document.querySelector(".animate-spin");
    expect(spinner).toBeInTheDocument();
  });

  it("should show completed steps with checkmarks", () => {
    useAppStore.setState({
      runStatus: "running",
      completedSteps: ["generation", "hr_review"],
      activeStep: "technical_review",
    });

    render(<GenerationProgress />);
    expect(screen.getByText("generation")).toBeInTheDocument();
    expect(screen.getByText("hr_review")).toBeInTheDocument();
    expect(screen.getByText("technical_review")).toBeInTheDocument();
  });

  it("should display reviewer memos", () => {
    useAppStore.setState({
      runStatus: "running",
      liveReviewMemos: [
        {
          reviewer: "HR",
          score: 8,
          summary: "Good alignment",
          suggestions: ["Add metrics"],
        },
      ],
    });

    render(<GenerationProgress />);
    expect(screen.getByText(/HR/)).toBeInTheDocument();
    expect(screen.getByText(/Score: 8/)).toBeInTheDocument();
    expect(screen.getByText("Good alignment")).toBeInTheDocument();
    expect(screen.getByText("Add metrics")).toBeInTheDocument();
  });

  it("should show error alert when generationError is set", () => {
    useAppStore.setState({
      runStatus: "failed",
      generationError: "API timeout",
    });

    render(<GenerationProgress />);
    expect(screen.getByText("Generation Failed")).toBeInTheDocument();
    expect(screen.getByText("API timeout")).toBeInTheDocument();
  });

  it("should show success message when completed", () => {
    useAppStore.setState({
      runStatus: "completed",
    });

    render(<GenerationProgress />);
    expect(screen.getByText("Generation Complete")).toBeInTheDocument();
  });
});
