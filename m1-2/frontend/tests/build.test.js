import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync, rmSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

test("build requires API_BASE_URL", () => {
  const result = spawnSync(process.execPath, ["scripts/build.mjs"], {
    cwd: root,
    env: { ...process.env, API_BASE_URL: "" },
  });
  assert.notEqual(result.status, 0);
});

test("build copies sources and exposes only public API URL", () => {
  rmSync(path.join(root, "dist"), { recursive: true, force: true });
  const result = spawnSync(process.execPath, ["scripts/build.mjs"], {
    cwd: root,
    env: { ...process.env, API_BASE_URL: "https://api.example.com/" },
  });
  assert.equal(result.status, 0, result.stderr.toString());
  const config = readFileSync(path.join(root, "dist", "config.js"), "utf8");
  assert.match(config, /https:\/\/api\.example\.com/);
  assert.doesNotMatch(config, /COPA_API_KEY|FIREBASE|secret/i);
  assert.ok(readFileSync(path.join(root, "dist", "js", "api.js"), "utf8"));
});
