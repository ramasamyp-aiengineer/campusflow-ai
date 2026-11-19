import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Ring } from "./Ring";

describe("Ring", () => {
  it("exposes a labeled progress image", () => {
    render(<Ring value={72} label="Semester progress" />);
    expect(screen.getByRole("img", { name: "Semester progress: 72 percent" })).toBeInTheDocument();
  });
});
