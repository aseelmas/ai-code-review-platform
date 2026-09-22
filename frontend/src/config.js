// Shared by Vite's build configuration and the configuration tests.
export function resolveApiUrl(value, production = false) {
  const configured = value?.trim();
  if (!configured) {
    if (production) throw new Error("Set VITE_API_URL to the deployed HTTPS backend URL before building.");
    return "http://127.0.0.1:8000";
  }

  let url;
  try {
    url = new URL(configured);
  } catch {
    throw new Error("VITE_API_URL must be an absolute HTTP(S) URL.");
  }
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error("VITE_API_URL must be an HTTP(S) URL without credentials, query strings, or fragments.");
  }
  const local = url.hostname === "localhost" || url.hostname.endsWith(".localhost")
    || url.hostname === "[::1]" || url.hostname === "0.0.0.0" || url.hostname.startsWith("127.");
  if (production && (url.protocol !== "https:" || local)) {
    throw new Error("Production VITE_API_URL must use HTTPS and cannot point to localhost.");
  }
  return url.href.replace(/\/+$/, "");
}
