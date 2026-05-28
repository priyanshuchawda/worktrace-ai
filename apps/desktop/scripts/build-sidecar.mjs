import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const desktopDir = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(desktopDir, "..", "..");
const localAgentDir = path.join(repoRoot, "services", "local-agent");
const tauriDir = path.join(desktopDir, "src-tauri");
const targetDir = path.join(tauriDir, "target", "pyinstaller");
const distDir = path.join(targetDir, "dist");
const workDir = path.join(targetDir, "work");
const specDir = path.join(targetDir, "spec");
const binariesDir = path.join(tauriDir, "binaries");
const migrationsDir = path.join(localAgentDir, "src", "worktrace_agent", "db", "migrations");

const targetTriple = execFileSync("rustc", ["--print", "host-tuple"], {
  encoding: "utf8",
}).trim();
if (!targetTriple) {
  throw new Error("Could not determine Rust target triple.");
}

const extension = process.platform === "win32" ? ".exe" : "";
const sourceBinary = path.join(distDir, `worktrace-local-agent${extension}`);
const targetBinary = path.join(
  binariesDir,
  `worktrace-local-agent-${targetTriple}${extension}`,
);

rmSync(targetDir, { recursive: true, force: true });
mkdirSync(distDir, { recursive: true });
mkdirSync(workDir, { recursive: true });
mkdirSync(specDir, { recursive: true });
mkdirSync(binariesDir, { recursive: true });

execFileSync(
  "uv",
  [
    "run",
    "--python",
    "3.13",
    "pyinstaller",
    "--onefile",
    "--name",
    "worktrace-local-agent",
    "--paths",
    path.join(localAgentDir, "src"),
    "--collect-data",
    "worktrace_agent",
    "--collect-submodules",
    "worktrace_agent",
    "--hidden-import",
    "worktrace_agent.api.app",
    "--add-data",
    `${migrationsDir}${path.delimiter}${path.join("worktrace_agent", "db", "migrations")}`,
    "--distpath",
    distDir,
    "--workpath",
    workDir,
    "--specpath",
    specDir,
    path.join(localAgentDir, "src", "worktrace_agent", "__main__.py"),
  ],
  {
    cwd: localAgentDir,
    stdio: "inherit",
  },
);

copyFileSync(sourceBinary, targetBinary);
console.log(`Prepared sidecar binary: ${targetBinary}`);
