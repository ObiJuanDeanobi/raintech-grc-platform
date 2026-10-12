/**
 * The CMMC package choice (#146, ADR 0023). The gap assessment is the default; the
 * final self-assessment is the internal readiness close and keeps its own gates.
 * The same control sits above the draft button and inside the issue dialog, and the
 * draft and the issue always follow the one choice.
 */
export type PackageType = "gap_assessment" | "readiness_close";

export const DEFAULT_PACKAGE: PackageType = "gap_assessment";

export const PACKAGE_OPTIONS: ReadonlyArray<{ value: PackageType; label: string; sentence: string }> = [
  {
    value: "gap_assessment",
    label: "Gap assessment",
    sentence: "Shows where the client stands today, including requirements that are not met. It can be finalized with gaps.",
  },
  {
    value: "readiness_close",
    label: "Final self-assessment (all requirements Met)",
    sentence: "The close-out once every requirement is Met and verified. It cannot be finalized while any are left.",
  },
];

/** Query string for the draft and checklist calls; empty for frameworks with no choice. */
export function packageQuery(packageType: PackageType | null): string {
  return packageType ? `?package=${packageType}` : "";
}
