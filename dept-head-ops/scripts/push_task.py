#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dept-head-ops · 任务派发与监督推送脚本
配合 WorkBuddy automation 使用，实现：
  - 系主任一句话派活 -> 写入中央台账 -> 企业微信推送责任人
  - 周期扫描逾期 / 待拍板 -> 反向推送系主任（HEAD_WEBHOOK）
  - weekly / monthly / party 周期动作
未配置 webhook 时自动降级：仅落盘 state/last_push.md，不报错。

用法：
  python push_task.py add --owner 张晓丽 --task "..." --due 2026-10-10 --deliver "报告"
  python push_task.py scan
  python push_task.py weekly | monthly | party
"""

import argparse
import csv
import json
import os
import urllib.request
from datetime import datetime, date

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, "state")
BACKLOG = os.path.join(STATE_DIR, "backlog.csv")
LAST_PUSH = os.path.join(STATE_DIR, "last_push.md")

# ===================== 配置区（一次性填写）=====================
CONFIG = {
    # 系部工作群机器人 webhook（推给副主任/委员 + 全体）
    "DEPT_WEBHOOK": "",
    # 彭老师私人推送 webhook（反向 push 你拍板/预警）
    "HEAD_WEBHOOK": "",
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


def ensure_state():
    os.makedirs(STATE_DIR, exist_ok=True)
    if not os.path.exists(BACKLOG):
        with open(BACKLOG, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(FIELDS)


def today():
    return date.today()


def parse_due(s):
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def next_id():
    ensure_state()
    rows = []
    with open(BACKLOG, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    d = datetime.now().strftime("%Y%m%d")
    n = sum(1 for r in rows if r["id"].startswith("DH-" + d))
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


def read_rows():
    ensure_state()
    with open(BACKLOG, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_rows(rows):
    with open(BACKLOG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def at_user(name):
    uid = CONFIG["USER_MAP"].get(name, "")
    return "<@%s>" % uid if uid else "【%s】" % name


def push(webhook, title, content_lines, mention=None):
    md = "## %s\n" % title + "\n".join(content_lines)
    if mention:
        md = mention + "\n" + md
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(LAST_PUSH, "a", encoding="utf-8") as f:
        f.write("\n\n[%s] %s\n%s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M"), title, md))
    if not webhook:
        print("⚠️ 未配置 webhook，仅本地落盘 state/last_push.md")
        return False
    payload = {"msgtype": "markdown", "markdown": {"content": md}}
    try:
        req = urllib.request.Request(
            webhook,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        print("✅ 推送成功:", resp.read().decode("utf-8", "ignore"))
        return True
    except Exception as e:
        print("⚠️ 推送失败(已落盘):", e)
        return False


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
    rows = read_rows()
    overdue, waiting = [], []
    for r in rows:
        if r["status"] in ("已完成",):
            continue
        d = parse_due(r["due"])
        if d is None:
            continue
        if r["status"] == "待拍板":
            waiting.append(r)
        elif d < today():
            r["status"] = "逾期"
            overdue.append(r)
    write_rows(rows)

    lines = []
    if waiting:
        lines.append("**⏳ 待您拍板 %d 项：**" % len(waiting))
        for r in waiting:
            lines.append("- %s %s：%s" % (r["id"], r["owner"], r["task"]))
    if overdue:
        lines.append("**🔴 逾期 %d 项（建议约谈）：**" % len(overdue))
        for r in overdue:
            lines.append("- %s %s：%s（原截止 %s）" % (r["id"], r["owner"], r["task"], r["due"]))
    if not lines:
        lines = ["✅ 当前无待拍板、无逾期任务，系部运转正常。"]
    push(CONFIG["HEAD_WEBHOOK"], "🔔 每日运营看板（反向 push 您）", lines)

    if overdue:
        ol = ["- %s %s（截止 %s，已逾期）" % (r["id"], r["task"], r["due"]) for r in overdue]
        push(CONFIG["DEPT_WEBHOOK"], "⏰ 逾期任务提醒",
             ["以下任务已逾期，请尽快处理："] + ol)


def cmd_weekly(args):
    rows = read_rows()
    pk = [r for r in rows if "排课" in r["task"] and r["status"] in ("进行中",)]
    lines = ["**本周排课推进检查**"]
    if pk:
        for r in pk:
            lines.append("- %s %s：%s（%s，截止 %s）" % (r["id"], r["owner"], r["task"], r["status"], r["due"]))
    else:
        lines.append("- 暂无在途排课任务，请确认是否已启动下学期 T1 摸底。")
    lines.append("请曹敬馨反馈 T1 回收 / T2 出稿进度。")
    push(CONFIG["DEPT_WEBHOOK"], "🗓️ 每周排课推进", lines, mention=at_user("曹敬馨"))
    push(CONFIG["HEAD_WEBHOOK"], "🗓️ 每周排课推进（知会）", lines)


def cmd_monthly(args):
    lines = [
        "**下月系部工作预排 + 推进会准备**",
        "1. 各牵头人准备月度进展 + 难点（T5 模板）",
        "2. 排课：确认 T1 回收 / T2 出稿 / 冲突自检",
        "3. 科研/申硕：申报进度 + 台账（张晓丽）",
        "4. 党支部：T7 未勾选项清账（书记）",
        "5. 待彭老师拍板事项汇总",
    ]
    push(CONFIG["HEAD_WEBHOOK"], "📋 月度推进会准备清单", lines)
    push(CONFIG["DEPT_WEBHOOK"], "📋 月度推进会准备清单", lines)


def cmd_party(args):
    rows = read_rows()
    keys = ("党建", "党支部", "三会一课", "第一议题", "党费")
    party = [r for r in rows if any(k in r["task"] for k in keys)
             and r["status"] in ("进行中", "待拍板")]
    lines = ["**党支部月度工作提醒（T7 台账）**"]
    if party:
        for r in party:
            lines.append("- %s %s：%s（%s）" % (r["id"], r["owner"], r["task"], r["status"]))
    else:
        lines.append("- 请书记核对 T7 年度台账本月应完成项，滞后转 T6 督办。")
    push(CONFIG["DEPT_WEBHOOK"], "🚩 党支部月度提醒", lines, mention=at_user("党支部书记"))
    push(CONFIG["HEAD_WEBHOOK"], "🚩 党支部月度提醒（知会）", lines)


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
    sub.add_parser("scan")
    sub.add_parser("weekly")
    sub.add_parser("monthly")
    sub.add_parser("party")
    args = p.parse_args()
    if args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "scan":
        cmd_scan(args)
    elif args.cmd == "weekly":
        cmd_weekly(args)
    elif args.cmd == "monthly":
        cmd_monthly(args)
    elif args.cmd == "party":
        cmd_party(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
