/**
 * Per-objective examine / interview / test notes (#140).
 *
 * They are stored in the objective's existing record note as labelled plain
 * text, so no schema change is needed and the SSP draft, which already quotes
 * objective notes, stays readable:
 *
 *   Examine: Reviewed the access control policy.
 *   Interview: IT manager walked through onboarding.
 *   Test: Attempted login with a disabled account.
 *
 * Text before the first label (for example a note written before #140) is
 * kept as general notes and written back first, unlabelled.
 */
export const NOTE_METHODS = ["examine", "interview", "test"] as const;
export type NoteMethod = (typeof NOTE_METHODS)[number];
export type ObjectiveNotes = Record<NoteMethod | "general", string>;

const LABELS: Record<NoteMethod, string> = { examine: "Examine", interview: "Interview", test: "Test" };
const LABEL_LINE = /^(Examine|Interview|Test):[ \t]?(.*)$/;

export function methodLabel(method: NoteMethod): string {
  return LABELS[method];
}

export function parseObjectiveNotes(note: string): ObjectiveNotes {
  const result: ObjectiveNotes = { general: "", examine: "", interview: "", test: "" };
  let current: keyof ObjectiveNotes = "general";
  const lines: Record<keyof ObjectiveNotes, string[]> = { general: [], examine: [], interview: [], test: [] };
  for (const line of note.split("\n")) {
    const match = LABEL_LINE.exec(line);
    if (match) {
      current = match[1].toLowerCase() as NoteMethod;
      lines[current].push(match[2]);
    } else {
      lines[current].push(line);
    }
  }
  for (const key of Object.keys(lines) as (keyof ObjectiveNotes)[]) {
    result[key] = lines[key].join("\n").trim();
  }
  return result;
}

export function serializeObjectiveNotes(notes: ObjectiveNotes): string {
  const parts: string[] = [];
  if (notes.general.trim()) parts.push(notes.general.trim());
  for (const method of NOTE_METHODS) {
    const text = notes[method].trim();
    if (text) parts.push(`${LABELS[method]}: ${text}`);
  }
  return parts.join("\n");
}
