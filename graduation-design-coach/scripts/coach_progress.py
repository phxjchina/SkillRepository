#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""coach_progress.py — 毕业设计陪跑教练·个人进度卡
扫描学生材料目录，按阶段模型推断当前阶段与下一步动作，输出 Markdown 进度卡。
用法:
  python coach_progress.py --root "<学生材料目录>" --name "学生名" [--state coach_state.json] [--out 进度卡.md] [--docx]
"""
import argparse, json, os, subprocess, sys, datetime

STAGES = [
    ("1", "选题", "题目被教师确认"),
    ("2", "配合任务书", "教师正式下发任务书(三方签名)"),
    ("3", "开题报告", "开题答辩通过"),
    ("4", "工程实施", "系统达任务书主要功能>=2/3且有留痕"),
    ("5", "中期检查", "中期通过"),
    ("6", "论文撰写", "查重达标+教师审核通过"),
    ("7", "答辩准备", "答辩通过、资料归档"),
]
# 分类关键词 -> (材料, 对应阶段号)
KEYWORDS = [
    ("答辩PPT", "答辩PPT", "7"),
    ("答辩", "答辩材料", "7"),
    ("中期", "中期检查", "5"),
    ("终稿", "论文终稿", "6"),
    ("定稿", "论文定稿", "6"),
    ("初稿", "论文初稿", "6"),
    ("论文", "论文", "6"),
    ("外文翻译", "外文翻译", "3"),
    ("开题报告", "开题报告", "3"),
    ("开题", "开题材料", "3"),
    ("任务书", "任务书", "2"),
]
SKIP = ("~$", "汇总", "模板", "空白")


def classify(name):
    low = name
    for kw, label, stage in KEYWORDS:
        if kw in low:
            return label, stage
    return None, None


def scan(root):
    items = []  # (label, stage, path)
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.startswith("~$") or any(s in f for s in SKIP):
                continue
            if not f.lower().endswith((".docx", ".pptx", ".doc", ".ppt")):
                continue
            label, stage = classify(f)
            if label:
                items.append((label, stage, os.path.join(dirpath, f)))
    return items


def infer(items):
    have = {}
    for label, stage, path in items:
        have.setdefault(stage, []).append(label)
    done = max([int(s) for s in have]) if have else 0
    # 当前阶段 = 最高已完成材料的阶段；若该阶段闸门材料齐 → 已过，下一步为下一阶段
    if done == 0:
        return 1, "尚未有任何材料，从阶段1选题开始"
    cur = done
    nxt = cur + 1 if cur < 7 else None
    return cur, nxt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--name", default="学生")
    ap.add_argument("--state", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--docx", action="store_true")
    a = ap.parse_args()

    items = scan(a.root)
    cur, nxt = infer(items)
    today = datetime.date.today().isoformat()

    lines = []
    lines.append("# 个人进度卡 · %s（%s）" % (a.name, today))
    lines.append("")
    lines.append("| 阶段 | 材料 | 状态 |")
    lines.append("|---|---|---|")
    for no, title, gate in STAGES:
        mats = [os.path.basename(p) for (lb, st, p) in items if st == no]
        status = "✅ 有" if mats else "✗ 暂无"
        lines.append("| %s %s | %s | %s |" % (no, title, "、".join(mats[:3]) if mats else "—", status))
    lines.append("")
    lines.append("**当前阶段**：阶段%s %s" % (cur, STAGES[cur - 1][1]))
    if nxt:
        lines.append("**下一步**：进入阶段%s %s，闸门 = %s" % (nxt, STAGES[nxt - 1][1], STAGES[nxt - 1][2]))
    else:
        lines.append("**下一步**：全部阶段已完成，归档收尾。")
    lines.append("")
    lines.append("> 只辅导不代写：本卡只跟踪与提示，正文由学生自己完成。")

    text = "\n".join(lines)
    out = a.out or os.path.join(a.root, "个人进度卡_%s.md" % a.name)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)

    if a.state:
        state = {}
        if os.path.exists(a.state):
            try:
                state = json.load(open(a.state, encoding="utf-8"))
            except Exception:
                state = {}
        state[a.name] = {
            "updated": today, "stage": cur,
            "materials": {str(st): [os.path.basename(p) for (lb, s, p) in items if s == st]
                          for st in sorted({s for (_, s, _) in items})},
        }
        with open(a.state, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=2)
        print("[state] %s" % a.state)

    if a.docx:
        m2d = os.environ.get("MD2DOCX", r"E:/培训所需软件/练习用材料/.workbuddy/md2docx.py")
        docx_out = os.path.splitext(out)[0] + ".docx"
        try:
            subprocess.run([sys.executable, m2d, out, docx_out], check=True)
            print("[docx] %s" % docx_out)
        except Exception as e:
            print("[docx] 生成失败(%s)，Markdown 版可用" % e)


if __name__ == "__main__":
    main()
