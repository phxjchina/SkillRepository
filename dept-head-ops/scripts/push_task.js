#!/usr/bin/env node
'use strict';
/*
 * dept-head-ops · 任务派发与监督推送脚本（Node 版）
 *
 * 本脚本是 push_task.py 的等价 Node 实现，用于在仅有 Node 运行时的环境下
 * 被 WorkBuddy 自动化（automation）调用。行为与原 Python 版保持一致：
 *   - 系主任一句话派活 -> 写入中央台账 -> 企业微信推送责任人
 *   - 三级催办：到期前2天软提醒 / 到期日硬提醒 / 逾期转状态并推主任约谈
 *   - 待拍板扫描 -> 反向推送系主任（HEAD_WEBHOOK），积压>3天升级
 *   - weekly / monthly / party 周期动作 + 周月运营健康度看板
 *   - 状态标记：done / pending / list / board
 * 未配置 webhook 时自动降级：仅落盘 state/last_push.md，不报错。
 *
 * 运行（由自动化调用）：
 *   node push_task.js add --owner 张晓丽 --task "..." --due 2026-10-10 --deliver "报告"
 *   node push_task.js scan                 # 全扫：软提醒 + 硬提醒 + 逾期 + 待拍板
 *   node push_task.js scan --only waiting  # 仅待拍板（工作日 08:30 用）
 *   node push_task.js scan --only overdue  # 仅逾期
 *   node push_task.js pending DH-20261003-01   # 标记待拍板
 *   node push_task.js done    DH-20261003-01   # 标记完成，闭环
 *   node push_task.js list                 # 打印台账（UTF-8 安全）
 *   node push_task.js board                # 系部运营健康度看板（私推主任）
 *   node push_task.js weekly | monthly | party
 *   node push_task.js test                 # 企业微信连通性自检
 *
 * 测试/离线开关：设置环境变量 PT_LOCAL=1 可强制 webhook 为空，仅本地落盘，
 * 便于在不配置企业微信时验证脚本逻辑（自动化正式运行请移除该变量）。
 */

const fs = require('fs');
const os = require('os');
const path = require('path');

const SKILL_DIR = path.dirname(path.dirname(path.resolve(__filename)));
const STATE_DIR = path.join(SKILL_DIR, 'state');
const BACKLOG = path.join(STATE_DIR, 'backlog.csv');
const LAST_PUSH = path.join(STATE_DIR, 'last_push.md');

// ===================== 配置区（一次性填写）=====================
const CONFIG = {
  // 系部工作群机器人 webhook（推给副主任/委员 + 全体）
  DEPT_WEBHOOK: 'https://work.weixin.qq.com/wework_admin/common/openBotProfile/248e1bcecc9003e3129ea5302408c3c65d',
  // 彭老师私人推送 webhook（反向 push 你拍板/预警）
  HEAD_WEBHOOK: 'https://work.weixin.qq.com/wework_admin/common/openBotProfile/247b83b4b7102a1f6893678a6dfc196b44',
  // 企业微信成员 userid，用于 @。姓名必须与 backlog 中 owner 一致；留空则退化为文本点名
  USER_MAP: {
    '张晓丽': '',
    '曹敬馨': '',
    '侯媛媛': '',
    '范文娜': '',
    '宋飞': '',
    '薛杉': '',
    '金聪': '',
    '贾楠': '',
    '党支部书记': '',
  },
};
// =============================================================

// 测试/离线开关：PT_LOCAL=1 时强制 webhook 为空，仅本地落盘
if (process.env.PT_LOCAL) {
  CONFIG.DEPT_WEBHOOK = '';
  CONFIG.HEAD_WEBHOOK = '';
}

const FIELDS = ['id', 'task', 'owner', 'co', 'due', 'deliverable',
  'supervisor', 'status', 'source', 'created', 'note'];

// 待拍板积压超过 N 天升级为「建议立即拍板 + 约谈」
const AGING_DAYS = 3;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function ensure_state() {
  if (!fs.existsSync(STATE_DIR)) fs.mkdirSync(STATE_DIR, { recursive: true });
  if (!fs.existsSync(BACKLOG)) {
    fs.writeFileSync(BACKLOG, FIELDS.join(',') + '\n', 'utf8');
  }
}

function nowDate() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

function fmtDate(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function nowStamp() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' +
    String(d.getDate()).padStart(2, '0') + ' ' +
    String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
}

function parse_due(s) {
  s = (s || '').trim();
  const fmts = [/^(\d{4})-(\d{2})-(\d{2})$/, /^(\d{4})\/(\d{2})\/(\d{2})$/];
  for (const re of fmts) {
    const m = s.match(re);
    if (m) {
      const d = new Date(+m[1], +m[2] - 1, +m[3]);
      d.setHours(0, 0, 0, 0);
      return d;
    }
  }
  return null;
}

function daysBetween(a, b) {
  return Math.round((a - b) / 86400000);
}

// ---------- CSV（支持引号转义与字段内逗号/换行） ----------
function parseCSV(text) {
  text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const rows = [];
  let row = [], field = '', i = 0, inQuotes = false;
  while (i < text.length) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i += 2; continue; }
        inQuotes = false; i++; continue;
      }
      field += c; i++; continue;
    } else {
      if (c === '"') { inQuotes = true; i++; continue; }
      if (c === ',') { row.push(field); field = ''; i++; continue; }
      if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; i++; continue; }
      field += c; i++;
    }
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows;
}

function csvEscape(s) {
  s = (s == null) ? '' : String(s);
  if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

function read_rows() {
  ensure_state();
  if (!fs.existsSync(BACKLOG)) fs.writeFileSync(BACKLOG, FIELDS.join(',') + '\n', 'utf8');
  let buf = fs.readFileSync(BACKLOG);
  let text = buf.toString('utf8');
  if (buf[0] === 0xEF && buf[1] === 0xBB && buf[2] === 0xBF) text = text.slice(1);
  const lines = parseCSV(text);
  if (lines.length === 0) return [];
  const rows = lines.slice(1).map((cols) => {
    const o = {};
    FIELDS.forEach((f, idx) => { o[f] = (cols[idx] !== undefined) ? cols[idx] : ''; });
    return o;
  });
  return rows;
}

function write_rows(rows) {
  let out = FIELDS.join(',') + '\n';
  for (const r of rows) {
    out += FIELDS.map((f) => csvEscape(r[f] || '')).join(',') + '\n';
  }
  fs.writeFileSync(BACKLOG, out, 'utf8');
}

function next_id() {
  const rows = read_rows();
  const d = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  const prefix = 'DH-' + d;
  const n = rows.filter((r) => (r.id || '').startsWith(prefix)).length;
  return prefix + '-' + String(n + 1).padStart(2, '0');
}

function append_task(owner, task, due, deliver, co, source, note) {
  ensure_state();
  const tid = next_id();
  const row = {};
  FIELDS.forEach((k) => { row[k] = ''; });
  row.id = tid;
  row.task = task;
  row.owner = owner;
  row.co = co || '';
  row.due = due;
  row.deliverable = deliver;
  row.supervisor = '彭寒';
  row.status = '进行中';
  row.source = source || '系主任';
  row.created = fmtDate(new Date());
  row.note = note || '';
  const all = read_rows();
  all.push(row);
  write_rows(all);
  return [tid, row];
}

function at_user(name) {
  const uid = CONFIG.USER_MAP[name];
  return uid ? '<@' + uid + '>' : '【' + name + '】';
}

async function _post(webhook, payload) {
  let last = null;
  for (let i = 0; i < 3; i++) {
    try {
      const resp = await fetch(webhook, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const text = await resp.text();
      return [true, text];
    } catch (e) {
      last = e;
      if (i < 2) await sleep(2000);
    }
  }
  return [false, String(last)];
}

async function push(webhook, title, content_lines, mention) {
  let md = '## ' + title + '\n' + content_lines.join('\n');
  if (mention) md = mention + '\n' + md;
  if (!fs.existsSync(STATE_DIR)) fs.mkdirSync(STATE_DIR, { recursive: true });
  fs.appendFileSync(LAST_PUSH, '\n\n[' + nowStamp() + '] ' + title + '\n' + md + '\n', 'utf8');
  if (!webhook) {
    console.log('[local] 未配置 webhook，仅本地落盘 state/last_push.md');
    return false;
  }
  const [ok, info] = await _post(webhook, { msgtype: 'markdown', markdown: { content: md } });
  if (ok) {
    console.log('[ok] 推送成功:', info);
  } else {
    console.log('[fail] 推送失败(已落盘):', info);
    fs.appendFileSync(LAST_PUSH, '\n[FAIL-RETRY-LATER] ' + title + ' | ' + info + '\n', 'utf8');
  }
  return ok;
}

// ---------- 待拍板积压天数 ----------
function set_note_flag(row, key, value) {
  const parts = (row.note || '').split(';').filter((p) => p.trim() && !p.startsWith(key + '='));
  parts.push(key + '=' + value);
  row.note = parts.join(';');
}

function get_note_flag(row, key) {
  for (const p of (row.note || '').split(';')) {
    if (p.startsWith(key + '=')) return p.split('=', 2)[1].trim();
  }
  return '';
}

function waiting_days(r) {
  const s = get_note_flag(r, 'pending_since') || r.created || '';
  const d = parse_due(s);
  if (d == null) return 0;
  return Math.max(0, daysBetween(nowDate(), d));
}

// ---------- 运营健康度看板 ----------
function board_lines(rows) {
  const st = {};
  for (const r of rows) {
    const s = r.status || '未填';
    st[s] = (st[s] || 0) + 1;
  }
  const lines = [
    '**系部运营健康度**',
    '- 台账总量：**' + rows.length + '** 条',
    '- 进行中 ' + (st['进行中'] || 0) + ' ｜ 待拍板 ' + (st['待拍板'] || 0) +
      ' ｜ 逾期 ' + (st['逾期'] || 0) + ' ｜ 已完成 ' + (st['已完成'] || 0),
  ];
  const by_owner = {};
  for (const r of rows) {
    if (r.status === '已完成') continue;
    const o = r.owner || '未指派';
    if (!by_owner[o]) by_owner[o] = { '进行中': 0, '待拍板': 0, '逾期': 0 };
    if (by_owner[o][r.status] !== undefined) by_owner[o][r.status] += 1;
  }
  if (Object.keys(by_owner).length) {
    lines.push('- **按责任人：**');
    const sorted = Object.entries(by_owner).sort((a, b) => b[1]['逾期'] - a[1]['逾期']);
    for (const [o, c] of sorted) {
      lines.push('  - ' + o + '：进行中 ' + c['进行中'] + ' / 待拍板 ' + c['待拍板'] + ' / 逾期 ' + c['逾期']);
    }
  }
  const soon = [];
  for (const r of rows) {
    if (r.status === '已完成') continue;
    const d = parse_due(r.due || '');
    if (d && daysBetween(d, nowDate()) >= 0 && daysBetween(d, nowDate()) <= 7) soon.push([d, r]);
  }
  if (soon.length) {
    soon.sort((a, b) => a[0] - b[0]);
    lines.push('- **未来 7 天到期：**');
    for (const [d, r] of soon.slice(0, 8)) {
      lines.push('  - ' + fmtDate(d).slice(5) + ' ' + r.owner + '：' + r.task + '（' + r.id + '，' + r.status + '）');
    }
  }
  const risk = [];
  if (st['逾期']) risk.push('有 ' + st['逾期'] + ' 项逾期，建议按 §十 约谈并纳入考核依据');
  const aged = rows.filter((r) => r.status === '待拍板' && waiting_days(r) > AGING_DAYS);
  if (aged.length) risk.push('有 ' + aged.length + ' 项待拍板积压超过 ' + AGING_DAYS + ' 天，建议今日清空');
  lines.push('- **风险提示：**' + (risk.length ? risk.join('；') : '无，运转正常'));
  return lines;
}

// ---------- 命令 ----------
function cmd_add(a) {
  const [tid] = append_task(a.owner, a.task, a.due, a.deliver, a.co, a.source, a.note);
  console.log('已派发 ' + tid + ' -> ' + a.owner + ' | 截止 ' + a.due + ' | 交付 ' + a.deliver);
  const lines = [
    '> 任务编号：**' + tid + '**',
    '> 负责人：' + at_user(a.owner),
    '> 截止：' + a.due,
    '> 交付物：' + a.deliver,
    '> 内容：' + a.task,
  ];
  if (a.co) lines.splice(3, 0, '> 协同：' + a.co);
  return push(CONFIG.DEPT_WEBHOOK, '📌 系部新任务派发', lines, at_user(a.owner));
}

async function cmd_scan(a) {
  const only = a.only || '';
  const rows = read_rows();
  const t = nowDate();
  const overdue = [], waiting = [], due_soon = [], due_today = [], aged = [];

  for (const r of rows) {
    if (r.status === '已完成') continue;
    const d = parse_due(r.due || '');
    if (d == null) continue;
    const delta = daysBetween(d, t);
    if (r.status === '待拍板') {
      waiting.push(r);
      if (waiting_days(r) > AGING_DAYS) aged.push(r);
    } else if (delta < 0) {
      if (r.status !== '逾期') r.status = '逾期';
      overdue.push(r);
    } else if (delta === 0) {
      due_today.push(r);
    } else if (delta <= 2) {
      due_soon.push(r);
    }
  }
  write_rows(rows);

  // 1) 软提醒：到期前 1-2 天
  if ((only === '' || only === 'overdue') && due_soon.length) {
    const sl = [];
    for (const r of due_soon) {
      const d = parse_due(r.due || '');
      sl.push('- ' + r.id + ' ' + at_user(r.owner) + '：' + r.task + '（还有 ' + daysBetween(d, t) + ' 天到期，交付物：' + r.deliverable + '）');
    }
    await push(CONFIG.DEPT_WEBHOOK, '⏳ 到期前提醒（还有 1-2 天）', ['以下任务临近截止，请责任人按时交付：'].concat(sl));
  }

  // 2) 硬提醒：今日到期
  if ((only === '' || only === 'overdue') && due_today.length) {
    const hl = due_today.map((r) => '- ' + r.id + ' ' + at_user(r.owner) + '：' + r.task + '（交付物：' + r.deliverable + '）');
    await push(CONFIG.DEPT_WEBHOOK, '🔔 今日到期，请确认交付', hl);
    await push(CONFIG.HEAD_WEBHOOK, '🔔 今日到期事项（知会）', ['今日有 ' + due_today.length + ' 项到期，如未交付明日将自动转逾期：'].concat(hl));
  }

  // 3) 反向 push 主任：待拍板
  if (only === '' || only === 'waiting') {
    const lines = [];
    if (waiting.length) {
      lines.push('**⏳ 待您拍板 ' + waiting.length + ' 项：**');
      for (const r of waiting) {
        const days = waiting_days(r);
        const flag = (days > AGING_DAYS) ? '（已积压 ' + days + ' 天）' : '（积压 ' + days + ' 天）';
        lines.push('- ' + r.id + ' ' + r.owner + '：' + r.task + ' ' + flag);
      }
      if (aged.length) lines.push('> ⚠️ ' + aged.length + ' 项积压超过 ' + AGING_DAYS + ' 天，请今日拍板，避免卡住下游。');
    }
    if (only === 'waiting' && !waiting.length) lines.push('✅ 当前无待拍板事项。');
    if (lines.length) await push(CONFIG.HEAD_WEBHOOK, '🔔 待拍板提醒（反向 push 您）', lines);
  }

  // 4) 反向 push 主任 + 群：逾期
  if (only === '' || only === 'overdue') {
    const lines = [];
    if (overdue.length) {
      lines.push('**🔴 逾期 ' + overdue.length + ' 项（建议约谈）：**');
      for (const r of overdue) {
        lines.push('- ' + r.id + ' ' + r.owner + '：' + r.task + '（原截止 ' + r.due + '，逾期 ' + daysBetween(nowDate(), parse_due(r.due)) + ' 天）');
      }
    }
    if (only === 'overdue' && !overdue.length) lines.push('✅ 当前无逾期任务。');
    if (lines.length) {
      await push(CONFIG.HEAD_WEBHOOK, '🔔 每日运营看板（反向 push 您）', lines);
      if (overdue.length) {
        const ol = overdue.map((r) => '- ' + r.id + ' ' + at_user(r.owner) + '：' + r.task + '（截止 ' + r.due + '，已逾期）');
        await push(CONFIG.DEPT_WEBHOOK, '⏰ 逾期任务提醒', ['以下任务已逾期，请尽快处理：'].concat(ol));
      }
    }
  }

  console.log('scan done: 待拍板 ' + waiting.length + ' / 逾期 ' + overdue.length + ' / 今日到期 ' + due_today.length + ' / 临期 ' + due_soon.length);
}

function cmd_pending(a) {
  const rows = read_rows();
  const hit = rows.filter((r) => r.id === a.id);
  if (!hit.length) { console.log('未找到任务 ' + a.id); return Promise.resolve(); }
  const r = hit[0];
  r.status = '待拍板';
  set_note_flag(r, 'pending_since', fmtDate(new Date()));
  write_rows(rows);
  console.log(a.id + ' 已标记【待拍板】，下次扫描将推给主任拍板');
  return push(CONFIG.HEAD_WEBHOOK, '📥 成果待您拍板', [
    '> 任务编号：**' + r.id + '**',
    '> 负责人：' + r.owner,
    '> 内容：' + r.task,
    '> 交付物：' + r.deliverable,
    '> 请主任审核拍板：通过 / 退回（注明原因）',
  ]);
}

function cmd_done(a) {
  const rows = read_rows();
  const hit = rows.filter((r) => r.id === a.id);
  if (!hit.length) { console.log('未找到任务 ' + a.id); return Promise.resolve(); }
  const r = hit[0];
  r.status = '已完成';
  set_note_flag(r, 'done_at', fmtDate(new Date()));
  write_rows(rows);
  console.log(a.id + ' 已标记【已完成】，闭环');
  return push(CONFIG.HEAD_WEBHOOK, '✅ 任务已闭环', [
    '- ' + r.id + ' ' + r.owner + '：' + r.task + '（交付物：' + r.deliverable + '）',
  ], at_user(r.owner));
}

function cmd_list(a) {
  const rows = read_rows();
  if (!rows.length) { console.log('台账为空'); return Promise.resolve(); }
  const show = a.all ? rows : rows.filter((r) => r.status !== '已完成');
  console.log('共 ' + show.length + ' 条（未显示已完成 ' + (rows.length - show.length) + ' 条，--all 查看全部）');
  for (const r of show) {
    const d = parse_due(r.due || '');
    const left = d == null ? '' : ' 剩' + daysBetween(d, nowDate()) + '天';
    console.log([r.id.padEnd(18), (r.status || '').padEnd(6), (r.owner || '').padEnd(8), r.due, '|', (r.task || '') + left, '|', r.deliverable].join(' '));
  }
  return Promise.resolve();
}

function cmd_board() {
  const rows = read_rows();
  const lines = board_lines(rows);
  for (const l of lines) console.log(l);
  return push(CONFIG.HEAD_WEBHOOK, '📊 系部运营健康度看板', lines);
}

function cmd_weekly() {
  const rows = read_rows();
  const pk = rows.filter((r) => (r.task || '').includes('排课') && r.status === '进行中');
  const lines = ['**本周排课推进检查**'];
  if (pk.length) {
    for (const r of pk) lines.push('- ' + r.id + ' ' + r.owner + '：' + r.task + '（' + r.status + '，截止 ' + r.due + '）');
  } else {
    lines.push('- 暂无在途排课任务，请确认是否已启动下学期 T1 摸底。');
  }
  lines.push('请曹敬馨反馈 T1 回收 / T2 出稿进度。');
  return Promise.all([
    push(CONFIG.DEPT_WEBHOOK, '🗓️ 每周排课推进', lines, at_user('曹敬馨')),
    push(CONFIG.HEAD_WEBHOOK, '🗓️ 每周排课推进 + 运营健康度', lines.concat(['']).concat(board_lines(rows))),
  ]);
}

function cmd_monthly() {
  const rows = read_rows();
  const lines = [
    '**下月系部工作预排 + 推进会准备**',
    '1. 各牵头人准备月度进展 + 难点（T5 模板）',
    '2. 排课：确认 T1 回收 / T2 出稿 / 冲突自检',
    '3. 科研/申硕：申报进度 + 台账（张晓丽）',
    '4. 党支部：T7 未勾选项清账（书记）',
    '5. 待彭老师拍板事项汇总',
  ];
  const waiting = rows.filter((r) => r.status === '待拍板');
  if (waiting.length) lines.push('6. 当前待拍板 ' + waiting.length + ' 项，建议推进会前清空');
  return Promise.all([
    push(CONFIG.DEPT_WEBHOOK, '📋 月度推进会准备清单', lines),
    push(CONFIG.HEAD_WEBHOOK, '📋 月度推进会准备 + 运营健康度', lines.concat(['']).concat(board_lines(rows))),
  ]);
}

function cmd_party() {
  const rows = read_rows();
  const keys = ['党建', '党支部', '三会一课', '第一议题', '党费'];
  const party = rows.filter((r) => keys.some((k) => (r.task || '').includes(k)) && ['进行中', '待拍板'].includes(r.status));
  const lines = ['**党支部月度工作提醒（T7 台账）**'];
  if (party.length) {
    for (const r of party) lines.push('- ' + r.id + ' ' + r.owner + '：' + r.task + '（' + r.status + '）');
  } else {
    lines.push('- 请书记核对 T7 年度台账本月应完成项，滞后转 T6 督办。');
  }
  return Promise.all([
    push(CONFIG.DEPT_WEBHOOK, '🚩 党支部月度提醒', lines, at_user('党支部书记')),
    push(CONFIG.HEAD_WEBHOOK, '🚩 党支部月度提醒（知会）', lines),
  ]);
}

async function cmd_test() {
  const targets = [
    ['系部工作群 DEPT_WEBHOOK', CONFIG.DEPT_WEBHOOK],
    ['彭老师私人 HEAD_WEBHOOK', CONFIG.HEAD_WEBHOOK],
  ];
  for (const [name, hook] of targets) {
    if (!hook) { console.log('[跳过] ' + name + ' 未配置'); continue; }
    const ok = await push(hook, '企业微信连通测试', ['- 收到这条，说明 **' + name + '** 配置正确', '- 时间：' + nowStamp()]);
    console.log('[' + (ok ? '成功' : '失败') + '] ' + name);
  }
  const mapped = Object.entries(CONFIG.USER_MAP).filter(([, v]) => v).map(([k]) => k);
  console.log('已填 userid 的成员：' + (mapped.length ? mapped.join('、') : '（无，将退化为文本点名）'));
}

// ---------- 参数解析 ----------
function parseArgs(argv) {
  const cmd = argv[0];
  const rest = argv.slice(1);
  const a = {};
  for (let i = 0; i < rest.length; i++) {
    const tok = rest[i];
    if (tok === '--only') { a.only = rest[++i]; }
    else if (tok === '--all') { a.all = true; }
    else if (tok === '--owner') { a.owner = rest[++i]; }
    else if (tok === '--task') { a.task = rest[++i]; }
    else if (tok === '--due') { a.due = rest[++i]; }
    else if (tok === '--deliver') { a.deliver = rest[++i]; }
    else if (tok === '--co') { a.co = rest[++i]; }
    else if (tok === '--source') { a.source = rest[++i]; }
    else if (tok === '--note') { a.note = rest[++i]; }
    else if (!cmd && /^[A-Z]{2}-\d{8}-\d{2}$/.test(tok)) { a.id = tok; } // 兼容无子命令直接给 id 的情形（不会触发）
    else { a.id = tok; }
  }
  return { cmd, a };
}

async function main() {
  const { cmd, a } = parseArgs(process.argv.slice(2));
  switch (cmd) {
    case 'add': await cmd_add(a); break;
    case 'scan': await cmd_scan(a); break;
    case 'done': await cmd_done(a); break;
    case 'pending': await cmd_pending(a); break;
    case 'list': await cmd_list(a); break;
    case 'board': await cmd_board(); break;
    case 'weekly': await cmd_weekly(); break;
    case 'monthly': await cmd_monthly(); break;
    case 'party': await cmd_party(); break;
    case 'test': await cmd_test(); break;
    default:
      console.log('用法: node push_task.js <add|scan|pending|done|list|board|weekly|monthly|party|test> [选项]');
      console.log('  add   --owner --task --due --deliver [--co --source --note]');
      console.log('  scan  [--only waiting|overdue]');
      console.log('  list  [--all]');
      break;
  }
}

main().catch((e) => { console.error('运行出错:', e); process.exit(1); });
