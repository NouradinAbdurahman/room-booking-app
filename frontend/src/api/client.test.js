import { describe, expect, it, vi } from "vitest";
import { ApiError, createApiClient, parseCsrfCookie } from "./client.js";

/** A fake fetch that records calls and replies from a queue of [status, body]. */
function fakeFetch(...replies) {
  const calls = [];
  const fetch = vi.fn(async (url, init = {}) => {
    calls.push({ url, method: init.method ?? "GET", headers: init.headers ?? {}, body: init.body });
    const [status, body] = replies.shift() ?? [200, {}];
    return new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  return { fetch, calls };
}

/** A fake cookie jar whose csrftoken can change between requests, like after login. */
function cookieJar(initial) {
  let token = initial;
  return {
    getCsrfToken: () => token,
    rotate: (next) => {
      token = next;
    },
  };
}

describe("CSRF header", () => {
  it("is sent on unsafe requests and never on GET", async () => {
    const { fetch, calls } = fakeFetch([200, {}], [204], [204]);
    const api = createApiClient({ fetch, getCsrfToken: cookieJar("token-A").getCsrfToken });

    await api.get("/api/auth/me/");
    await api.post("/api/auth/logout/");
    await api.delete("/api/bookings/1/");

    expect(calls[0].headers["X-CSRFToken"]).toBeUndefined();
    expect(calls[1].headers["X-CSRFToken"]).toBe("token-A");
    expect(calls[2].headers["X-CSRFToken"]).toBe("token-A");
  });

  it("uses the current token after it rotates, never a stale cached one", async () => {
    const jar = cookieJar("pre-login-token");
    const { fetch, calls } = fakeFetch([200, { user: { id: 1, username: "user1" } }], [201, {}]);
    const api = createApiClient({ fetch, getCsrfToken: jar.getCsrfToken });

    await api.post("/api/auth/login/", { username: "user1", password: "x" });
    jar.rotate("post-login-token"); // Django rotates the cookie on login
    await api.post("/api/bookings/", { title: "Sync" });

    expect(calls[0].headers["X-CSRFToken"]).toBe("pre-login-token");
    expect(calls[1].headers["X-CSRFToken"]).toBe("post-login-token");
  });
});

describe("paginated lists", () => {
  it("follows next until it is null and returns every result once", async () => {
    const { fetch, calls } = fakeFetch(
      [200, { count: 3, next: "/api/rooms/?page=2", previous: null, results: [{ id: 1 }, { id: 2 }] }],
      [200, { count: 3, next: null, previous: "/api/rooms/", results: [{ id: 3 }] }],
    );
    const api = createApiClient({ fetch, getCsrfToken: () => null, origin: "http://localhost:5173" });

    const rooms = await api.listAll("/api/rooms/");

    expect(rooms).toEqual([{ id: 1 }, { id: 2 }, { id: 3 }]);
    expect(calls.map((c) => c.url)).toEqual(["/api/rooms/", "/api/rooms/?page=2"]);
  });
});

describe("CSRF bootstrap", () => {
  it("fetches a token when there is no cookie yet", async () => {
    const { fetch, calls } = fakeFetch([200, { csrf_token: "t" }]);
    const api = createApiClient({ fetch, getCsrfToken: () => null });

    await api.ensureCsrfToken();

    expect(calls.map((c) => [c.method, c.url])).toEqual([["GET", "/api/auth/csrf/"]]);
  });

  it("does nothing when a cookie already exists", async () => {
    const { fetch, calls } = fakeFetch();
    const api = createApiClient({ fetch, getCsrfToken: () => "existing" });

    await api.ensureCsrfToken();

    expect(calls).toEqual([]);
  });
});

describe("errors", () => {
  it("turn the error envelope into a message and field errors", async () => {
    const envelope = {
      error: {
        code: "validation_error",
        message: "Some fields are invalid.",
        fields: { title: ["This field may not be blank."] },
      },
    };
    const { fetch } = fakeFetch([400, envelope]);
    const api = createApiClient({ fetch, getCsrfToken: () => "t" });

    const error = await api.post("/api/bookings/", {}).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(400);
    expect(error.code).toBe("validation_error");
    expect(error.message).toBe("Some fields are invalid.");
    expect(error.fields).toEqual({ title: ["This field may not be blank."] });
  });

  it("report 401 so the app can send the User to Login", async () => {
    const onUnauthorized = vi.fn();
    const { fetch } = fakeFetch([401, { error: { code: "not_authenticated", message: "x", fields: {} } }]);
    const api = createApiClient({ fetch, getCsrfToken: () => null, onUnauthorized });

    const error = await api.get("/api/auth/me/").catch((e) => e);

    expect(onUnauthorized).toHaveBeenCalledTimes(1);
    expect(error.code).toBe("not_authenticated");
  });

  it("do not treat other refusals as a lost session", async () => {
    const onUnauthorized = vi.fn();
    const { fetch } = fakeFetch([403, { error: { code: "csrf_failed", message: "x", fields: {} } }]);
    const api = createApiClient({ fetch, getCsrfToken: () => "t", onUnauthorized });

    await api.post("/api/auth/logout/").catch(() => {});

    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("still give a readable message when the body is not the envelope", async () => {
    const fetch = vi.fn(async () => new Response("<html>Bad gateway</html>", { status: 502 }));
    const api = createApiClient({ fetch, getCsrfToken: () => null });

    const error = await api.get("/api/rooms/").catch((e) => e);

    expect(error.status).toBe(502);
    expect(error.message).toBe("Something went wrong. Please try again.");
  });
});

describe("pagination links", () => {
  it("are only followed within this origin's /api/", async () => {
    const { fetch, calls } = fakeFetch([
      200,
      { count: 2, next: "https://evil.example/api/rooms/?page=2", previous: null, results: [{ id: 1 }] },
    ]);
    const api = createApiClient({ fetch, getCsrfToken: () => null, origin: "http://localhost:5173" });

    const error = await api.listAll("/api/rooms/").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(calls).toHaveLength(1);
  });

  it("accept an absolute same-origin link, as Django builds them", async () => {
    const { fetch, calls } = fakeFetch(
      [200, { next: "http://localhost:5173/api/rooms/?page=2", results: [{ id: 1 }] }],
      [200, { next: null, results: [{ id: 2 }] }],
    );
    const api = createApiClient({ fetch, getCsrfToken: () => null, origin: "http://localhost:5173" });

    expect(await api.listAll("/api/rooms/")).toEqual([{ id: 1 }, { id: 2 }]);
    expect(calls[1].url).toBe("/api/rooms/?page=2");
  });

  it("stop instead of looping when a page links back to itself", async () => {
    const loop = [200, { next: "/api/rooms/?page=2", results: [{ id: 1 }] }];
    const { fetch, calls } = fakeFetch(loop, loop, loop);
    const api = createApiClient({ fetch, getCsrfToken: () => null, origin: "http://localhost:5173" });

    const error = await api.listAll("/api/rooms/?page=2").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(calls).toHaveLength(1);
  });
});

describe("reading the CSRF cookie", () => {
  it("finds the token among other cookies", () => {
    expect(parseCsrfCookie("theme=dark; csrftoken=AbC123xyz; lang=en")).toBe("AbC123xyz");
  });

  it("takes the last duplicate, as Django does", () => {
    expect(parseCsrfCookie("csrftoken=firstOne; csrftoken=secondOne")).toBe("secondOne");
  });

  it("ignores values that are not a token and never throws on malformed input", () => {
    expect(parseCsrfCookie("csrftoken=%E0%A4%A")).toBeNull();
    expect(parseCsrfCookie("csrftoken=<script>")).toBeNull();
    expect(parseCsrfCookie("")).toBeNull();
  });
});

describe("more pagination safety", () => {
  it("refuse a same-origin link that leaves /api/", async () => {
    const { fetch, calls } = fakeFetch([200, { next: "/admin/?page=2", results: [{ id: 1 }] }]);
    const api = createApiClient({ fetch, getCsrfToken: () => null, origin: "http://localhost:5173" });

    expect(await api.listAll("/api/rooms/").catch((e) => e)).toBeInstanceOf(ApiError);
    expect(calls).toHaveLength(1);
  });

  it("stop at the page cap even when every link is new", async () => {
    const page = (n) => [200, { next: `/api/rooms/?page=${n + 1}`, results: [{ id: n }] }];
    const { fetch, calls } = fakeFetch(page(1), page(2), page(3));
    const api = createApiClient({
      fetch,
      getCsrfToken: () => null,
      origin: "http://localhost:5173",
      maxPages: 2,
    });

    expect(await api.listAll("/api/rooms/?page=1").catch((e) => e)).toBeInstanceOf(ApiError);
    expect(calls).toHaveLength(2);
  });
});

describe("network failures", () => {
  it("become a readable ApiError instead of the browser's raw message", async () => {
    const fetch = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });
    const api = createApiClient({ fetch, getCsrfToken: () => null });

    const error = await api.get("/api/auth/me/").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.message).toBe("Can't reach the server. Check your connection and try again.");
  });
});
