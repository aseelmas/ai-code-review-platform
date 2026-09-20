export function errorMessage(detail, fallback) {
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item?.msg).filter((message) => typeof message === "string");
    if (messages.length) return messages.join("; ");
  }
  return fallback;
}

export async function postJson(url, payload, timeoutMs = 150000) {
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (error) {
    if (error.name === "TimeoutError" || error.name === "AbortError") {
      throw new Error("The request timed out. Please try again.", { cause: error });
    }
    throw new Error("Cannot reach the backend. Check that it is running and try again.", { cause: error });
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("The backend returned an unreadable response. Please try again.");
  }
  if (!response.ok) {
    throw new Error(errorMessage(data.detail, "The request failed. Please try again."));
  }
  return data;
}
