import { test } from "node:test";
import assert from "node:assert/strict";
import { resolveApiUrl } from "./config.js";

test("local development retains its default backend", () => {
  assert.equal(resolveApiUrl(undefined), "http://127.0.0.1:8000");
  assert.equal(resolveApiUrl(" http://localhost:8001/ "), "http://localhost:8001");
});

test("production uses the configured URL without duplicate slashes", () => {
  assert.equal(resolveApiUrl(" https://api.example.test/api/ ", true), "https://api.example.test/api");
});

for (const value of [undefined, "", "   ", "http://api.example.test", "https://localhost", "https://127.0.0.1", "https://[::1]", "https://0.0.0.0"]) {
  test(`production rejects missing or local/insecure URL: ${value}`, () => {
    assert.throws(() => resolveApiUrl(value, true), /VITE_API_URL/);
  });
}

for (const value of ["/api", "ftp://example.test", "https://user:secret@example.test", "https://example.test?token=secret", "https://example.test#fragment"]) {
  test(`invalid API configuration is rejected: ${value}`, () => {
    assert.throws(() => resolveApiUrl(value), /VITE_API_URL/);
  });
}
