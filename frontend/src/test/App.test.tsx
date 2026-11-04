import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../App";

describe("App smoke test", () => {
  it("renders platform title", () => {
    render(<App />);
    expect(screen.getByText("Enterprise Billing Automation")).toBeInTheDocument();
  });
});
