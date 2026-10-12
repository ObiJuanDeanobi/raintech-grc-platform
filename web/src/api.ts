export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

const locationPrefixes = new Set(["body", "query", "path", "header", "cookie"]);

function formatLocation(location: unknown): string | undefined {
  if (!Array.isArray(location)) return undefined;
  const parts = location.filter(
    (part, index) => !(index === 0 && typeof part === "string" && locationPrefixes.has(part)),
  );
  let result = "";
  for (const part of parts) {
    if (typeof part === "number") {
      result += `[${part}]`;
    } else if (typeof part === "string" && part.length > 0) {
      const readable = part.replaceAll("_", " ");
      result += result ? `.${readable}` : readable;
    }
  }
  return result || undefined;
}

function formatValidationIssue(issue: unknown): string | undefined {
  if (typeof issue === "string") return issue.trim() || undefined;
  if (!issue || typeof issue !== "object") return undefined;

  const value = issue as Record<string, unknown>;
  const message =
    (typeof value.msg === "string" && value.msg.trim()) ||
    (typeof value.message === "string" && value.message.trim());
  if (!message) return undefined;
  const location = formatLocation(value.loc);
  return location ? `${location}: ${message}` : message;
}

function normalizeErrorDetail(detail: unknown): string | undefined {
  if (typeof detail === "string") return detail.trim() || undefined;
  if (Array.isArray(detail)) {
    const issues = detail
      .map(formatValidationIssue)
      .filter((issue): issue is string => Boolean(issue));
    return issues.length > 0 ? issues.join("; ") : undefined;
  }
  if (!detail || typeof detail !== "object") return undefined;

  const value = detail as Record<string, unknown>;
  if ("detail" in value) return normalizeErrorDetail(value.detail);
  if ("errors" in value) return normalizeErrorDetail(value.errors);
  return formatValidationIssue(value);
}

export async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers:
      options?.body instanceof FormData
        ? options.headers
        : { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => undefined);
    const detail = normalizeErrorDetail(payload);
    throw new ApiError(detail ?? "The workspace could not save this change.", response.status);
  }
  return (await response.json()) as T;
}


/** Download a file the API builds on request; an API error becomes a readable message. */
export async function downloadFile(url: string): Promise<string> {
  const response = await fetch(url);
  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => undefined);
    throw new ApiError(normalizeErrorDetail(payload) ?? "The file could not be made.", response.status);
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const name = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "draft.zip";
  const link = document.createElement("a");
  link.href = URL.createObjectURL(await response.blob());
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
  return name;
}

/** Record intake and create the first assessment in one step. */
export function startAssessment(projectId: string): Promise<unknown> {
  return request(`/api/projects/${projectId}/start-assessment`, { method: "POST" });
}
