import type { EvidenceReview } from "../types";

/** Enough of a SHA-256 to tell versions apart in a label; the full hash goes in a tooltip (#142). */
export function shortHash(sha256: string): string {
  return sha256.slice(0, 12);
}

/** File name, version and short hash: the label used wherever an artifact is chosen. */
export function artifactLabel(artifact: { name: string; version_number: number; sha256: string }): string {
  return `${artifact.name} · v${artifact.version_number} · ${shortHash(artifact.sha256)}`;
}

export const REVIEW_LABELS: Record<EvidenceReview, string> = {
  current: "Current",
  due_soon: "Due soon",
  stale: "Stale",
};

/** Plain-language review line for one artifact or mapping. */
export function reviewDetail(reviewDate: string | null | undefined, status: EvidenceReview | undefined, days: number | null | undefined): string {
  if (!reviewDate) return "No review date";
  if (status === "stale") return `Review overdue since ${reviewDate}`;
  if (status === "due_soon") {
    if (days === 0) return `Review due today (${reviewDate})`;
    return `Review due in ${days} day${days === 1 ? "" : "s"} (${reviewDate})`;
  }
  return `Review by ${reviewDate}`;
}
