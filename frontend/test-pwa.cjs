const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const assert = require("node:assert/strict");

const root = __dirname;
const manifest = JSON.parse(readFileSync(join(root, "public", "manifest.webmanifest"), "utf8"));
const html = readFileSync(join(root, "index.html"), "utf8");
const worker = readFileSync(join(root, "public", "sw.js"), "utf8");

assert.equal(manifest.display, "standalone");
assert.equal(manifest.start_url, "/");
assert.match(html, /rel="apple-touch-icon"/);

for (const size of [192, 512]) {
  const icon = manifest.icons.find((item) => item.sizes === `${size}x${size}`);
  assert.ok(icon, `Missing ${size}x${size} manifest icon`);
  assert.match(icon.purpose, /maskable/);
  const png = readFileSync(join(root, "public", icon.src.replace(/^\//, "")));
  assert.deepEqual([...png.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  assert.equal(png.readUInt32BE(16), size);
  assert.equal(png.readUInt32BE(20), size);
  assert.ok(worker.includes(icon.src), `${icon.src} is missing from the offline shell`);
}

console.log("PASS: PWA manifest, install icons and offline shell are consistent");
