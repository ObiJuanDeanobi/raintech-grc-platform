import { Check, ChevronDown, ChevronRight, X } from "lucide-react";
import { useEffect, useState } from "react";

import { request } from "../../api";
import type { CmmcScore, ConditionalCheck, ScoreFigure, ScoreState } from "../../types";

/**
 * Verified and projected SPRS scores with their arithmetic and the 32 CFR
 * 170.21 Conditional-status checks (#141).
 *
 * The verified score is always the headline. The projected score counts
 * evidence-pending Met as Met; it is always smaller, always labelled, and
 * never rendered without the verified score beside it.
 */

const STATE_LABELS: Record<ScoreState, string> = {
  met: "Verified Met",
  evidence_pending: "Evidence pending",
  not_met: "Not Met",
  pending: "Pending",
  not_assessed: "Not assessed",
};

const PROJECTED_LABEL = "projected (includes evidence pending)";

const CHECK_TITLES: Record<ConditionalCheck["key"], string> = {
  minimum_score: "Minimum score",
  maximum_points: "Every requirement not verified Met is POA&M-eligible",
  excluded: "Requirements never allowed on a POA&M are verified Met",
};

function signed(value: number): string {
  return value < 0 ? `−${-value}` : String(value);
}

function useCmmcScore(projectId: string, assessmentId: string, refreshKey: unknown): CmmcScore | null {
  const [score, setScore] = useState<CmmcScore | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    request<CmmcScore>(`/api/projects/${projectId}/assessments/${assessmentId}/cmmc-score`, { signal: controller.signal })
      .then(setScore)
      .catch(() => undefined);
    return () => controller.abort();
  }, [projectId, assessmentId, refreshKey]);
  return score && score.verified ? score : null;
}

/** Deduction totals grouped by why the requirement does not count as Met. */
function groups(figure: ScoreFigure) {
  const order: ScoreState[] = ["not_met", "evidence_pending", "pending", "not_assessed"];
  return order
    .map((state) => {
      const lines = figure.deductions.filter((line) => line.state === state);
      return { state, count: lines.length, points: lines.reduce((sum, line) => sum + line.points, 0) };
    })
    .filter((group) => group.count > 0);
}

function Arithmetic({ label, figure, secondary }: { label: string; figure: ScoreFigure; secondary?: boolean }) {
  return (
    <div className={`score-arithmetic ${secondary ? "secondary" : ""}`}>
      <p className="eyebrow">{label}</p>
      <code aria-label={`${label} arithmetic`}>{figure.arithmetic}</code>
      {figure.deductions.length > 0 && (
        <ul className="score-groups">
          {groups(figure).map((group) => (
            <li key={group.state}>
              <span>{STATE_LABELS[group.state]}</span>
              <span>{group.count} requirement{group.count === 1 ? "" : "s"}</span>
              <strong>{signed(-group.points)}</strong>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ConditionalChecks({ score }: { score: CmmcScore }) {
  return (
    <section className="conditional-checks" aria-label="32 CFR 170.21 Conditional status checks">
      <p className="eyebrow">32 CFR 170.21 CONDITIONAL LEVEL 2 · ON THE VERIFIED SCORE</p>
      <p className={`conditional-verdict ${score.conditional.eligible ? "pass" : "fail"}`}>
        Conditional status: <strong>{score.conditional.eligible ? "Eligible" : "Not eligible"}</strong>
        {!score.complete && <span> · assessment not complete</span>}
      </p>
      <ul>
        {score.conditional.checks.map((check) => {
          const listed = (check.items ?? []).filter((item) => check.key === "excluded" || item.state !== "not_assessed");
          const notAssessed = (check.items ?? []).length - listed.length;
          return (
            <li key={check.key} className={check.passed ? "pass" : "fail"}>
              <div className="check-line">
                {check.passed ? <Check size={14} aria-hidden="true" /> : <X size={14} aria-hidden="true" />}
                <strong>{CHECK_TITLES[check.key]}</strong>
                <span className="check-result">{check.passed ? "Pass" : "Fail"}</span>
                <small>{check.source}</small>
              </div>
              <p>{check.detail}</p>
              {listed.length > 0 && (
                <ul className="check-items">
                  {listed.map((item) => (
                    <li key={item.record_id} className={item.allowed === false || (check.key === "excluded" && item.state !== "met") ? "fail" : "pass"}>
                      <span>{item.record_id}</span>
                      <span className={`score-state ${item.state}`}>{STATE_LABELS[item.state]}</span>
                      {item.points != null && <span>{item.points} pt</span>}
                      {item.reason && <small>{item.allowed ? "POA&M eligible" : "Not POA&M eligible"}: {item.reason}</small>}
                    </li>
                  ))}
                </ul>
              )}
              {notAssessed > 0 && <p className="muted-small">{notAssessed} not-assessed requirement{notAssessed === 1 ? "" : "s"} also count against this check.</p>}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** Arithmetic for both scores and the 170.21 checks. */
export function CmmcScoreDetails({ score }: { score: CmmcScore }) {
  return (
    <div className="cmmc-score-details">
      <Arithmetic label={`Verified SPRS score ${signed(score.verified.value)}`} figure={score.verified} />
      <Arithmetic label={`Projected score ${signed(score.projected.value)} · ${PROJECTED_LABEL}`} figure={score.projected} secondary />
      <p className="muted-small">
        Only the verified score may appear in an issued self-assessment, SPRS figure or client deliverable.
        Point values: {score.methodology}.
      </p>
      <ConditionalChecks score={score} />
    </div>
  );
}

function Figures({ score }: { score: CmmcScore }) {
  return (
    <>
      <span className="score-verified">
        <span className="eyebrow">VERIFIED SPRS</span>
        <strong>{signed(score.verified.value)}</strong>
        <small>of {score.maximum_score}{score.complete ? "" : " · provisional"}</small>
      </span>
      <span className="score-projected" title="Counts evidence-pending Met as Met. Not for SPRS submission.">
        <b>{signed(score.projected.value)}</b> {PROJECTED_LABEL}
      </span>
    </>
  );
}

/** The score in the requirement view toolbar, with the detail one click away. */
export function CmmcScoreLine({ projectId, assessmentId, refreshKey }: { projectId: string; assessmentId: string; refreshKey: unknown }) {
  const score = useCmmcScore(projectId, assessmentId, refreshKey);
  const [open, setOpen] = useState(false);
  if (!score) return null;
  return (
    <section className="cmmc-score-line" aria-label="Official CMMC score" title={score.blockers.join(" ")}>
      <Figures score={score} />
      <span className={`score-conditional ${score.conditional.eligible ? "pass" : "fail"}`}>
        Conditional {score.conditional.eligible ? "Eligible" : "Not eligible"}
      </span>
      <button type="button" className="score-toggle" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />} Arithmetic and 170.21 checks
      </button>
      {open && (
        <div className="cmmc-score-popover">
          <CmmcScoreDetails score={score} />
        </div>
      )}
    </section>
  );
}

/** The score block on the Overview. */
export function CmmcScorePanel({ projectId, assessmentId, refreshKey }: { projectId: string; assessmentId: string; refreshKey: unknown }) {
  const score = useCmmcScore(projectId, assessmentId, refreshKey);
  if (!score) return null;
  return (
    <section className="cmmc-score" aria-label="CMMC score and Conditional status">
      <div className="cmmc-score-head">
        <Figures score={score} />
      </div>
      {score.blockers.length > 0 && <ul className="cmmc-score-blockers">{score.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul>}
      <details>
        <summary><ChevronRight size={13} /> Show the arithmetic</summary>
        <Arithmetic label={`Verified SPRS score ${signed(score.verified.value)}`} figure={score.verified} />
        <Arithmetic label={`Projected score ${signed(score.projected.value)} · ${PROJECTED_LABEL}`} figure={score.projected} secondary />
        <p className="muted-small">Only the verified score may appear in an issued self-assessment, SPRS figure or client deliverable. Point values: {score.methodology}.</p>
      </details>
      <ConditionalChecks score={score} />
    </section>
  );
}
