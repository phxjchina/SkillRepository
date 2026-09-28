// -*- coding: utf-8 -*-
/**
 * GitHub Data API 增量推送（Node 版，本机可直接运行）。
 *
 * 适用：github.com:443 直连超时、但 api.github.com 可达（2026-09-28 实测）时的兜底推送。
 * 本机受管 Python 运行时缺标准库 `Lib`，无法执行 api_push_assets.py；本脚本用 Node 22 原生 fetch
 * 实现等价功能：blob -> tree(base_tree 增量) -> commit -> 更新 main，绝不删既有文件。
 *
 * 复用方式（与 api_push_assets.py 等价，推荐用环境变量，不改文件）：
 *   NEW_DIRS="github-skill-repo-sync" MSG="docs: ..." node api_push_assets.js
 *   NEW_TOP="README.md" 可附加顶层文件；多项逗号分隔。
 */
const fs = require("fs");
const path = require("path");
const os = require("os");
const { execFileSync } = require("child_process");

// ==== 默认常量（可被环境变量覆盖）====
const REPO = "phxjchina/SkillRepository";
const ROOT = "C:/Users/Administrator/.workbuddy/SkillRepository";
const NEW_DIRS = (process.env.NEW_DIRS || "uni-teacher-workbench")
  .split(",").map((s) => s.trim()).filter(Boolean);
const NEW_TOP = (process.env.NEW_TOP || "")
  .split(",").map((s) => s.trim()).filter(Boolean);
// 需从远程删除的路径（文件改名/移除时用），tree 条目以 sha:null 表达
const NEW_DELETE = (process.env.NEW_DELETE || "")
  .split(",").map((s) => s.trim()).filter(Boolean);
const MSG = process.env.MSG || "feat(skills): 增量更新\n\n(via GitHub Data API / node)";
// ==================

function token() {
  // 1) 显式环境变量（最稳）
  if (process.env.GH_PAT) return process.env.GH_PAT;
  // 2) git store 明文凭据文件（~/.git-credentials），免 spawn
  const cred = path.join(os.homedir(), ".git-credentials");
  if (fs.existsSync(cred)) {
    const txt = fs.readFileSync(cred, "utf8");
    for (const line of txt.split("\n")) {
      const m = line.match(/^https:\/\/[^:/]+:([^@\s]+)@github\.com/);
      if (m) return m[1];
    }
  }
  // 3) 兜底：git credential fill（部分环境 spawn 受限时会失败）
  try {
    const GIT = process.env.GIT_BIN || "git";
    const out = execFileSync(GIT, ["-c", "credential.helper=store", "credential", "fill"], {
      input: "protocol=https\nhost=github.com\n\n",
      encoding: "utf8",
    });
    for (const line of out.split("\n")) {
      if (line.startsWith("password=")) return line.slice("password=".length);
    }
  } catch (e) {
    /* ignore */
  }
  throw new Error("无 PAT：请设 GH_PAT 或确保 ~/.git-credentials 存在");
}

function api(method, p, tok, payload) {
  return fetch("https://api.github.com" + p, {
    method,
    headers: {
      Authorization: "Bearer " + tok,
      Accept: "application/vnd.github+json",
      "User-Agent": "skill-sync-node",
      "Content-Type": "application/json",
    },
    body: payload ? JSON.stringify(payload) : undefined,
  });
}

async function collect() {
  const files = [];
  for (const item of NEW_DIRS) {
    const base = path.join(ROOT, item);
    (function walk(d) {
      for (const e of fs.readdirSync(d, { withFileTypes: true })) {
        if (e.name === "__pycache__") continue;
        const full = path.join(d, e.name);
        if (e.isDirectory()) walk(full);
        else if (e.name.endsWith(".pyc")) continue;
        else files.push(path.relative(ROOT, full).replace(/\\/g, "/"));
      }
    })(base);
  }
  for (const f of NEW_TOP) files.push(f);
  return files;
}

async function main() {
  const tok = token();
  const files = await collect();
  console.log("待推送文件数:", files.length, files);

  const ref = await (await api("GET", `/repos/${REPO}/git/ref/heads/main`, tok)).json();
  const baseCommit = ref.object.sha;
  const baseTree = (await (await api("GET", `/repos/${REPO}/git/commits/${baseCommit}`, tok)).json()).tree.sha;
  console.log("baseCommit:", baseCommit, "\nbaseTree:", baseTree);

  const entries = [];
  for (const rel of files) {
    const buf = fs.readFileSync(path.join(ROOT, rel));
    const r = await (
      await api("POST", `/repos/${REPO}/git/blobs`, tok, {
        content: buf.toString("base64"),
        encoding: "base64",
      })
    ).json();
    entries.push({ path: rel, mode: "100644", type: "blob", sha: r.sha });
    console.log("blob ok:", rel);
  }

  const tree = await (
    await api("POST", `/repos/${REPO}/git/trees`, tok, {
      base_tree: baseTree,
      tree: [
        ...entries,
        ...NEW_DELETE.map((p) => ({ path: p, mode: "100644", type: "blob", sha: null })),
      ],
    })
  ).json();
  const commit = await (
    await api("POST", `/repos/${REPO}/git/commits`, tok, {
      message: MSG,
      tree: tree.sha,
      parents: [baseCommit],
    })
  ).json();
  console.log("new commit:", commit.sha);

  const patch = await api("PATCH", `/repos/${REPO}/git/refs/heads/main`, tok, {
    sha: commit.sha,
    force: false,
  });
  console.log("ref update status:", patch.status);
  console.log("PUSHED ✅", commit.sha);
}

main().catch((e) => {
  console.error("FAIL:", e);
  process.exit(1);
});
