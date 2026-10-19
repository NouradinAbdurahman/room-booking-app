// The one place the frontend talks HTTP. Requests go to /api on the page's own
// origin; the Vite proxy forwards them to Django, so there is no CORS (ADR 0004).

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const CSRF_BOOTSTRAP_URL = "/api/auth/csrf/";
// A safety net only; revisited links are already refused, so this never limits real lists.
const DEFAULT_MAX_PAGES = 1000;
const NETWORK_ERROR_MESSAGE = "Can't reach the server. Check your connection and try again.";
const TOKEN_PATTERN = /^[A-Za-z0-9]+$/;

/**
 * An API failure carrying the server's error envelope (ADR 0006).
 * `status` is the HTTP status, or 0 when no usable HTTP response arrived.
 */
export class ApiError extends Error {
  constructor(status, { code, message, fields } = {}) {
    super(message || "Something went wrong. Please try again.");
    this.status = status;
    this.code = code || "error";
    this.fields = fields || {};
  }
}

/**
 * The csrftoken value in a Cookie header string. Like Django, the last
 * duplicate wins; anything that is not a plain alphanumeric token is ignored.
 */
export function parseCsrfCookie(cookieString) {
  let token = null;
  for (const chunk of cookieString.split(";")) {
    const separator = chunk.indexOf("=");
    if (separator === -1 || chunk.slice(0, separator).trim() !== "csrftoken") continue;
    const value = chunk.slice(separator + 1).trim();
    token = TOKEN_PATTERN.test(value) ? value : null;
  }
  return token;
}

/** The csrftoken cookie's current value, read fresh every time. */
export function readCsrfCookie() {
  return parseCsrfCookie(document.cookie);
}

/**
 * @param {object} deps
 * @param {typeof fetch} deps.fetch
 * @param {() => string | null} deps.getCsrfToken  Reads the cookie at send time.
 *   The token is never cached: Django rotates it on login (ADR 0004).
 * @param {() => void} [deps.onUnauthorized]  Called on any 401 so the app can go to Login.
 * @param {string} [deps.origin]  This page's origin; pagination links must stay on it.
 * @param {number} [deps.maxPages]  Most pages listAll will read.
 */
export function createApiClient({
  fetch,
  getCsrfToken,
  onUnauthorized = () => {},
  origin = globalThis.location?.origin,
  maxPages = DEFAULT_MAX_PAGES,
}) {
  async function request(method, url, body) {
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (!SAFE_METHODS.has(method)) {
      const token = getCsrfToken();
      if (token) headers["X-CSRFToken"] = token;
    }

    let response;
    try {
      response = await fetch(url, {
        method,
        headers,
        credentials: "same-origin",
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError(0, { code: "network_error", message: NETWORK_ERROR_MESSAGE });
    }

    const data = await readJson(response);
    if (response.ok) return data;

    if (response.status === 401) onUnauthorized();
    throw new ApiError(response.status, data?.error);
  }

  return {
    get: (url) => request("GET", url),
    post: (url, body) => request("POST", url, body),
    delete: (url) => request("DELETE", url),

    /**
     * Every result of a paginated list, following `next` until it is null.
     * Links are only followed within this origin's /api/ and never revisited.
     */
    async listAll(url) {
      const results = [];
      const visited = new Set();
      for (let next = url; next; ) {
        if (visited.has(next) || visited.size >= maxPages) throw paginationError();
        visited.add(next);
        const page = await request("GET", next);
        if (!Array.isArray(page?.results)) throw paginationError();
        results.push(...page.results);
        next = page.next ? sameOriginApiPath(page.next, origin) : null;
      }
      return results;
    },

    /** Make sure a CSRF cookie exists before the first unsafe request. */
    async ensureCsrfToken() {
      if (!getCsrfToken()) await request("GET", CSRF_BOOTSTRAP_URL);
    },
  };
}

/** A pagination link as a relative /api/ path, or an error if it leaves this origin. */
function sameOriginApiPath(link, origin) {
  const url = new URL(link, origin);
  if (url.origin !== origin || !url.pathname.startsWith("/api/")) throw paginationError();
  return url.pathname + url.search;
}

function paginationError() {
  return new ApiError(0, { code: "bad_pagination", message: "The list could not be loaded." });
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
