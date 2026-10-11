#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dept-head-ops · 任务派发与监督推送脚本
配合 WorkBuddy automation 使用，实现：
  - 系主任一句话派活 -> 写入中央台账 -> 企业微信推送责任人
  - 三级催办：到期前2天软提醒 / 到期日硬提醒 / 逾期转状态并推主任约谈
  - 待拍板扫描 -> 反向推送系主任（HEAD_WEBHOOK），积压>3天升级
  - weekly / monthly / party 周期动作 + 周月运营健康度看板
  - 状态标记：done / pending / list / board
未配置 webhook 时自动降级：仅落盘 state/last_push.md，不报错。

用法：
  python push_task.py add --owner 张晓丽 --task "..." --due 2026-10-10 --deliver "报告"
  python push_task.py scan                 # 全扫：软提醒 + 硬提醒 + 逾期 + 待拍板
  python push_task.py scan --only waiting  # 仅待拍板（工作日 08:30 用）
  python push_task.py scan --only overdue  # 仅逾期
  python push_task.py pending DH-20261003-01   # 标记待拍板（成果已交，等主任拍板）
  python push_task.py done    DH-20261003-01   # 标记完成，闭环
  python push_task.py list                 # 打印台账（UTF-8 安全，不用开 Excel）
  python push_task.py board                # 系部运营健康度看板（私推主任）
  python push_task.py weekly | monthly | party
  python push_task.py test                 # 企业微信连通性自检
"""

import argparse
import csv
import json
import os
import time
import urllib.request
from datetime import datetime, date

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")
BACKLOG = os.path.join(STATE_DIR, "backlog.csv")
LAST_PUSH = os.path.join(STATE_DIR, "last_push.md")

# ===================== 配置区（一次性填写）=====================
CONFIG = {
    # 系部工作群机器人 webhook（推给副主任/委员 + 全体）
    "DEPT_WEBHOOK": "https://work.weixin.qq.com/wework_admin/common/openBotProfile/248e1bcecc9003e3129ea5302408c3c65d",
    # 彭老师私人推送 webhook（反向 push 你拍板/预警）
    "HEAD_WEBHOOK": "https://work.weixin.qq.com/wework_admin/common/openBotProfile/247b83b4b7102a1f6893678a6dfc196b44",
    # 企业微信成员 userid，用于 @。姓名必须与 backlog 中 owner 一致；留空则退化为文本点名
    "USER_MAP": {
        "张晓丽": "",
        "曹敬馨": "",
        "侯媛媛": "",
        "范文娜": "",
        "宋飞": "",
        "薛杉": "",
        "金聪": "",
        "贾楠": "",
        "党支部书记": "",
    },
}
# =============================================================

FIELDS = ["id", "task", "owner", "co", "due", "deliverable",
          "supervisor", "status", "source", "created", "note"]

# 待拍板积压超过 N 天升级为「建议立即拍板 + 约谈」
AGING_DAYS = 3


def ensure_state():
    os.makedirs(STATE_DIR, exist_ok=True)
    if not os.path.exists(BACKLOG):
        with open(BACKLOG, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(FIELDS)


def today():
    return date.today()


def parse_due(s):
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def read_rows():
    """读台账。UTF-8 优先；若被 Excel 存成 ANSI/GBK 则自动回退，并即时转存回 UTF-8 自愈。"""
    ensure_state()
    rows, used = [], None
    for enc in ("utf-8-sig", "gbk"):
        try:
            with open(BACKLOG, encoding=enc) as f:
                rows = list(csv.DictReader(f))
            used = enc
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if used and used != "utf-8-sig":
        try:
            write_rows(rows)
            print("[fix] 台账当前为 %s 编码，已自动转存为 UTF-8（以后别用 Excel 直接另存）" % used)
        except Exception:
            pass
    return rows


def write_rows(rows):
    """台账一律以 UTF-8（无 BOM）写回。"""
    with open(BACKLOG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            clean = {k: (r.get(k) or "") for k in FIELDS}
            w.writerow(clean)


def next_id():
    rows = read_rows()
    d = datetime.now().strftime("%Y%m%d")
    n = sum(1 for r in rows if (r.get("id") or "").startswith("DH-" + d))
    return "DH-%s-%02d" % (d, n + 1)


def append_task(owner, task, due, deliver, co="", source="系主任", note=""):
    ensure_state()
    tid = next_id()
    row = {k: "" for k in FIELDS}
    row.update({
        "id": tid, "task": task, "owner": owner, "co": co, "due": due,
        "deliverable": deliver, "supervisor": "彭寒", "status": "进行中",
        "source": source, "created": datetime.now().strftime("%Y-%m-%d"),
        "note": note,
    })
    with open(BACKLOG, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=FIELDS).writerow(row)
    return tid, row


def at_user(name):
    uid = CONFIG["USER_MAP"].get(name, "")
    return "<@%s>" % uid if uid else "【%s】" % name


def _post(webhook, payload):
    """带重试的推送：最多 3 次，间隔 2 秒，规避企业微信临时限流。"""
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(
                webhook,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=10)
            return True, resp.read().decode("utf-8", "ignore")
        except Exception as e:
            last = e
            if i < 2:
                time.sleep(2)
    return False, str(last)


def push(webhook, title, content_lines, mention=None):
    md = "## %s\n" % title + "\n".join(content_lines)
    if mention:
        md = mention + "\n" + md
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(LAST_PUSH, "a", encoding="utf-8") as f:
        f.write("\n\n[%s] %s\n%s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M"), title, md))
    if not webhook:
        print("[local] 未配置 webhook，仅本地落盘 state/last_push.md")
        return False
    ok, info = _post(webhook, {"msgtype": "markdown", "markdown": {"content": md}})
    if ok:
        print("[ok] 推送成功:", info)
    else:
        print("[fail] 推送失败(已落盘):", info)
        with open(LAST_PUSH, "a", encoding="utf-8") as f:
            f.write("\n[FAIL-RETRY-LATER] %s | %s\n" % (title, info))
    return ok


# ---------- 待拍板积压天数 ----------

def set_note_flag(row, key, value):
    parts = [p for p in (row.get("note") or "").split(";") if p.strip() and not p.startswith(key + "=")]
    parts.append("%s=%s" % (key, value))
    row["note"] = ";".join(parts)


def get_note_flag(row, key):
    for p in (row.get("note") or "").split(";"):
        if p.startswith(key + "="):
            return p.split("=", 1)[1].strip()
    return ""


def waiting_days(r):
    """待拍板积压天数：以 pending_since 为准，缺失则退回 created。"""
    s = get_note_flag(r, "pending_since") or r.get("created") or ""
    d = parse_due(s)
    if d is None:
        return 0
    return max(0, (today() - d).days)


# ---------- 运营健康度看板 ----------

def board_lines(rows):
    st = {}
    for r in rows:
        st[r.get("status") or "未填"] = st.get(r.get("status") or "未填", 0) + 1
    lines = ["**系部运营健康度**",
             "- 台账总量：**%d** 条" % len(rows),
             "- 进行中 %d ｜ 待拍板 %d ｜ 逾期 %d ｜ 已完成 %d" % (
                 st.get("进行中", 0), st.get("待拍板", 0),
                 st.get("逾期", 0), st.get("已完成", 0))]
    by_owner = {}
    for r in rows:
        s = r.get("status")
        if s == "已完成":
            continue
        o = r.get("owner") or "未指派"
        by_owner.setdefault(o, {"进行中": 0, "待拍板": 0, "逾期": 0})
        if s in by_owner[o]:
            by_owner[o][s] += 1
    if by_owner:
        lines.append("- **按责任人：**")
        for o, c in sorted(by_owner.items(), key=lambda x: -x[1]["逾期"]):
            lines.append("  - %s：进行中 %d / 待拍板 %d / 逾期 %d" % (o, c["进行中"], c["待拍板"], c["逾期"]))
    soon = []
    for r in rows:
        if r.get("status") == "已完成":
            continue
        d = parse_due(r.get("due") or "")
        if d and 0 <= (d - today()).days <= 7:
            soon.append((d, r))
    if soon:
        soon.sort(key=lambda x: x[0])
        lines.append("- **未来 7 天到期：**")
        for d, r in soon[:8]:
            lines.append("  - %s %s：%s（%s，%s）" % (d.strftime("%m-%d"), r.get("owner"),
                                                     r.get("task"), r.get("id"), r.get("status")))
    risk = []
    if st.get("逾期", 0):
        risk.append("有 %d 项逾期，建议按 §十 约谈并纳入考核依据" % st.get("逾期", 0))
    aged = [r for r in rows if r.get("status") == "待拍板" and waiting_days(r) > AGING_DAYS]
    if aged:
        risk.append("有 %d 项待拍板积压超过 %d 天，建议今日清空" % (len(aged), AGING_DAYS))
    lines.append("- **风险提示：**" + ("；".join(risk) if risk else "无，运转正常"))
    return lines


# ---------- 命令 ----------

def cmd_add(args):
    tid, row = append_task(args.owner, args.task, args.due, args.deliver,
                           args.co, args.source, args.note)
    print("已派发 %s -> %s | 截止 %s | 交付 %s" % (tid, args.owner, args.due, args.deliver))
    lines = [
        "> 任务编号：**%s**" % tid,
        "> 负责人：%s" % at_user(args.owner),
        "> 截止：%s" % args.due,
        "> 交付物：%s" % args.deliver,
        "> 内容：%s" % args.task,
    ]
    if args.co:
        lines.insert(3, "> 协同：%s" % args.co)
    push(CONFIG["DEPT_WEBHOOK"], "📌 系部新任务派发", lines, mention=at_user(args.owner))


def cmd_scan(args):
    only = getattr(args, "only", "") or ""
    rows = read_rows()
    t = today()
    overdue, waiting, due_soon, due_today, aged = [], [], [], [], []

    for r in rows:
        if r.get("status") == "已完成":
            continue
        d = parse_due(r.get("due") or "")
        if d is None:
            continue
        delta = (d - t).days
        if r.get("status") == "待拍板":
            waiting.append(r)
            if waiting_days(r) > AGING_DAYS:
                aged.append(r)
        elif delta < 0:
            if r.get("status") != "逾期":
                r["status"] = "逾期"
            overdue.append(r)
        elif delta == 0:
            due_today.append(r)
        elif delta <= 2:
            due_soon.append(r)
    write_rows(rows)

    # ---- 1) 软提醒：到期前 1-2 天，群里 @ 责任人 ----
    if only in ("", "overdue") and due_soon:
        sl = []
        for r in due_soon:
            d = parse_due(r.get("due") or "")
            sl.append("- %s %s：%s（还有 %d 天到期，交付物：%s）" % (
                r.get("id"), at_user(r.get("owner")), r.get("task"),
                (d - t).days, r.get("deliverable")))
        push(CONFIG["DEPT_WEBHOOK"], "⏳ 到期前提醒（还有 1-2 天）",
             ["以下任务临近截止，请责任人按时交付："] + sl)

    # ---- 2) 硬提醒：今日到期未交，群 @ 责任人 + 抄送主任 ----
    if only in ("", "overdue") and due_today:
        hl = ["- %s %s：%s（交付物：%s）" % (r.get("id"), at_user(r.get("owner")),
                                        r.get("task"), r.get("deliverable")) for r in due_today]
        push(CONFIG["DEPT_WEBHOOK"], "🔔 今日到期，请确认交付", hl)
        push(CONFIG["HEAD_WEBHOOK"], "🔔 今日到期事项（知会）",
             ["今日有 %d 项到期，如未交付明日将自动转逾期：" % len(due_today)] + hl)

    # ---- 3) 反向 push 主任：待拍板 + 逾期 ----
    if only in ("", "waiting"):
        lines = []
        if waiting:
            lines.append("**⏳ 待您拍板 %d 项：**" % len(waiting))
            for r in waiting:
                days = waiting_days(r)
                flag = "（已积压 %d 天）" % days if days > AGING_DAYS else "（积压 %d 天）" % days
                lines.append("- %s %s：%s %s" % (r.get("id"), r.get("owner"), r.get("task"), flag))
            if aged:
                lines.append("> ⚠️ %d 项积压超过 %d 天，请今日拍板，避免卡住下游。" % (len(aged), AGING_DAYS))
        if only == "waiting" and not waiting:
            lines = ["✅ 当前无待拍板事项。"]
        if lines:
            push(CONFIG["HEAD_WEBHOOK"], "🔔 待拍板提醒（反向 push 您）", lines)

    if only in ("", "overdue"):
        lines = []
        if overdue:
            lines.append("**🔴 逾期 %d 项（建议约谈）：**" % len(overdue))
            for r in overdue:
                lines.append("- %s %s：%s（原截止 %s，逾期 %d 天）" % (
                    r.get("id"), r.get("owner"), r.get("task"),
                    r.get("due"), (t - parse_due(r.get("due"))).days))
        if only == "overdue" and not overdue:
            lines = ["✅ 当前无逾期任务。"]
        if lines:
            push(CONFIG["HEAD_WEBHOOK"], "🔔 每日运营看板（反向 push 您）", lines)

        if overdue:
            ol = ["- %s %s：%s（截止 %s，已逾期）" % (r.get("id"), at_user(r.get("owner")),
                                               r.get("task"), r.get("due")) for r in overdue]
            push(CONFIG["DEPT_WEBHOOK"], "⏰ 逾期任务提醒",
                 ["以下任务已逾期，请尽快处理："] + ol)

    print("scan done: 待拍板 %d / 逾期 %d / 今日到期 %d / 临期 %d" % (
        len(waiting), len(overdue), len(due_today), len(due_soon)))


def cmd_pending(args):
    rows = read_rows()
    hit = [r for r in rows if r.get("id") == args.id]
    if not hit:
        print("未找到任务 %s" % args.id)
        return
    r = hit[0]
    r["status"] = "待拍板"
    set_note_flag(r, "pending_since", today().strftime("%Y-%m-%d"))
    write_rows(rows)
    print("%s 已标记【待拍板】，下次扫描将推给主任拍板" % args.id)
    push(CONFIG["HEAD_WEBHOOK"], "📥 成果待您拍板", [
        "> 任务编号：**%s**" % r.get("id"),
        "> 负责人：%s" % r.get("owner"),
        "> 内容：%s" % r.get("task"),
        "> 交付物：%s" % r.get("deliverable"),
        "> 请主任审核拍板：通过 / 退回（注明原因）",
    ])


def cmd_done(args):
    rows = read_rows()
    hit = [r for r in rows if r.get("id") == args.id]
    if not hit:
        print("未找到任务 %s" % args.id)
        return
    r = hit[0]
    r["status"] = "已完成"
    set_note_flag(r, "done_at", today().strftime("%Y-%m-%d"))
    write_rows(rows)
    print("%s 已标记【已完成】，闭环" % args.id)
    push(CONFIG["DEPT_WEBHOOK"], "✅ 任务已闭环", [
        "- %s %s：%s（交付物：%s）" % (r.get("id"), r.get("owner"),
                                    r.get("task"), r.get("deliverable")),
    ], mention=at_user(r.get("owner")))


def cmd_list(args):
    rows = read_rows()
    if not rows:
        print("台账为空")
        return
    show = rows if args.all else [r for r in rows if r.get("status") != "已完成"]
    print("共 %d 条（未显示已完成 %d 条，--all 查看全部）" % (len(show), len(rows) - len(show)))
    for r in show:
        d = parse_due(r.get("due") or "")
        left = "" if d is None else " 剩%d天" % (d - today()).days
        print("%-18s %-6s %-8s %s | %s%s | %s" % (
            r.get("id"), r.get("status"), r.get("owner"), r.get("due"),
            r.get("task"), left, r.get("deliverable")))


def cmd_board(args):
    rows = read_rows()
    push(CONFIG["HEAD_WEBHOOK"], "📊 系部运营健康度看板", board_lines(rows))
    for l in board_lines(rows):
        print(l)


def cmd_weekly(args):
    rows = read_rows()
    pk = [r for r in rows if "排课" in (r.get("task") or "") and r.get("status") == "进行中"]
    lines = ["**本周排课推进检查**"]
    if pk:
        for r in pk:
            lines.append("- %s %s：%s（%s，截止 %s）" % (r.get("id"), r.get("owner"),
                                                    r.get("task"), r.get("status"), r.get("due")))
    else:
        lines.append("- 暂无在途排课任务，请确认是否已启动下学期 T1 摸底。")
    lines.append("请曹敬馨反馈 T1 回收 / T2 出稿进度。")
    push(CONFIG["DEPT_WEBHOOK"], "🗓️ 每周排课推进", lines, mention=at_user("曹敬馨"))
    push(CONFIG["HEAD_WEBHOOK"], "🗓️ 每周排课推进 + 运营健康度",
         lines + [""] + board_lines(rows))


def cmd_monthly(args):
    rows = read_rows()
    lines = [
        "**下月系部工作预排 + 推进会准备**",
        "1. 各牵头人准备月度进展 + 难点（T5 模板）",
        "2. 排课：确认 T1 回收 / T2 出稿 / 冲突自检",
        "3. 科研/申硕：申报进度 + 台账（张晓丽）",
        "4. 党支部：T7 未勾选项清账（书记）",
        "5. 待彭老师拍板事项汇总",
    ]
    waiting = [r for r in rows if r.get("status") == "待拍板"]
    if waiting:
        lines.append("6. 当前待拍板 %d 项，建议推进会前清空" % len(waiting))
    push(CONFIG["DEPT_WEBHOOK"], "📋 月度推进会准备清单", lines)
    push(CONFIG["HEAD_WEBHOOK"], "📋 月度推进会准备 + 运营健康度",
         lines + [""] + board_lines(rows))


def cmd_party(args):
    rows = read_rows()
    keys = ("党建", "党支部", "三会一课", "第一议题", "党费")
    party = [r for r in rows if any(k in (r.get("task") or "") for k in keys)
             and r.get("status") in ("进行中", "待拍板")]
    lines = ["**党支部月度工作提醒（T7 台账）**"]
    if party:
        for r in party:
            lines.append("- %s %s：%s（%s）" % (r.get("id"), r.get("owner"),
                                             r.get("task"), r.get("status")))
    else:
        lines.append("- 请书记核对 T7 年度台账本月应完成项，滞后转 T6 督办。")
    push(CONFIG["DEPT_WEBHOOK"], "🚩 党支部月度提醒", lines, mention=at_user("党支部书记"))
    push(CONFIG["HEAD_WEBHOOK"], "🚩 党支部月度提醒（知会）", lines)


def cmd_test(args):
    """连通性自检：分别向两个 webhook 发一条测试消息，打印企业微信返回的 errcode。"""
    targets = [("系部工作群 DEPT_WEBHOOK", CONFIG["DEPT_WEBHOOK"]),
               ("彭老师私人 HEAD_WEBHOOK", CONFIG["HEAD_WEBHOOK"])]
    for name, hook in targets:
        if not hook:
            print("[跳过] %s 未配置" % name)
            continue
        ok = push(hook, "企业微信连通测试",
                  ["- 收到这条，说明 **%s** 配置正确" % name,
                   "- 时间：%s" % datetime.now().strftime("%Y-%m-%d %H:%M")])
        print("[%s] %s" % ("成功" if ok else "失败", name))
    mapped = [k for k, v in CONFIG["USER_MAP"].items() if v]
    print("已填 userid 的成员：%s" % ("、".join(mapped) if mapped else "（无，将退化为文本点名）"))


def main():
    p = argparse.ArgumentParser(description="dept-head-ops 任务派发与监督")
    sub = p.add_subparsers(dest="cmd")

    a = sub.add_parser("add")
    a.add_argument("--owner", required=True)
    a.add_argument("--task", required=True)
    a.add_argument("--due", required=True, help="YYYY-MM-DD")
    a.add_argument("--deliver", required=True)
    a.add_argument("--co", default="")
    a.add_argument("--source", default="系主任")
    a.add_argument("--note", default="")

    s = sub.add_parser("scan")
    s.add_argument("--only", choices=["waiting", "overdue"], default="",
                   help="waiting=仅待拍板(工作日08:30)；overdue=仅逾期")

    d = sub.add_parser("done", help="标记任务完成，闭环")
    d.add_argument("id")
    pd = sub.add_parser("pending", help="标记任务待主任拍板")
    pd.add_argument("id")

    l = sub.add_parser("list", help="打印台账（UTF-8 安全）")
    l.add_argument("--all", action="store_true", help="含已完成")

    sub.add_parser("board", help="系部运营健康度看板（私推主任）")
    sub.add_parser("weekly")
    sub.add_parser("monthly")
    sub.add_parser("party")
    sub.add_parser("test")

    args = p.parse_args()
    if args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "scan":
        cmd_scan(args)
    elif args.cmd == "done":
        cmd_done(args)
    elif args.cmd == "pending":
        cmd_pending(args)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "board":
        cmd_board(args)
    elif args.cmd == "weekly":
        cmd_weekly(args)
    elif args.cmd == "monthly":
        cmd_monthly(args)
    elif args.cmd == "party":
        cmd_party(args)
    elif args.cmd == "test":
        cmd_test(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
