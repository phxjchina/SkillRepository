// -*- coding: utf-8 -*-
// sanitize.js —— SkillRepository 推送前强制脱敏引擎
//
// 设计：引擎与词表分离。本脚本入库公开，**不含任何真实名词**；
//       词表为私有文件（含真实名词），绝不入库：
//         默认 ~/.workbuddy/sanitize-words.json（可用环境变量 SANITIZE_WORDS 覆盖）
//
// 用法：
//   node sanitize.js <目标目录>          # 替换模式：按词表改写文本文件
//   node sanitize.js --check <目标目录>  # 校验模式：只报告残留，发现即退出码 1（推送前核验用）
//
// 返回码：0 = 干净；1 = 仍有残留（--check 模式）或出错。
// 词表格式（JSON）：
//   { "replacements": [["真实词","占位"], ...长串在前...],
//     "patterns": [ { "name":"说明","regex":"...","to":"占位" }, ... ] }
// 维护：识别到新的真实名词（学校/人名/邮箱/项目代号等）→ 只改词表文件，勿改本脚本。
const fs = require("fs");
const path = require("path");
const os = require("os");

const CHECK = process.argv[2] === "--check";
const ROOT = CHECK ? process.argv[3] : process.argv[2];
const WORDS_FILE = process.env.SANITIZE_WORDS || path.join(os.homedir(), ".workbuddy", "sanitize-words.json");

if (!ROOT || !fs.existsSync(ROOT)) { console.error("sanitize: 目标目录不存在: " + ROOT); process.exit(1); }
if (!fs.existsSync(WORDS_FILE)) {
  console.error("sanitize: 词表缺失: " + WORDS_FILE);
  console.error("sanitize: 请先创建私有词表（格式见脚本头注释）。⚠️ 词表含真实名词，绝不入库。");
  process.exit(1);
}

let RULES;
try {
  const raw = JSON.parse(fs.readFileSync(WORDS_FILE, "utf8"));
  RULES = {
    replacements: Array.isArray(raw.replacements) ? raw.replacements : [],
    patterns: Array.isArray(raw.patterns) ? raw.patterns : [],
  };
} catch (e) {
  console.error("sanitize: 词表解析失败: " + e.message);
  process.exit(1);
}
if (!RULES.replacements.length && !RULES.patterns.length) {
  console.error("sanitize: 词表为空，拒绝执行（防止空表假通过）。");
  process.exit(1);
}

const TEXT_EXT = /\.(md|py|txt|json|js|mjs|html?|svg|css|xml|yaml|yml|ini|cfg)$/i;

function walk(d, cb) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    if (e.name === ".git" || e.name === "node_modules" || e.name === "__pycache__") continue;
    const full = path.join(d, e.name);
    if (e.isDirectory()) walk(full, cb);
    else cb(full);
  }
}

function hitsIn(text) {
  const found = [];
  for (const [a] of RULES.replacements) {
    const n = text.split(a).length - 1;
    if (n > 0) found.push(a + " x" + n);
  }
  for (const p of RULES.patterns) {
    try {
      const m = text.match(new RegExp(p.regex, "g"));
      if (m) found.push((p.name || p.regex) + " x" + m.length);
    } catch (e) { found.push("!! 无效正则: " + (p.name || p.regex)); }
  }
  return found;
}

const report = [];
let totalReplaced = 0;
walk(ROOT, (f) => {
  if (!TEXT_EXT.test(f)) return;
  let text;
  try { text = fs.readFileSync(f, "utf8"); } catch (e) { return; }
  const found = hitsIn(text);
  if (!found.length) return;
  const rel = path.relative(ROOT, f);
  if (CHECK) { report.push([rel, found]); return; }
  let count = 0, out = text;
  for (const [a, b] of RULES.replacements) {
    const parts = out.split(a);
    if (parts.length > 1) { count += parts.length - 1; out = parts.join(b); }
  }
  for (const p of RULES.patterns) {
    try {
      out = out.replace(new RegExp(p.regex, "g"), () => { count++; return p.to; });
    } catch (e) { /* 无效正则在 hitsIn 已提示 */ }
  }
  if (out !== text) fs.writeFileSync(f, out);
  totalReplaced += count;
  report.push([rel, ["replaced " + count]]);
});

if (CHECK) {
  if (report.length) {
    console.log("sanitize --check: 发现残留 " + report.length + " 个文件（推送前必须处理）：");
    for (const [rel, found] of report) console.log("  " + rel + "  <- " + found.join(", "));
    console.log("sanitize --check: FAIL");
    process.exit(1);
  }
  console.log("sanitize --check: 干净（词表 " + RULES.replacements.length + " 条替换 + " + RULES.patterns.length + " 条正则，零残留）");
  process.exit(0);
}

for (const [rel, info] of report) { console.log("  " + rel + "  " + info.join(", ")); }
console.log("sanitize: " + report.length + " 个文件，共替换 " + totalReplaced + " 处。");
console.log("sanitize: 复跑 --check 确认零残留后再推送。");
