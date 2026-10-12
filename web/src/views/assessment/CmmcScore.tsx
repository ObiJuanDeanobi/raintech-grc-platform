import { Check, ChevronDown, ChevronRight, Minus, X } from "lucide-react";
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

/** One wording everywhere (#144): plain English. */
const PROJECTED_LABEL = "Projected (includes Met awaiting evidence)";

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

const NOT_EVALUATED = "Not yet evaluated";
const NOT_EVALUATED_NOTE = "Evaluated once every requirement is decided.";

function ConditionalChecks({ score, compact = false }: { score: CmmcScore; compact?: boolean }) {
  // Until every requirement is decided a check is neutral, unless decided work has
  // already made it impossible to pass; then it says which decided item did.
  if (!score.all_decided) {
    const failed = score.conditional.checks.filter((check) => score.check_flags?.[check.key]?.state === "failed");
    return (
      <section className="conditional-checks not-evaluated" aria-label="32 CFR 170.21 Conditional status checks">
        <p className="eyebrow">32 CFR 170.21 CONDITIONAL LEVEL 2 · ON THE VERIFIED SCORE</p>
        <p className={`conditional-verdict ${failed.length > 0 ? "fail" : "neutral"}`}>
          Conditional status: <strong>{failed.length > 0 ? "Not eligible" : NOT_EVALUATED}</strong>
          <span> · {failed.length > 0 ? "decided work already fails a check" : NOT_EVALUATED_NOTE}</span>
        </p>
        <ul>
          {score.conditional.checks.map((check) => {
            const flag = score.check_flags?.[check.key];
            const isFailed = flag?.state === "failed";
            return (
              <li key={check.key} className={isFailed ? "fail" : "neutral"}>
                <div className="check-line">
                  {isFailed ? <X size={14} aria-hidden="true" /> : <Minus size={14} aria-hidden="true" />}
                  <strong>{CHECK_TITLES[check.key]}</strong>
                  <span className="check-result">{isFailed ? "Fail" : NOT_EVALUATED}</span>
                  <small>{check.source}</small>
                </div>
                {isFailed && <p>{flag.reason}</p>}
              </li>
            );
          })}
        </ul>
      </section>
    );
  }
  return (
    <section className="conditional-checks" aria-label="32 CFR 170.21 Conditional status checks">
      <p className="eyebrow">32 CFR 170.21 CONDITIONAL LEVEL 2 · ON THE VERIFIED SCORE</p>
      <p className={`conditional-verdict ${score.conditional.eligible ? "pass" : "fail"}`}>
        Conditional status: <strong>{score.conditional.eligible ? "Eligible" : "Not eligible"}</strong>
        {!score.complete && <span> · {score.hints.length > 0 ? score.hints.join(" ") : "assessment not complete"}</span>}
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
              {listed.length > 0 && (() => {
                const items = (
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
                );
                // On the Overview the requirements behind a check stay one click away (#144).
                return compact
                  ? <details className="check-details"><summary>Show the {listed.length} requirement{listed.length === 1 ? "" : "s"} behind this check</summary>{items}</details>
                  : items;
              })()}
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
      {score.started && (
        <>
          <Arithmetic label={`Verified SPRS score ${signed(score.verified.value)}`} figure={score.verified} />
          <Arithmetic label={`Projected score ${signed(score.projected.value)} · counts Met awaiting evidence`} figure={score.projected} secondary />
          <p className="muted-small">
            Only the verified score may appear in a final self-assessment, SPRS figure or client deliverable.
            Point values: {score.methodology}.
          </p>
        </>
      )}
      <ConditionalChecks score={score} />
    </div>
  );
}

function Figures({ score, projectedLabel = PROJECTED_LABEL }: { score: CmmcScore; projectedLabel?: string }) {
  if (!score.started) {
    // A blank assessment would print the worst possible score; say nothing has started instead.
    return (
      <span className="score-verified not-started">
        <span className="eyebrow">VERIFIED SPRS</span>
        <strong>Not started</strong>
        <small>Your score appears once you record the first decision.</small>
      </span>
    );
  }
  return (
    <>
      <span className="score-verified">
        <span className="eyebrow">VERIFIED SPRS</span>
        <strong>{signed(score.verified.value)}</strong>
        <small>of {score.maximum_score}{score.complete ? "" : " · provisional"}</small>
      </span>
      <span className="score-projected" title="Counts evidence-pending Met as Met. Not for SPRS submission.">
        <b>{signed(score.projected.value)}</b> {projectedLabel}
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
    <section className="cmmc-score-line" aria-label="Official CMMC score">
      <Figures score={score} />
      {score.all_decided || Object.values(score.check_flags ?? {}).some((flag) => flag.state === "failed") ? (
        <span className={`score-conditional ${score.all_decided && score.conditional.eligible ? "pass" : "fail"}`}>
          Conditional {score.all_decided && score.conditional.eligible ? "Eligible" : "Not eligible"}
        </span>
      ) : (
        <span className="score-conditional neutral">Conditional {NOT_EVALUATED.toLowerCase()}</span>
      )}
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
        <Figures score={score} projectedLabel={PROJECTED_LABEL} />
      </div>
      {score.hints.length > 0 && <ul className="score-hints">{score.hints.map((hint) => <li key={hint}>{hint}</li>)}</ul>}
      {score.started && (
        <details>
          <summary><ChevronRight size={13} /> Show the arithmetic</summary>
          <Arithmetic label={`Verified SPRS score ${signed(score.verified.value)}`} figure={score.verified} />
          <Arithmetic label={`Projected score ${signed(score.projected.value)} · counts Met awaiting evidence`} figure={score.projected} secondary />
          <p className="muted-small">Only the verified score may appear in a final self-assessment, SPRS figure or client deliverable. Point values: {score.methodology}.</p>
        </details>
      )}
      <ConditionalChecks score={score} compact />
    </section>
  );
}
