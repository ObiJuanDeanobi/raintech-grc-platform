
import { statusClass } from "../lib/status";
import type {
  Status,
} from "../types";

export function StatusPill({ status, derived = false }: { status: Status; derived?: boolean }) {
  return (
    <span className={`status-pill ${statusClass(status)}`}>
      {derived ? `Derived · ${status || "Blank"}` : status || "Blank"}
    </span>
  );
}
