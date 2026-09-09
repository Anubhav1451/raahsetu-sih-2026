const { readFileSync } = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const handlers = {};
const deleted = [];
const cachedBatches = [];
const worker = readFileSync(__dirname + "/public/sw.js", "utf8");

vm.runInNewContext(worker, {
  self: {
    location: { origin: "https://example.test" },
    addEventListener: (name, fn) => { handlers[name] = fn; },
    clients: { claim() {} },
    skipWaiting() {},
  },
  URL,
  Response,
  Set,
  fetch: async () => new Response(
    '<link rel="stylesheet" href="/assets/app-hash.css"><script src="/assets/app-hash.js"></script>',
    { status: 200 },
  ),
  caches: {
    open: async () => ({ addAll: async (paths) => { cachedBatches.push([...paths]); } }),
    keys: async () => ["raahsetu-shell-v1", "raahsetu-shell-v2", "other-app"],
    delete: async (key) => { deleted.push(key); },
  },
});

(async () => {
  let installation;
  handlers.install({ waitUntil(promise) { installation = promise; } });
  await installation;
  assert.ok(cachedBatches[0].includes("/pwa-512.png"));
  assert.deepEqual(cachedBatches[1], ["/assets/app-hash.css", "/assets/app-hash.js"]);

  for (const [path, auth] of [
    ["/api/v1/me", false],
    ["/api/v1/deliveries", false],
    ["/assets/app.js", true],
    ["/index.html?token=secret", false],
    ["/private.json", false],
  ]) {
    handlers.fetch({
      request: {
        method: "GET",
        url: "https://example.test" + path,
        headers: new Headers(auth ? { Authorization: "Bearer test" } : {}),
      },
      respondWith() { throw Error("Private request intercepted: " + path); },
    });
  }

  let activation;
  handlers.activate({ waitUntil(promise) { activation = promise; } });
  await activation;
  assert.deepEqual(deleted, ["raahsetu-shell-v1", "raahsetu-shell-v2"]);
  console.log("PASS: offline assets are primed; private/API requests bypass cache");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
