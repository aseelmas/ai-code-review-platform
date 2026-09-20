import { test } from "node:test";
import assert from "node:assert/strict";
import { errorMessage, postJson } from "./api.js";

test("validation and plain-text errors are readable", () => {
  assert.equal(errorMessage([{ msg: "Invalid URL" }, { msg: "Missing field" }], "Fallback"), "Invalid URL; Missing field");
  assert.equal(errorMessage("Clone failed", "Fallback"), "Clone failed");
  assert.equal(errorMessage({ unexpected: true }, "Fallback"), "Fallback");
});

test("JSON requests preserve the optional AI setting", async (context) => {
  const fetch = context.mock.method(globalThis, "fetch", async () => ({ ok: true, json: async () => ({ health_score: 90 }) }));
  assert.deepEqual(await postJson("/analyze", { include_ai_review: true }), { health_score: 90 });
  assert.equal(JSON.parse(fetch.mock.calls[0].arguments[1].body).include_ai_review, true);
});

test("backend errors become messages, not rendered objects", async (context) => {
  context.mock.method(globalThis, "fetch", async () => ({ ok: false, json: async () => ({ detail: [{ msg: "Invalid repository URL" }] }) }));
  await assert.rejects(postJson("/analyze", {}), /Invalid repository URL/);
});

test("network failures explain how to recover", async (context) => {
  context.mock.method(globalThis, "fetch", async () => { throw new TypeError("Failed to fetch"); });
  await assert.rejects(postJson("/analyze", {}), /Check that it is running/);
});

test("timeouts have a clear message", async (context) => {
  context.mock.method(globalThis, "fetch", async () => { throw new DOMException("Timeout", "TimeoutError"); });
  await assert.rejects(postJson("/analyze", {}), /timed out/);
});

test("non-JSON responses are handled", async (context) => {
  context.mock.method(globalThis, "fetch", async () => ({ ok: false, json: async () => { throw new SyntaxError("HTML"); } }));
  await assert.rejects(postJson("/analyze", {}), /unreadable response/);
});
