// A failed "Create and start" still opens the new project, on the Start card.
// The create screens hand the reason over here so the card can show it.
let pendingStartError = "";

export function setStartError(message: string): void {
  pendingStartError = message;
}

export function takeStartError(): string {
  const message = pendingStartError;
  pendingStartError = "";
  return message;
}
