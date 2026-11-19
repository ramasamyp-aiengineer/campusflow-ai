import { describe, expect, it } from "vitest";

import { COLUMNS, scoreColor } from "./format";
import { sentimentCounts } from "@/components/SentimentCharts";

describe("format helpers", () => {
  it("keeps kanban columns keyboard-describable", () => {
    expect(COLUMNS.every((column) => column.hint.length > 0)).toBe(true);
  });

  it("maps score colors for progress meters", () => {
    expect(scoreColor(80)).toBe("#059669");
    expect(scoreColor(60)).toBe("#D97706");
    expect(scoreColor(20)).toBe("#E11D48");
  });
});

describe("sentimentCounts", () => {
  it("buckets unknown sentiments as Neutral", () => {
    expect(sentimentCounts([{ sentiment: "Positive" }, { sentiment: "Weird" }])).toEqual({
      Positive: 1,
      Watchful: 0,
      Critical: 0,
      Neutral: 1,
    });
  });
});
