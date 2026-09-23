import { beforeEach, expect, test, vi } from "vitest";

import { request } from "./api";

beforeEach(() => {
  vi.restoreAllMocks();
});

test("formats FastAPI validation details as readable field errors", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [
            {
              type: "missing",
              loc: ["body", "profile_version_id"],
              msg: "Field required",
              input: { secret: "must not be shown" },
            },
            {
              type: "string_type",
              loc: ["body", "items", 0, "environment_type"],
              msg: "Input should be a valid string",
            },
          ],
        }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ),
    ),
  );

  await expect(request("/api/projects/project-1/sra/scope", { method: "PUT" })).rejects.toMatchObject({
    name: "Error",
    message: "profile version id: Field required; items[0].environment type: Input should be a valid string",
    status: 422,
  });
});

test("preserves string API details and uses a fallback for unreadable details", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "This profile version is stale." }), { status: 409 }),
    )
    .mockResolvedValueOnce(new Response("not json", { status: 500 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(request("/api/profile")).rejects.toMatchObject({
    message: "This profile version is stale.",
    status: 409,
  });
  await expect(request("/api/profile")).rejects.toMatchObject({
    message: "The workspace could not save this change.",
    status: 500,
  });
});
