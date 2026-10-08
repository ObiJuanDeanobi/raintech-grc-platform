
import { RoutineSaveState } from "./routineSave";

export function RoutineSaveStatus({
  state,
  retry,
  label,
}: {
  state: RoutineSaveState;
  retry: () => void;
  label: string;
}) {
  if (state === "saved") return null;
  return (
    <p className={`routine-save-state ${state}`} aria-live="polite">
      {state === "saving" ? "Saving" : "Save failed"}
      {state === "failed" && (
        <button className="text-button" type="button" onClick={retry} aria-label={`Retry ${label}`}>
          Retry
        </button>
      )}
    </p>
  );
}
