#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
排课冲突检查器（dept-head-ops 技能配套）

用法：
    python schedule_check.py 排课.csv
    python schedule_check.py            # 无参数：生成示例 CSV 并演示

输入 CSV 列（表头可含/不含，按顺序或按列名识别）：
    课程, 教师, 星期, 节次, 教室(可选), 班级(可选)
例：
    机器学习,张三,周一,1-2,教三201,智科2301
    数据结构,李四,周一,1-2,教三202,计科2301

检查项：
    1. 教师时间冲突：同一教师同一(星期,节次)排了不同课程
    2. 教室冲突：同一教室同一(星期,节次)排了不同课程
    3. 未分配教师：课程无教师
输出：Markdown 报告（同时打印到终端）
"""
import csv
import io
import sys
import os

EXPECTED_HEADERS = ["课程", "教师", "星期", "节次", "教室", "班级"]

WEEK_MAP = {
    "周一": "周一", "星期二": "周二", "周三": "周三", "周四": "周四",
    "周五": "周五", "周六": "周六", "周日": "周日", "星期天": "周日",
    "1": "周一", "2": "周二", "3": "周三", "4": "周四",
    "5": "周五", "6": "周六", "7": "周日",
    "mon": "周一", "tue": "周二", "wed": "周三", "thu": "周四",
    "fri": "周五", "sat": "周六", "sun": "周日",
}


def norm_week(s: str) -> str:
    s = (s or "").strip()
    key = s.lower().replace("星期", "").replace("周", "").replace("week", "").strip()
    return WEEK_MAP.get(s, WEEK_MAP.get(key, s))


def norm_period(s: str) -> str:
    """节次归一：去空格、去尾缀'节/课时'。'1-2' 与 '1-2节' 视为同槽。"""
    s = (s or "").strip().replace(" ", "")
    s = s.replace("节", "").replace("课时", "")
    return s


def read_rows(path: str):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        text = f.read()
    # 尝试用表头识别列；否则按顺序
    has_header = False
    first = text.strip().splitlines()[0] if text.strip() else ""
    if first and any(h in first for h in EXPECTED_HEADERS):
        has_header = True
    reader = csv.reader(io.StringIO(text))
    lines = list(reader)
    if not lines:
        return [], {}
    if has_header:
        header = [h.strip() for h in lines[0]]
        idx = {name: header.index(name) if name in header else None
               for name in EXPECTED_HEADERS}
        body = lines[1:]
    else:
        idx = {name: i for i, name in enumerate(EXPECTED_HEADERS)}
        body = lines
    rows = []
    for ln, cells in enumerate(body, start=1):
        if not any(c.strip() for c in cells):
            continue
        get = lambda name: cells[idx[name]].strip() if idx.get(name) is not None and idx[name] < len(cells) else ""
        rows.append({
            "line": ln,
            "课程": get("课程"),
            "教师": get("教师"),
            "星期": norm_week(get("星期")),
            "节次": norm_period(get("节次")),
            "教室": get("教室"),
            "班级": get("班级"),
        })
    return rows, idx


def check(rows):
    teacher_slot = {}   # (星期,节次) -> {教师: [行]}
    room_slot = {}      # (星期,节次) -> {教室: [行]}
    missing_teacher = []
    for r in rows:
        slot = (r["星期"], r["节次"])
        if not r["教师"]:
            missing_teacher.append(r)
            continue
        teacher_slot.setdefault(slot, {}).setdefault(r["教师"], []).append(r)
        if r["教室"]:
            room_slot.setdefault(slot, {}).setdefault(r["教室"], []).append(r)

    teacher_conflicts = []
    for slot, teachers in teacher_slot.items():
        for teacher, rs in teachers.items():
            courses = {x["课程"] for x in rs}
            if len(courses) > 1:
                teacher_conflicts.append((slot, teacher, rs))

    room_conflicts = []
    for slot, rooms in room_slot.items():
        for room, rs in rooms.items():
            courses = {x["课程"] for x in rs}
            if len(courses) > 1:
                room_conflicts.append((slot, room, rs))
    return teacher_conflicts, room_conflicts, missing_teacher


def render(rows, teacher_conflicts, room_conflicts, missing_teacher):
    total = len(rows)
    out = []
    out.append("# 排课冲突检查报告")
    out.append("")
    out.append(f"- 总课程行数：{total}")
    out.append(f"- 教师时间冲突：{len(teacher_conflicts)} 处")
    out.append(f"- 教室冲突：{len(room_conflicts)} 处")
    out.append(f"- 未分配教师：{len(missing_teacher)} 处")
    out.append("")
    if not (teacher_conflicts or room_conflicts or missing_teacher):
        out.append("✅ **无冲突，方案可提交主任审核拍板。**")
        out.append("")
        return "\n".join(out)

    if teacher_conflicts:
        out.append("## ⛔ 教师时间冲突（同一教师同一时间两门课）")
        out.append("")
        out.append("| 星期 | 节次 | 教师 | 冲突课程 | 行号 |")
        out.append("|---|---|---|---|---|")
        for slot, teacher, rs in teacher_conflicts:
            courses = "、".join(sorted({x["课程"] for x in rs}))
            lines = "、".join(str(x["line"]) for x in rs)
            out.append(f"| {slot[0]} | {slot[1]} | {teacher} | {courses} | {lines} |")
        out.append("")

    if room_conflicts:
        out.append("## ⛔ 教室冲突（同一教室同一时间两门课）")
        out.append("")
        out.append("| 星期 | 节次 | 教室 | 冲突课程 | 行号 |")
        out.append("|---|---|---|---|---|")
        for slot, room, rs in room_conflicts:
            courses = "、".join(sorted({x["课程"] for x in rs}))
            lines = "、".join(str(x["line"]) for x in rs)
            out.append(f"| {slot[0]} | {slot[1]} | {room} | {courses} | {lines} |")
        out.append("")

    if missing_teacher:
        out.append("## ⚠️ 未分配教师")
        out.append("")
        out.append("| 行号 | 课程 | 星期 | 节次 | 教室 |")
        out.append("|---|---|---|---|---|")
        for r in missing_teacher:
            out.append(f"| {r['line']} | {r['课程']} | {r['星期']} | {r['节次']} | {r['教室']} |")
        out.append("")

    out.append("> 冲突须在曹敬馨修改、主任拍板前清零。")
    out.append("")
    return "\n".join(out)


SAMPLE = """课程,教师,星期,节次,教室,班级
机器学习,张三,周一,1-2,教三201,智科2301
数据结构,李四,周一,1-2,教三202,计科2301
计算机视觉,张三,周一,1-2,教三203,智科2302
操作系统,王五,周二,3-4,教三201,智科2301
未排教师课,,周一,5-6,教三205,计科2302
神经网络,赵六,周三,1-2,教三201,智科2302
"""


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if not os.path.exists(path):
            print(f"文件不存在: {path}")
            sys.exit(2)
        rows, _ = read_rows(path)
    else:
        print("【未提供 CSV，使用内置示例演示】\n")
        import tempfile
        tmp = os.path.join(tempfile.gettempdir(), "schedule_sample.csv")
        with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
            f.write(SAMPLE)
        rows, _ = read_rows(tmp)
        path = tmp

    tc, rc, mt = check(rows)
    report = render(rows, tc, rc, mt)
    print(report)
    # 同时落盘为同目录 md，便于归档
    out_path = os.path.splitext(path)[0] + "_check_report.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n报告已保存：{out_path}")


if __name__ == "__main__":
    main()
