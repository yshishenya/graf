const { spawnSync } = require("node:child_process");

const result = spawnSync("node", ["specs/050-mvp-launch-proof/evidence/browser-runtime-check.cjs"], {
  cwd: process.cwd(),
  stdio: "inherit",
  env: { ...process.env, FEATURE_PROOF: "052-mvp-live-ui-proof" },
});

process.exit(result.status === null ? 1 : result.status);
