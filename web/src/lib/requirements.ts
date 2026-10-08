import type { RecordIndex, RecordState, Status } from "../types";

/** Met and Not Met decide an objective; Blank and Pending leave it open. */
export function isDecided(status: Status | undefined): boolean {
  return status === "Met" || status === "Not Met";
}

export interface RequirementFamily {
  name: string;
  requirements: RecordIndex[];
  objectiveCount: number;
  decidedCount: number;
}

export function objectivesByRequirement(workList: RecordIndex[]): Map<string, RecordIndex[]> {
  const byParent = new Map<string, RecordIndex[]>();
  for (const record of workList) {
    if (!record.parent_id) continue;
    const list = byParent.get(record.parent_id) ?? [];
    list.push(record);
    byParent.set(record.parent_id, list);
  }
  return byParent;
}

export function requirementFamilies(
  workList: RecordIndex[],
  states: Record<string, RecordState>,
): RequirementFamily[] {
  const objectives = objectivesByRequirement(workList);
  const families = new Map<string, RequirementFamily>();
  for (const record of workList) {
    if (record.parent_id) continue;
    const family = families.get(record.work_area)
      ?? { name: record.work_area, requirements: [], objectiveCount: 0, decidedCount: 0 };
    family.requirements.push(record);
    for (const objective of objectives.get(record.record_id) ?? []) {
      family.objectiveCount += 1;
      if (isDecided(states[objective.record_id]?.status)) family.decidedCount += 1;
    }
    families.set(record.work_area, family);
  }
  return [...families.values()];
}

/** The requirement an assessment opens on: the first with an undecided objective. */
export function firstActionableRequirement(
  workList: RecordIndex[],
  states: Record<string, RecordState>,
): string {
  const objectives = objectivesByRequirement(workList);
  const requirements = workList.filter((record) => !record.parent_id);
  const actionable = requirements.find((requirement) =>
    (objectives.get(requirement.record_id) ?? []).some((objective) => !isDecided(states[objective.record_id]?.status)),
  );
  return (actionable ?? requirements[0])?.record_id ?? workList[0]?.record_id ?? "";
}
