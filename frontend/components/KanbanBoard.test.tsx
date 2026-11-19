import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { KanbanBoard } from "./KanbanBoard";
import type { LWI, Sprint } from "@/lib/types";

const sprint: Sprint = {
  id: 1,
  title: "DBMS Sprint",
  course_code: "CS301",
  start_date: "2026-11-03",
  end_date: "2026-11-17",
  co_po_tags: ["CO1"],
  kind: "COURSE",
  lwi_count: 1,
  mastered_count: 0,
  progress_percent: 0,
};

const item: LWI = {
  id: 11,
  sprint_id: 1,
  student_id: 1,
  ticket_code: "CS301-101",
  title: "Explain left joins",
  description: "Write the unmatched-row case",
  type: "TASK",
  status: "BACKLOG",
  story_points: 3,
  skill_tag: "SQL",
  prerequisite_id: null,
  prerequisite_code: null,
  prerequisite_title: null,
  blocked: false,
  block_reason: null,
  co_tag: "CO1",
  rubric_criteria: [],
  ai_feedback: null,
};

describe("KanbanBoard", () => {
  it("moves a ticket with the accessible Move control", async () => {
    const user = userEvent.setup();
    const onMove = vi.fn();
    render(
      <KanbanBoard
        sprint={sprint}
        items={[item]}
        query=""
        onOpen={vi.fn()}
        onMove={onMove}
        onGenerate={vi.fn()}
        onCreate={async () => undefined}
      />,
    );
    await user.selectOptions(screen.getByLabelText(/Move to/i), "IN_PROGRESS");
    expect(onMove).toHaveBeenCalledWith(11, "IN_PROGRESS");
  });
});
