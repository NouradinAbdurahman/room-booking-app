import { createApiClient, readCsrfCookie } from "./client.js";

let handleUnauthorized = () => {};

/** Lets the auth layer decide what a 401 means (go back to Login). */
export function setUnauthorizedHandler(handler) {
  handleUnauthorized = handler;
}

export const api = createApiClient({
  fetch: (...args) => window.fetch(...args),
  getCsrfToken: readCsrfCookie,
  onUnauthorized: () => handleUnauthorized(),
});

export const authApi = {
  me: () => api.get("/api/auth/me/"),
  login: (username, password) => api.post("/api/auth/login/", { username, password }),
  logout: () => api.post("/api/auth/logout/"),
};
