#!/usr/bin/env node
/**
 * verify_docx.js — 学术论文 docx 引用体系核验（对解包后的 document.xml 运行）
 *
 * 用法:
 *   基础核验:  node verify_docx.js <已解包目录> <N> [--appendix <附录标题>]
 *   跨版本等价: node verify_docx.js <新目录> <N> [--appendix <附录标题>] --old <旧目录或旧document.xml> --report <renumber_report.json>
 *
 * 基础核验项: XML 标签平衡(w:p/w:r/w:t)、正文引用首现序列==1..N 严格单调、
 *             文献列表 1..N 有序、无悬空引用、附录(可选)编号升序。
 * 跨版本等价: 新列表第 k 条内容 == 旧列表第 report.order[k-1] 条内容（逐条全等，只动编号不动内容）。
 * 全部通过退出码 0，否则 1。
 */
'use strict';
const fs = require('fs');

const args = process.argv.slice(2);
if (args.length < 2) { console.error('用法: node verify_docx.js <已解包目录> <N> [--appendix <标题>] [--old <旧目录|旧xml>] [--report <report.json>]'); process.exit(2); }
const dir = args[0].replace(/\\/g, '/').replace(/\/$/, '');
const N = parseInt(args[1], 10);
const apIdx = args.indexOf('--appendix');
const APPENDIX = apIdx >= 0 ? args[apIdx + 1] : null;
const oldIdx = args.indexOf('--old');
const OLD = oldIdx >= 0 ? args[oldIdx + 1] : null;
const repIdx = args.indexOf('--report');
const REPORT = repIdx >= 0 ? args[repIdx + 1] : null;
if ((oldIdx >= 0) !== (repIdx >= 0)) { console.error('--old 与 --report 必须同时提供'); process.exit(2); }

const FILE = dir + '/word/document.xml';
const strip = s => s.replace(/<[^>]+>/g, '');
let bad = 0;
const log = (ok, msg) => { console.log((ok ? 'PASS' : 'FAIL') + '  ' + msg); if (!ok) bad++; };

function paraStart(x, idx) { return Math.max(x.lastIndexOf('<w:p>', idx), x.lastIndexOf('<w:p ', idx)); }
function* paras(x, from, to) {
  const re = /<w:p(?:\s[^>]*)?>/g; re.lastIndex = from; let m;
  while ((m = re.exec(x)) && m.index < to) {
    const end = x.indexOf('</w:p>', m.index);
    if (end < 0 || end >= to) break;
    const p = { start: m.index, end: end + 6 }; re.lastIndex = p.end; yield p;
  }
}
const GRP = /\[(-?\d+(?:\s*[，,]\s*-?\d+)*)\]|\[(-?\d+)(\s*[-\u2212\u2013]\s*)(-?\d+)\]/g;
function parseGroups(text) {
  const out = []; let m; GRP.lastIndex = 0;
  while ((m = GRP.exec(text))) {
    let nums = null;
    if (m[1] !== undefined) {
      const parts = m[1].split(/\s*[，,]\s*/).map(Number);
      if (parts.length && parts.every(n => Number.isInteger(n) && n >= 1 && n <= N)) nums = parts;
    } else {
      const a = +m[2], b = +m[4];
      if (a >= 1 && b <= N && a <= b) { nums = []; for (let k = a; k <= b; k++) nums.push(k); }
    }
    if (nums) out.push(nums);
  }
  return out;
}
const entryNum = para => { const m = strip(para).match(/^\s*\[(\d+)\]\s/); return m ? +m[1] : null; };
const entryText = para => strip(para).replace(/^\s*\[\d+\]\s*/, '');
function refEntries(x, N, appendixHeading) {
  const feM = x.match(/<w:t[^>]*>\[1\] (?=[^\d])/);
  if (!feM) return null;
  const lps = paraStart(x, feM.index);
  const listEnd = appendixHeading ? paraStart(x, x.indexOf(appendixHeading)) : x.length;
  const entries = new Map(); const ordered = [];
  for (const p of paras(x, lps, listEnd)) {
    const t = x.slice(p.start, p.end); const n = entryNum(t);
    if (n !== null && !entries.has(n)) { entries.set(n, entryText(t)); ordered.push(n); }
  }
  return { entries, ordered, listStart: lps, listEnd };
}

// ---- 主文档核验 ----
const x = fs.readFileSync(FILE, 'utf8');
const bal = t => {
  const o = (x.match(new RegExp('<' + t + '[ >]', 'g')) || []).length;
  const c = (x.match(new RegExp('</' + t + '>', 'g')) || []).length;
  return { ok: o === c, s: o + '/' + c };
};
for (const t of ['w:p', 'w:r', 'w:t']) { const r = bal(t); log(r.ok, '标签平衡 ' + t + ' = ' + r.s); }

const mine = refEntries(x, N, APPENDIX);
if (!mine) { console.error('FAIL: 未找到 "[1] " 文献条目'); process.exit(1); }
const body = x.slice(0, mine.listStart);
const seen = new Set(); const seq = [];
{
  const re = /<w:t[^>]*>([^<]*)<\/w:t>/g; let m;
  while ((m = re.exec(body))) for (const g of parseGroups(m[1])) for (const n of [...g].sort((a, b) => a - b)) if (!seen.has(n)) { seen.add(n); seq.push(n); }
}
log(seq.length === N && seq.every((v, i) => v === i + 1), '正文引用首现序列==1..' + N + ' 严格单调 (实际: ' + (seq.length === N ? '1..N' : seq.join(',') || '空') + ')');
log(mine.ordered.length === N && mine.ordered.every((v, i) => v === i + 1), '文献列表 1..' + N + ' 有序 (共 ' + mine.ordered.length + ' 条)');
const dangling = [...seen].filter(n => n < 1 || n > N);
log(dangling.length === 0, '无悬空引用' + (dangling.length ? '（越界: ' + dangling.join(',') + '）' : ''));
if (APPENDIX) {
  const ap = [];
  for (const p of paras(x, paraStart(x, x.indexOf(APPENDIX)), x.length)) {
    const n = entryNum(x.slice(p.start, p.end)); if (n !== null) ap.push(n);
  }
  log(ap.every((v, i) => i === 0 || v > ap[i - 1]), '附录编号升序: ' + ap.join(','));
}

// ---- 跨版本内容等价 ----
if (OLD) {
  const report = JSON.parse(fs.readFileSync(REPORT, 'utf8'));
  let oldXml = OLD;
  if (!oldXml.includes('<w:body')) oldXml = fs.readFileSync(OLD.replace(/\\/g, '/').replace(/\/$/, '') + '/word/document.xml', 'utf8');
  const oldR = refEntries(oldXml, N, APPENDIX);
  if (!oldR) { console.error('FAIL: 旧文档未找到文献条目'); process.exit(1); }
  let mismatch = 0;
  for (let k = 1; k <= N; k++) {
    const oldNo = report.order[k - 1];
    const a = (oldR.entries.get(oldNo) || '').slice(0, 4000);
    const b = (mine.entries.get(k) || '').slice(0, 4000);
    if (a !== b) { mismatch++; console.log('  MISMATCH 新[' + k + '] vs 旧[' + oldNo + ']\n    旧: ' + a.slice(0, 80) + '\n    新: ' + b.slice(0, 80)); }
  }
  log(mismatch === 0, '跨版本内容等价: ' + N + ' 条逐条比对' + (mismatch ? '，' + mismatch + ' 条不一致' : '，全部一致（只动编号、不动内容）'));
}

console.log(bad === 0 ? 'VERIFY OK' : 'VERIFY FAILED (' + bad + ' 项)');
process.exit(bad === 0 ? 0 : 1);
