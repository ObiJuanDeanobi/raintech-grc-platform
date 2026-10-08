import { ChevronDown, ChevronRight, FileCheck2 } from "lucide-react";
import { Dispatch, SetStateAction, useEffect, useMemo, useRef } from "react";

import { isDecided, objectivesByRequirement, requirementFamilies } from "../../lib/requirements";
import { statusClass } from "../../lib/status";
import type { RecordIndex, RecordState } from "../../types";

/**
 * CMMC work list (#140): families expand to requirements. Each requirement row
 * carries its derived status and evidence / POA&M markers; objectives are
 * worked on the requirement view, not listed here.
 */
export function RequirementList({
  workList,
  states,
  activeRequirementId,
  search,
  area,
  expanded,
  onExpandedChange,
  onSelect,
  onlyIds = null,
}: {
  workList: RecordIndex[];
  states: Record<string, RecordState>;
  activeRequirementId: string;
  search: string;
  area: string;
  /**
   * Families the user opened or closed, held by the workspace so it survives
   * the reload between requirements. Others are open only when they hold the
   * active requirement.
   */
  expanded: Map<string, boolean>;
  onExpandedChange: Dispatch<SetStateAction<Map<string, boolean>>>;
  onSelect: (requirementId: string) => void;
  /** When set, only these requirements are listed, with their families open (#143). */
  onlyIds?: ReadonlySet<string> | null;
}) {
  const families = useMemo(() => requirementFamilies(workList, states), [workList, states]);
  const objectives = useMemo(() => objectivesByRequirement(workList), [workList]);
  const activeFamily = workList.find((record) => record.record_id === activeRequirementId)?.work_area ?? "";
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.querySelector('[aria-current="true"]')?.scrollIntoView?.({ block: "nearest" });
  }, [activeRequirementId, expanded]);

  const term = search.trim().toLowerCase();
  const matches = (record: RecordIndex) =>
    (!onlyIds || onlyIds.has(record.record_id))
    && (!term || record.title.toLowerCase().includes(term) || record.citation.toLowerCase().includes(term));
  const narrowed = Boolean(term) || Boolean(onlyIds);

  return (
    <div ref={listRef} className="requirement-list" role="navigation" aria-label="Requirements by family">
      {onlyIds && onlyIds.size === 0 && <p className="muted-small requirement-list-empty">Every NOT MET requirement is on an open POA&amp;M item.</p>}
      {families
        .filter((family) => area === "all" || family.name === area)
        .map((family) => {
          const visible = family.requirements.filter(matches);
          if (narrowed && visible.length === 0) return null;
          const open = narrowed || (expanded.get(family.name) ?? family.name === activeFamily);
          return (
            <section key={family.name} className="family-group">
              <button
                type="button"
                className="family-header"
                aria-expanded={open}
                onClick={() => onExpandedChange((current) => new Map(current).set(family.name, !open))}
              >
                {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                <strong>{family.name}</strong>
                <span
                  className={`family-count ${family.decidedCount === family.objectiveCount ? "complete" : ""}`}
                  aria-label={`${family.decidedCount} of ${family.objectiveCount} objectives decided`}
                >
                  {family.decidedCount}/{family.objectiveCount}
                </span>
              </button>
              {open && (
                <ul>
                  {visible.map((requirement) => {
                    const state = states[requirement.record_id];
                    const children = objectives.get(requirement.record_id) ?? [];
                    const withEvidence = children.filter((child) => (states[child.record_id]?.evidence_count ?? 0) > 0).length
                      + ((state?.evidence_count ?? 0) > 0 ? 1 : 0);
                    const decided = children.filter((child) => isDecided(states[child.record_id]?.status)).length;
                    const status = state?.status ?? "";
                    const openPoam = state?.open_poam_count ?? 0;
                    const evidencePending = status === "Met" && state?.verification === "evidence_pending";
                    return (
                      <li key={requirement.record_id}>
                        <button
                          type="button"
                          className={`requirement-row ${requirement.record_id === activeRequirementId ? "active" : ""}`}
                          aria-current={requirement.record_id === activeRequirementId ? "true" : undefined}
                          onClick={() => onSelect(requirement.record_id)}
                        >
                          <span className={`status-dot ${statusClass(status)} ${evidencePending ? "evidence-pending" : ""}`} title={evidencePending ? "Met · evidence pending" : status || "Blank"} aria-hidden="true" />
                          <span className="requirement-row-text">
                            <small title={requirement.citation}>{requirement.record_id}</small>
                            <strong>{requirement.title}</strong>
                          </span>
                          <span className="requirement-markers">
                            <span className="sr-only">Status {status || "Blank"}{evidencePending ? ", evidence pending" : ""}.</span>
                            <span className="marker-count" title="Objectives decided">{decided}/{children.length}</span>
                            {withEvidence > 0 && (
                              <span className="marker evidence" title={`Evidence on ${withEvidence} record(s)`} aria-label={`Evidence on ${withEvidence}`}>
                                <FileCheck2 size={11} />{withEvidence}
                              </span>
                            )}
                            {evidencePending && (
                              <span className="marker evidence-pending" title="Met without current evidence or a documented interview/observation">Evidence pending</span>
                            )}
                            {openPoam > 0 ? (
                              <span className="marker poam" title={`${openPoam} open POA&M item(s)`}>POA&amp;M</span>
                            ) : status === "Not Met" ? (
                              <span className="marker poam-needed" title="Not Met with no open POA&M item">No POA&amp;M</span>
                            ) : null}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          );
        })}
    </div>
  );
}
