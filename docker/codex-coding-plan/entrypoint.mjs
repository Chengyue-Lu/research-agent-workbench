#!/usr/bin/env node

import { access, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { spawn } from "node:child_process";
import { TextDecoder } from "node:util";

const MAGIC = Buffer.from("RWBCP001", "ascii");
const MAX_CREDENTIAL_BYTES = 16_384;
const MAX_PROMPT_BYTES = 65_536;

async function exists(path) {
  try {
    await access(path, fsConstants.F_OK);
    return true;
  } catch {
    return false;
  }
}

function statusValue(status, name) {
  const match = status.match(new RegExp(`^${name}:\\s+([^\\n]+)$`, "m"));
  return match ? match[1].trim() : null;
}

async function probe() {
  let rootfsReadOnly = false;
  try {
    await writeFile("/rwb-rootfs-write-test", "blocked", { flag: "wx" });
    await rm("/rwb-rootfs-write-test", { force: true });
  } catch {
    rootfsReadOnly = true;
  }

  const workspaceTest = "/workspace/.rwb-probe";
  let workspaceTmpfsWritable = false;
  try {
    await writeFile(workspaceTest, "ok", { flag: "wx" });
    await rm(workspaceTest);
    workspaceTmpfsWritable = true;
  } catch {
    workspaceTmpfsWritable = false;
  }

  const interfaces = (await readdir("/sys/class/net")).sort();
  const status = await readFile("/proc/self/status", "utf8");
  const coreDumpLimitZero = await assertCoreDumpDisabled();
  const hostPaths = ["/mnt/c", "/host_mnt", "/run/desktop/mnt/host/c"];
  const credentialObserved = Object.keys(process.env).some((name) =>
    /(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)/i.test(name),
  );
  const result = {
    schema: "rwb-codex-coding-plan-docker-probe/0.1",
    uid: process.getuid(),
    gid: process.getgid(),
    network_interfaces: interfaces,
    rootfs_read_only: rootfsReadOnly,
    workspace_tmpfs_writable: workspaceTmpfsWritable,
    host_paths_absent: !(await Promise.all(hostPaths.map(exists))).some(Boolean),
    docker_socket_absent: !(await exists("/var/run/docker.sock")),
    credential_observed: credentialObserved,
    cap_eff: statusValue(status, "CapEff"),
    no_new_privs: Number(statusValue(status, "NoNewPrivs")),
    seccomp: Number(statusValue(status, "Seccomp")),
    core_dump_limit_zero: coreDumpLimitZero,
  };
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

async function assertCoreDumpDisabled() {
  const limits = await readFile("/proc/self/limits", "utf8");
  const line = limits
    .split("\n")
    .find((candidate) => candidate.startsWith("Max core file size"));
  if (!line) throw new Error("core-dump-limit-unverified");
  const columns = line.trim().split(/\s+/);
  const numeric = columns.filter((value) => /^\d+$/.test(value));
  if (numeric.length < 2 || numeric[0] !== "0" || numeric[1] !== "0") {
    throw new Error("core-dump-limit-unverified");
  }
  return true;
}

async function readFramedInput() {
  const chunks = [];
  let total = 0;
  for await (const chunk of process.stdin) {
    total += chunk.length;
    if (total > MAGIC.length + 8 + MAX_CREDENTIAL_BYTES + MAX_PROMPT_BYTES) {
      chunk.fill(0);
      for (const original of chunks) original.fill(0);
      chunks.length = 0;
      throw new Error("frame-byte-limit-exceeded");
    }
    chunks.push(chunk);
  }
  const payload = Buffer.concat(chunks);
  for (const original of chunks) original.fill(0);
  chunks.length = 0;
  try {
    let offset = 0;
    if (payload.length < MAGIC.length || !payload.subarray(0, MAGIC.length).equals(MAGIC)) {
      throw new Error("frame-magic-invalid");
    }
    offset += MAGIC.length;
    if (offset + 4 > payload.length) throw new Error("frame-truncated");
    const credentialLength = payload.readUInt32BE(offset);
    offset += 4;
    if (credentialLength < 1 || credentialLength > MAX_CREDENTIAL_BYTES) {
      throw new Error("credential-byte-limit-exceeded");
    }
    if (offset + credentialLength + 4 > payload.length) throw new Error("frame-truncated");
    const credentialBytes = payload.subarray(offset, offset + credentialLength);
    offset += credentialLength;
    const promptLength = payload.readUInt32BE(offset);
    offset += 4;
    if (promptLength < 1 || promptLength > MAX_PROMPT_BYTES || offset + promptLength !== payload.length) {
      throw new Error("prompt-byte-limit-exceeded");
    }
    const promptBytes = payload.subarray(offset, offset + promptLength);
    const decoder = new TextDecoder("utf-8", { fatal: true });
    const credential = decoder.decode(credentialBytes);
    const prompt = decoder.decode(promptBytes);
    if (!credential || credential.includes("\0") || !prompt.trim() || prompt.includes("\0")) {
      throw new Error("frame-content-invalid");
    }
    if (prompt.includes(credential)) throw new Error("credential-present-in-prompt");
    return { credential, prompt, payload };
  } catch (error) {
    payload.fill(0);
    throw error;
  }
}

const disabledFeatures = [
  "shell_tool",
  "multi_agent",
  "browser_use",
  "computer_use",
  "apps",
  "plugins",
  "image_generation",
  "in_app_browser",
  "codex_hooks",
  "skill_mcp_dependency_install",
  "workspace_dependencies",
];

function codexArgs() {
  const provider = "model_providers.zhipu_coding_plan";
  const overrides = [
    'model_provider="zhipu_coding_plan"',
    'model_reasoning_effort="low"',
    'model_catalog_json="/runtime/models.json"',
    'approval_policy="never"',
    'history.persistence="none"',
    "analytics.enabled=false",
    "feedback.enabled=false",
    'otel.exporter="none"',
    'otel.metrics_exporter="none"',
    'otel.trace_exporter="none"',
    "otel.log_user_prompt=false",
    "allow_login_shell=false",
    "hide_agent_reasoning=true",
    "show_raw_agent_reasoning=false",
    'shell_environment_policy.inherit="none"',
    'web_search="disabled"',
    "tools.web_search=false",
    "tools.view_image=false",
    `${provider}.name="Zhipu GLM Coding Plan"`,
    `${provider}.base_url="https://open.bigmodel.cn/api/v1"`,
    `${provider}.env_key="RWB_CODEX_CODING_PLAN_CREDENTIAL"`,
    `${provider}.wire_api="responses"`,
    `${provider}.request_max_retries=0`,
    `${provider}.stream_max_retries=0`,
    `${provider}.stream_idle_timeout_ms=30000`,
    `${provider}.requires_openai_auth=false`,
    `${provider}.supports_standalone_web_search=false`,
    `${provider}.supports_websockets=false`,
  ];
  const args = [
    "/runtime/node_modules/@openai/codex/bin/codex.js",
    "exec",
    "--ignore-user-config",
    "--ignore-rules",
    "--ephemeral",
    "--json",
    "--color",
    "never",
    "--sandbox",
    "read-only",
    "--skip-git-repo-check",
    "--cd",
    "/workspace",
    "--model",
    "glm-5.3",
  ];
  for (const override of overrides) args.push("--config", override);
  for (const feature of disabledFeatures) args.push("--disable", feature);
  args.push("-");
  return args;
}

function approvedProxyEnvironment() {
  const expected = "http://rwb-egress-proxy:3128";
  const allowed = new Set(["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"]);
  const observed = Object.keys(process.env).filter((name) =>
    name.toUpperCase().endsWith("_PROXY"),
  );
  if (observed.some((name) => !allowed.has(name))) {
    throw new Error("proxy-environment-not-approved");
  }
  const configured = observed.some((name) => allowed.has(name));
  if (!configured) return {};
  if (
    process.env.HTTP_PROXY !== expected ||
    process.env.HTTPS_PROXY !== expected ||
    process.env.NO_PROXY !== ""
  ) {
    throw new Error("proxy-environment-not-approved");
  }
  return { HTTP_PROXY: expected, HTTPS_PROXY: expected, NO_PROXY: "" };
}

async function run() {
  await assertCoreDumpDisabled();
  const frame = await readFramedInput();
  const env = {
    HOME: "/codex-home",
    CODEX_HOME: "/codex-home",
    NO_COLOR: "1",
    RUST_BACKTRACE: "0",
    RWB_CODEX_CODING_PLAN_CREDENTIAL: frame.credential,
    ...approvedProxyEnvironment(),
  };
  const child = spawn(process.execPath, codexArgs(), {
    cwd: "/workspace",
    env,
    stdio: ["pipe", "pipe", "pipe"],
  });
  frame.payload.fill(0);
  frame.credential = "";
  env.RWB_CODEX_CODING_PLAN_CREDENTIAL = "";
  child.stdout.pipe(process.stdout);
  child.stderr.pipe(process.stderr);
  child.stdin.end(frame.prompt, "utf8");
  const forward = (signal) => {
    if (!child.killed) child.kill(signal);
  };
  process.on("SIGTERM", () => forward("SIGTERM"));
  process.on("SIGINT", () => forward("SIGINT"));
  const code = await new Promise((resolve, reject) => {
    child.once("error", reject);
    child.once("exit", (exitCode, signal) => resolve(exitCode ?? (signal ? 1 : 0)));
  });
  process.exitCode = code;
}

try {
  if (process.argv.length !== 3) throw new Error("entrypoint-mode-invalid");
  if (process.argv[2] === "--probe") await probe();
  else if (process.argv[2] === "--run") await run();
  else throw new Error("entrypoint-mode-invalid");
} catch (error) {
  const code = error instanceof Error ? error.message : "entrypoint-failed";
  process.stderr.write(`${code}\n`);
  process.exitCode = 1;
}
