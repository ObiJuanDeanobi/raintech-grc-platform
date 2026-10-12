import { CloseReadinessPanel, PackageGenerationPanel } from "../close/ClosePanels";
import type { RecordIndex } from "../../types";

/** Reports: package generation, review and issue, moved off the Overview (#144). */
export function ReportsView({
  projectId,
  assessmentId,
  records,
  hasClose,
  refreshKey,
  onReopened,
  onNavigate,
}: {
  projectId: string;
  assessmentId: string;
  records: RecordIndex[];
  hasClose: boolean;
  refreshKey: unknown;
  onReopened: () => Promise<void>;
  onNavigate: (link: Record<string, unknown>) => void;
}) {
  return (
    <main className="overview-panel reports-panel">
      <div className="overview-heading">
        <div>
          <p className="eyebrow">REPORTS</p>
          <h1>Reports and packages</h1>
        </div>
      </div>
      {hasClose ? (
        <>
          <CloseReadinessPanel
            key={`close:${projectId}:${assessmentId}:${refreshKey}`}
            projectId={projectId}
            assessmentId={assessmentId}
            onNavigate={onNavigate}
          />
          <PackageGenerationPanel
          key={`package:${projectId}:${assessmentId}:${refreshKey}`}
          projectId={projectId}
          assessmentId={assessmentId}
          records={records}
          onReopened={onReopened}
          />
        </>
      ) : (
        <p className="muted-small">This framework has no package workflow yet.</p>
      )}
    </main>
  );
}
