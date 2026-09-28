import { expect, test } from "vitest";

import { clientAssessmentProjectsFixture } from "./activeAssessmentFixtures";

const baseAssessment = {
  id: "assessment-1",
  project: { id: "project-1", client_id: "client-1", client_name: "Northwind Health", name: "HIPAA A" },
};

test("same-client and cross-client fixture projects select their own active revision", () => {
  for (const crossClient of [false, true]) {
    const fixture = clientAssessmentProjectsFixture(baseAssessment, {
      crossClient,
      revisionIds: { "project-1": ["a-1", "a-2"], "project-2": ["b-1", "b-2"] },
      activeAssessmentIds: { "project-1": "a-1", "project-2": "b-2" },
    });
    expect(fixture.projects["project-1"].activeAssessment.id).toBe("a-1");
    expect(fixture.projects["project-2"].activeAssessment.id).toBe("b-2");
    expect(fixture.projects["project-1"].activeAssessment.project.client_id
      === fixture.projects["project-2"].activeAssessment.project.client_id).toBe(!crossClient);
    expect(fixture.projects["project-2"].revisions).toHaveLength(2);
  }
});

test("fixture rejects an active ID outside its project's revisions", () => {
  expect(() => clientAssessmentProjectsFixture(baseAssessment, {
    revisionIds: { "project-2": ["b-1"] },
    activeAssessmentIds: { "project-2": "project-1-revision" },
  })).toThrow("active assessment must be included");
});
