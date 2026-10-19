// The one place the frontend talks HTTP. Requests go to /api on the page's own
// origin; the Vite proxy forwards them to Django, so there is no CORS (ADR 0004).

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const CSRF_BOOTSTRAP_URL = "/api/auth/csrf/";

/** An API failure carrying the server's error envelope (ADR 0006). */
export class ApiError extends Error {
  constructor(status, { code, message, fields } = {}) {
    super(message || "Something went wrong. Please try again.");
    this.status = status;
    this.code = code || "error";
    this.fields = fields || {};
  }
}

/** The csrftoken cookie's current value, read fresh every time. */
export function readCsrfCookie() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * @param {object} deps
 * @param {typeof fetch} deps.fetch
 * @param {() => string | null} deps.getCsrfToken  Reads the cookie at send time.
 *   The token is never cached: Django rotates it on login (ADR 0004).
 * @param {() => void} [deps.onUnauthorized]  Called on any 401 so the app can go to Login.
 */
export function createApiClient({ fetch, getCsrfToken, onUnauthorized = () => {} }) {
  async function request(method, url, body) {
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (!SAFE_METHODS.has(method)) {
      const token = getCsrfToken();
      if (token) headers["X-CSRFToken"] = token;
    }

    const response = await fetch(url, {
      method,
      headers,
      credentials: "same-origin",
      body: body === undefined ? undefined : JSON.stringify(body),
    });

    const data = await readJson(response);
    if (response.ok) return data;

    if (response.status === 401) onUnauthorized();
    throw new ApiError(response.status, data?.error);
  }

  return {
    get: (url) => request("GET", url),
    post: (url, body) => request("POST", url, body),
    delete: (url) => request("DELETE", url),

    /** Every result of a paginated list, following `next` until it is null. */
    async listAll(url) {
      const results = [];
      for (let next = url; next; ) {
        const page = await request("GET", next);
        results.push(...page.results);
        next = page.next;
      }
      return results;
    },

    /** Make sure a CSRF cookie exists before the first unsafe request. */
    async ensureCsrfToken() {
      if (!getCsrfToken()) await request("GET", CSRF_BOOTSTRAP_URL);
    },
  };
}

async function readJson(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}
