
import type {
  Status,
} from "../types";

export function statusClass(status: Status): string {
  return status ? `status-${status.toLowerCase().replaceAll(" ", "-").replace("/", "")}` : "status-blank";
}
