#!/usr/bin/env node
/**
 * renumber_citations.js — 学术论文 docx 引用编号按 GB/T 7714 顺序编码制整体重排
 *
 * 用法:
 *   node renumber_citations.js <已解包目录> <最大文献号N> [--appendix <附录标题文本>]
 *   例: node renumber_citations.js ./extracted 44
 *       node renumber_citations.js ./extracted 29 --appendix "附中文参考文献"
 *
 * 前置: <目录>/word/document.xml 已由 docx 解包得到。
 * 功能:
 *   1) 扫描正文全部引用组（单条 [n]、相邻簇 [n][m]…、合并式 [n,m]、区间式 [a−b]），
 *      数学区间（含负号或含 0）自动排除；
 *   2) 按正文首次出现顺序生成 old→new 映射（组内按升序计入首现）；
 *   3) 正文引用替换：连续相邻括号簇合并升序重渲染；区间组映射后仍连续则保留 [a−b]；
 *   4) 文献列表段落物理重排并改前导编号（非条目段落原位保留）；
 *   5) --appendix 时：附录条目联动改号并按新号升序重排；
 *   6) 自校验：XML 标签平衡、首现序列==1..N 严格单调、列表 1..N 有序、附录升序；
 *   7) 写回 document.xml，并在 <目录>/renumber_report.json 落盘映射报告（供跨版本等价核验）。
 * 任何一步校验失败即非零退出且不写盘（写盘在校验通过之后）。
 */
'use strict';
const fs = require('fs');

const args = process.argv.slice(2);
if (args.length < 2) { console.error('用法: node renumber_citations.js <已解包目录> <N> [--appendix <标题>]'); process.exit(2); }
const dir = args[0].replace(/\\/g, '/').replace(/\/$/, '');
const N = parseInt(args[1], 10);
if (!Number.isInteger(N) || N < 1) { console.error('N 必须为正整数'); process.exit(2); }
const apIdx = args.indexOf('--appendix');
const APPENDIX = apIdx >= 0 ? args[apIdx + 1] : null;

const FILE = dir + '/word/document.xml';
const strip = s => s.replace(/<[^>]+>/g, '');
const fail = msg => { console.error('FAIL: ' + msg); process.exit(1); };

function paraStart(x, idx) { return Math.max(x.lastIndexOf('<w:p>', idx), x.lastIndexOf('<w:p ', idx)); }
function* paras(x, from, to) {
  const re = /<w:p(?:\s[^>]*)?>/g; re.lastIndex = from; let m;
  while ((m = re.exec(x)) && m.index < to) {
    const end = x.indexOf('</w:p>', m.index);
    if (end < 0 || end >= to) break;
    const p = { start: m.index, end: end + 6 }; re.lastIndex = p.end; yield p;
  }
}

// ---- 引用组解析：逗号式 / 区间式；含负号或 0 的数学区间自动排除 ----
const GRP = /\[(-?\d+(?:\s*[，,]\s*-?\d+)*)\]|\[(-?\d+)(\s*[-\u2212\u2013]\s*)(-?\d+)\]/g;
function parseGroups(text) {
  const out = []; let m; GRP.lastIndex = 0;
  while ((m = GRP.exec(text))) {
    let nums = null, kind = null;
    if (m[1] !== undefined) {
      const parts = m[1].split(/\s*[，,]\s*/).map(Number);
      if (parts.length && parts.every(n => Number.isInteger(n) && n >= 1 && n <= N)) { nums = parts; kind = 'comma'; }
    } else {
      const a = +m[2], b = +m[4];
      if (a >= 1 && b <= N && a <= b) { nums = []; for (let k = a; k <= b; k++) nums.push(k); kind = 'range'; }
    }
    if (nums) out.push({ start: m.index, end: m.index + m[0].length, nums, kind });
  }
  return out;
}

let x = fs.readFileSync(FILE, 'utf8');
if (!x.includes('<w:body')) fail('输入不像 word/document.xml');

// ---- 定位文献列表边界 ----
const feM = x.match(/<w:t[^>]*>\[1\] (?=[^\d])/);
if (!feM) fail('未找到 "[1] " 起始的文献条目');
const listParaStart = paraStart(x, feM.index);
let appendixParaStart = -1;
if (APPENDIX) {
  const ap = x.indexOf(APPENDIX);
  if (ap < 0) fail('未找到附录标题: ' + APPENDIX);
  appendixParaStart = paraStart(x, ap);
  if (appendixParaStart <= listParaStart) fail('附录标题位置在文献列表之前，参数可能有误');
}
const listRegionEnd = APPENDIX ? appendixParaStart : x.length;

// ---- 1) 正文首现扫描 ----
const body = x.slice(0, listParaStart);
const firsts = new Map(); let seqPos = 0;
{
  const re = /(<w:t[^>]*>)([^<]*)(<\/w:t>)/g; let m;
  while ((m = re.exec(body))) {
    for (const g of parseGroups(m[2])) {
      for (const n of [...g.nums].sort((a, b) => a - b)) if (!firsts.has(n)) firsts.set(n, seqPos++);
    }
  }
}
if (firsts.size !== N) fail('正文仅引用 ' + firsts.size + ' 条 != N=' + N + '；未引用: ' +
  [...Array(N).keys()].map(i => i + 1).filter(n => !firsts.has(n)).join(','));
const order = [...firsts.keys()];
const oldToNew = new Map(); order.forEach((o, i) => oldToNew.set(o, i + 1));

// ---- 2) 正文替换 ----
function mapText(text) {
  const gs = parseGroups(text);
  if (!gs.length) return text;
  let out = '', pos = 0, k = 0;
  while (k < gs.length) {
    let j = k;
    while (j + 1 < gs.length && gs[j + 1].start === gs[j].end) j++; // 连续相邻括号簇
    out += text.slice(pos, gs[k].start);
    if (j === k) {
      const g = gs[k];
      const nn = [...new Set(g.nums.map(n => oldToNew.get(n)))].sort((a, b) => a - b);
      if (g.kind === 'range') {
        const contig = nn.every((v, i) => i === 0 || v === nn[i - 1] + 1);
        out += contig ? '[' + nn[0] + '\u2212' + nn[nn.length - 1] + ']' : '[' + nn.join(',') + ']';
      } else out += '[' + nn.join(',') + ']';
    } else {
      let all = [];
      for (let q = k; q <= j; q++) all.push(...gs[q].nums.map(n => oldToNew.get(n)));
      all = [...new Set(all)].sort((a, b) => a - b);
      out += all.map(n => '[' + n + ']').join('');
    }
    pos = gs[j].end; k = j + 1;
  }
  out += text.slice(pos);
  return out;
}
const newBody = body.replace(/(<w:t[^>]*>)([^<]*)(<\/w:t>)/g, (all, o, t, c) => o + mapText(t) + c);

// ---- 3) 列表段落收集与重排 ----
function collectRegion(from, to) {
  const pieces = []; let cursor = from;
  for (const p of paras(x, from, to)) {
    if (p.start > cursor) pieces.push({ type: 'gap', s: x.slice(cursor, p.start) });
    pieces.push({ type: 'para', s: x.slice(p.start, p.end) });
    cursor = p.end;
  }
  if (cursor < to) pieces.push({ type: 'gap', s: x.slice(cursor, to) });
  return pieces;
}
const entryNum = para => { const m = strip(para).match(/^\s*\[(\d+)\]\s/); return m ? +m[1] : null; };
function renumberEntry(para, newN) {
  if (para === undefined) fail('renumberEntry 收到 undefined（newN=' + newN + '）');
  const out = para.replace(/(<w:t[^>]*>)\[(\d+)\]/, (a, p1) => p1 + '[' + newN + ']');
  const chk = strip(out).match(/^\s*\[(\d+)\]\s/);
  if (!chk || +chk[1] !== newN) fail('前导改号校验失败 newN=' + newN);
  return out;
}
const mainPieces = collectRegion(listParaStart, listRegionEnd);
const mainEntries = new Map();
for (const p of mainPieces) if (p.type === 'para') { const n = entryNum(p.s); if (n !== null) mainEntries.set(n, p.s); }
if (mainEntries.size !== N || [...mainEntries.keys()].some(n => n < 1 || n > N))
  fail('文献列表条目 ' + mainEntries.size + ' != N；编号: ' + [...mainEntries.keys()].sort((a, b) => a - b).join(','));
const mainQueue = [];
for (let i = 1; i <= N; i++) mainQueue.push(renumberEntry(mainEntries.get(order[i - 1]), i));
let qi = 0;
const newMain = mainPieces.map(p => {
  if (p.type === 'gap') return p.s;
  return entryNum(p.s) !== null ? mainQueue[qi++] : p.s;
}).join('');
if (qi !== N) fail('主列表重排消费 ' + qi + ' != ' + N);

// ---- 4) 附录联动 ----
let newAppendix = ''; const appendixRemap = {};
if (APPENDIX) {
  const apPieces = collectRegion(appendixParaStart, x.length);
  const apEntries = new Map();
  for (const p of apPieces) if (p.type === 'para') { const n = entryNum(p.s); if (n !== null) apEntries.set(n, p.s); }
  const apPairs = [...apEntries.keys()].map(o => ({ o, nn: oldToNew.get(o), s: renumberEntry(apEntries.get(o), oldToNew.get(o)) }))
    .sort((a, b) => a.nn - b.nn);
  apPairs.forEach(p => { appendixRemap[p.o] = p.nn; });
  const apQueue = apPairs.map(p => p.s); let q2 = 0;
  newAppendix = apPieces.map(p => {
    if (p.type === 'gap') return p.s;
    return entryNum(p.s) !== null ? apQueue[q2++] : p.s;
  }).join('');
  if (q2 !== apQueue.length) fail('附录重排队列未消费完');
}

// ---- 5) 组装 + 自校验 + 写盘 ----
const out = newBody + newMain + (APPENDIX ? newAppendix : '');
const bal = t => {
  const o = (out.match(new RegExp('<' + t + '[ >]', 'g')) || []).length;
  const c = (out.match(new RegExp('</' + t + '>', 'g')) || []).length;
  return o === c ? o + '/' + c : o + '/' + c + ' MISMATCH';
};
const bp = bal('w:p'), br = bal('w:r'), bt = bal('w:t');
console.log('标签平衡: w:p ' + bp + ' | w:r ' + br + ' | w:t ' + bt);
if (/MISMATCH/.test(bp + br + bt)) fail('标签不平衡，放弃写盘');

// 改后自校验（重排会改变文本长度，边界偏移必须在 out 上重新定位）
{
  const fe2 = out.match(/<w:t[^>]*>\[1\] (?=[^\d])/);
  if (!fe2) fail('改后未找到 [1] 条目');
  const lps2 = paraStart(out, fe2.index);
  const lre2 = APPENDIX ? paraStart(out, out.indexOf(APPENDIX)) : out.length;
  const seen = new Set(); const seq = [];
  const re = /(<w:t[^>]*>)([^<]*)(<\/w:t>)/g; let m;
  const nb = out.slice(0, lps2);
  while ((m = re.exec(nb))) for (const g of parseGroups(m[2])) for (const n of [...g.nums].sort((a, b) => a - b)) if (!seen.has(n)) { seen.add(n); seq.push(n); }
  if (!(seq.length === N && seq.every((v, i) => v === i + 1))) fail('改后首现序列非 1..N 单调: ' + seq.join(','));
  const entries = [];
  for (const p of paras(out, lps2, lre2)) { const n = entryNum(out.slice(p.start, p.end)); if (n !== null) entries.push(n); }
  if (!(entries.length === N && entries.every((v, i) => v === i + 1))) fail('改后列表非 1..N 有序: ' + entries.join(','));
}

fs.writeFileSync(FILE, out, 'utf8');
const report = {
  generatedAt: new Date().toISOString(), file: FILE, N,
  appendix: APPENDIX, order, mapping: Object.fromEntries(order.map(o => [o, oldToNew.get(o)])), appendixRemap,
};
fs.writeFileSync(dir + '/renumber_report.json', JSON.stringify(report, null, 2), 'utf8');
console.log('重排完成: 首现顺序(旧号) = ' + order.join(','));
if (APPENDIX) console.log('附录联动: ' + Object.entries(appendixRemap).map(([o, n]) => '[' + o + ']→[' + n + ']').join(' '));
console.log('报告已写: ' + dir + '/renumber_report.json');
