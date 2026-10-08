import { RoutineSaveState } from "./routineSave";

export function RoutineSaveStatus({
  state,
  retry,
  label,
  message = "",
}: {
  state: RoutineSaveState;
  retry: () => void;
  label: string;
  /** The API's reason for a refused save, shown beside the failure (#140). */
  message?: string;
}) {
  if (state === "saved") return null;
  return (
    <p className={`routine-save-state ${state}`} aria-live="polite">
      {state === "saving" ? "Saving" : "Save failed"}
      {state === "failed" && message && <span className="routine-save-reason">{message}</span>}
      {state === "failed" && (
        <button className="text-button" type="button" onClick={retry} aria-label={`Retry ${label}`}>
          Retry
        </button>
      )}
    </p>
  );
}
