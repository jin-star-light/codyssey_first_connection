import { cpSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = path.join(root, "src");
const destination = path.join(root, "dist");
const rawBaseUrl = process.env.API_BASE_URL?.trim();

if (!rawBaseUrl) {
  console.error("API_BASE_URL 환경 변수가 필요합니다.");
  process.exit(1);
}

let baseUrl;
try {
  baseUrl = new URL(rawBaseUrl).toString().replace(/\/$/, "");
} catch {
  console.error("API_BASE_URL은 유효한 http(s) URL이어야 합니다.");
  process.exit(1);
}
if (!/^https?:/.test(baseUrl)) {
  console.error("API_BASE_URL은 http(s) URL이어야 합니다.");
  process.exit(1);
}

rmSync(destination, { recursive: true, force: true });
mkdirSync(destination, { recursive: true });
cpSync(source, destination, { recursive: true });
writeFileSync(
  path.join(destination, "config.js"),
  `window.APP_CONFIG = Object.freeze({ API_BASE_URL: ${JSON.stringify(baseUrl)} });\n`,
  "utf8",
);
console.log(`Built frontend for ${baseUrl}`);
