// Windows-safe deploy.
//
// On Windows, `opennextjs-cloudflare deploy` (and `wrangler deploy`, which invokes
// wrangler's OpenNext framework hook when open-next.config.ts is present) crashes
// with ERR_UNSUPPORTED_ESM_URL_SCHEME — it `import()`s the config via a raw `C:\`
// path instead of a file:// URL. `wrangler deploy` of the already-built worker is
// fine, so: build normally, hide open-next.config.ts, deploy the built worker with
// wrangler directly, then restore the config. (Linux/CI can use `npm run cf:deploy`.)
import { execSync } from "node:child_process";
import { renameSync, existsSync } from "node:fs";

const CFG = "open-next.config.ts";
const HIDDEN = "_open-next.config.ts.hidden";
const run = (cmd) => execSync(cmd, { stdio: "inherit" });

run("node scripts/generate-briefs.mjs"); // refresh the bundled daily-brief manifest
run("opennextjs-cloudflare build");
renameSync(CFG, HIDDEN);
try {
  run("node ./node_modules/wrangler/bin/wrangler.js deploy");
} finally {
  if (existsSync(HIDDEN)) renameSync(HIDDEN, CFG);
}
