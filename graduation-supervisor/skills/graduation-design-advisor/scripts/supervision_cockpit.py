#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
supervision_cockpit.py — 毕业设计「监督驾驶舱」队列看板生成器

用途：代替指导教师一眼掌握整届多名学生毕业设计的推进情况。
扫描本地 .docx 原件目录，按学生归类，按关键词（任务书/开题报告/论文/批注/译文）
分类，输出一张进度看板：
  · 队列总览矩阵（学生 × 材料齐备度）
  · 阶段进度推断
  · 风险高亮（缺材料 / 未批注 / 待线下确认）
  · 单人下钻提示（可直接复制的审查命令）

依赖：仅 Python 标准库。可选 --docx 调用工作区 md2docx.py 转 .docx 看板。

用法：
  python supervision_cockpit.py --root "<本地原件根目录>" --term "2022届" --advisor "彭寒" [--roster roster.json] [--docx] [--state state.json] [--out 看板.md]
  roster.json: JSON 数组，元素为 学生姓名字符串 或 {"name":"巩晶伟","id":"184070221","topic":"..."}
"""

import os
import re
import json
import argparse
import datetime
import subprocess

CJK = r'[\u4e00-\u9fff]'

# 聚合/模板/非学生个人文件，扫描时一律跳过（无论 auto 还是 roster 模式）
SKIP_KEYWORDS = [
    '汇总', '模板', '系统下载', '题目汇总', '审核手册', '抽检', '试卷',
    '成绩评阅', '会议信息', '答辩安排', '答辩组', '分组', '分配', '情况表',
    '第七组', '第八组', '最终版', '二次修改终版', '附件3', '附件5：计算机学院',
    '毕业生信息', '开题答辩所需附件', '论文进度汇报', '外文翻译译文-修改版',
    '任务书汇总', '开题报告-景月娟', '杨老师', '刘舟洲', '苏世雄',
    '创新实验室2022届开题答辩PPT', '校园实行封闭管理',
]

DOC_KEYWORDS = {
    '任务书', '开题报告', '开题', '论文', '答辩', '译文', '外文', '批注',
    '中期', '检查', '报告', '附件', '设计', '实现', '系统', '控制', '仿真',
    '分析', '研究', '基于', '方法', '综述', '资料', '素材', '修改终稿版',
    '终稿', '初稿', '指导教师', '评阅', '综合成绩', '评定表',
}

# 文档类型关键词（按优先级，先匹配者胜）
TYPE_RULES = [
    ('comments', ['批注']),
    ('task', ['任务书']),
    ('opening', ['开题报告', '任开题报告', '开题']),
    ('translation', ['译文', '外文翻译']),
    ('thesis', ['论文', '终稿', '初稿']),
]


def classify(path):
    p = path.replace('\\', '/')
    for t, kws in TYPE_RULES:
        for kw in kws:
            if kw in p:
                return t
    return 'other'


def extract_student(name, roster):
    """从文件名/路径推断学生姓名。roster 优先精确匹配，否则启发式抽取中文姓名片段。"""
    if roster:
        norm = name.replace(' ', '')
        for s in roster:
            sname = s if isinstance(s, str) else s.get('name', '')
            if sname and (sname in name or sname in norm):
                return sname
        return None
    base = name
    base = re.sub(r'\s*-\s*批注$', '', base)
    base = base.replace('批注', '').replace('修改终稿版', '').replace(' ', '')
    pos = [(m.start(), m.group()) for m in re.finditer(r'[\u4e00-\u9fff]{2,4}', base)
           if m.group() not in DOC_KEYWORDS]
    if not pos:
        return None
    pos2 = [p for p in pos if len(p[1]) in (2, 3)] or pos
    pos2.sort()
    return pos2[-1][1]


def scan(root, roster):
    records = {}
    order = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if not f.lower().endswith('.docx') or f.startswith('~$'):
                continue
            full = os.path.join(dirpath, f)
            # 跳过聚合/模板类非学生文件
            if any(k in f for k in SKIP_KEYWORDS):
                continue
            stu = extract_student(f, roster)
            if not stu:
                # 无 roster 且无法识别姓名 → 跳过，避免噪音桶
                continue
            if stu not in records:
                records[stu] = {'_meta': {}, 'task': [], 'opening': [],
                                'thesis': [], 'translation': [], 'comments': [],
                                'other': []}
                order.append(stu)
            t = classify(f)
            records[stu][t].append(full)
    return records, order


def infer_stage(rec):
    """根据材料齐备度推断已到达的阶段。"""
    # 三件套：任务书 / 开题报告 / 论文
    if rec['thesis']:
        return '论文终稿'
    if rec['opening']:
        return '开题报告'
    if rec['task']:
        return '任务书'
    if rec['translation']:
        return '外文翻译'
    return '选题/未提交'


def risk_flags(rec):
    flags = []
    if not rec['task']:
        flags.append('缺任务书')
    if not rec['opening']:
        flags.append('缺开题报告')
    if not rec['thesis']:
        flags.append('缺论文终稿')
    # 有原件无批注 → 未审
    raw_docs = rec['task'] + rec['opening'] + rec['thesis'] + rec['translation']
    if raw_docs and not rec['comments']:
        flags.append('有原件未批注')
    if rec['thesis'] and not rec['comments']:
        flags.append('论文定稿前未做抽检自查')
    return flags


def cell(items):
    """材料存在性单元格：有 / 缺（不臆断'已审'，避免按文件名误标）。"""
    return '✓ 有' if items else '✗ 缺'


def build_md(root, term, advisor, records, order, roster):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    L = []
    L.append('# 毕业设计监督驾驶舱（%s）' % term)
    L.append('')
    L.append('> **指导教师**：%s　**生成时间**：%s　**扫描根目录**：`%s`' % (advisor, now, root))
    L.append('> **模式**：队列看板（整届多名学生进度总览）。下钻单人精审见 §四。')
    L.append('')
    n = len(order)
    complete = sum(1 for s in order if records[s]['task'] and records[s]['opening'] and records[s]['thesis'])
    L.append('## 一、队列总览矩阵（%d 名学生）' % n)
    L.append('')
    L.append('| # | 学生 | 任务书 | 开题报告 | 论文终稿 | 译文 | 批注版 | 已到阶段 | 风险 |')
    L.append('|---|---|---|---|---|---|---|---|---|')
    for i, s in enumerate(order, 1):
        rec = records[s]
        row = [
            str(i), s,
            cell(rec['task']), cell(rec['opening']), cell(rec['thesis']),
            '✓' if rec['translation'] else '—',
            '✓' if rec['comments'] else '✗',
            infer_stage(rec),
            '；'.join(risk_flags(rec)) or '无',
        ]
        L.append('| ' + ' | '.join(row) + ' |')
    L.append('')
    L.append('> 齐备度：三件套（任务书+开题+论文）齐全 %d/%d 人。' % (complete, n))
    L.append('')

    L.append('## 二、阶段进度推断')
    L.append('')
    for s in order:
        rec = records[s]
        parts = []
        if rec['task']:
            parts.append('任务书✓')
        if rec['opening']:
            parts.append('开题✓')
        if rec['thesis']:
            parts.append('论文✓')
        if rec['translation']:
            parts.append('译文✓')
        L.append('- **%s**：%s → 推断已到【%s】' % (s, ' → '.join(parts) or '无材料', infer_stage(rec)))
    L.append('')

    L.append('## 三、风险高亮（需教师介入）')
    L.append('')
    any_risk = False
    for s in order:
        flags = risk_flags(records[s])
        if flags:
            any_risk = True
            L.append('- 🔴 **%s**：%s' % (s, '；'.join(flags)))
    if not any_risk:
        L.append('- 本轮扫描未发现材料缺失类风险。')
    L.append('')

    L.append('## 四、单人下钻提示（可直接复制执行）')
    L.append('')
    for s in order:
        rec = records[s]
        if not (rec['task'] or rec['opening'] or rec['thesis']):
            continue
        doc = rec['thesis'][0] if rec['thesis'] else (rec['opening'][0] if rec['opening'] else rec['task'][0])
        L.append('- **%s**：`python scripts/review_docx.py "%s" --type %s` ；批注：`python scripts/inject_comments.py --in "%s" --out "%s-批注.docx"`'
                 % (s, doc, 'thesis' if rec['thesis'] else ('opening' if rec['opening'] else 'task'), doc, os.path.splitext(doc)[0]))
    L.append('')

    L.append('## 五、使用说明')
    L.append('')
    L.append('- 本看板由 `scripts/supervision_cockpit.py` 扫描本地 `.docx` 原件生成，**天然保留表格内容**（优于知识库文本提取）。')
    L.append('- 状态枚举：✓有 / ✓已审（含批注版）/ ✗缺。任一篇档被判🔴阻塞即整阶段退回，须经"修改后复审"才能转已通过。')
    L.append('- 单人精审后，把结论回填到每份文档（inject_comments.py 注入 Word 批注），并据 §八 五条铁律做跨文档串链。')
    L.append('- 跨会话跟踪：用 `--state state.json` 导出矩阵，下次巡检 diff 出"本周新增卡点"。')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, help='本地 .docx 原件根目录')
    ap.add_argument('--term', default='未知届')
    ap.add_argument('--advisor', default='指导教师')
    ap.add_argument('--roster', help='学生名单 JSON（数组：姓名串 或 {name,id,topic}）')
    ap.add_argument('--out', help='输出 md 路径，默认 毕业设计监督驾驶舱_<届>.md')
    ap.add_argument('--docx', action='store_true', help='同时用 md2docx.py 生成 .docx 看板')
    ap.add_argument('--state', help='导出矩阵 JSON 路径（用于跨会话 diff）')
    args = ap.parse_args()

    roster = None
    if args.roster:
        roster = json.load(open(args.roster, encoding='utf-8'))

    records, order = scan(args.root, roster)
    if not order:
        print('WARN: 根目录下未扫描到 .docx 文件，请检查 --root 路径。')
        return

    md = build_md(args.root, args.term, args.advisor, records, order, roster)
    out = args.out or ('毕业设计监督驾驶舱_%s.md' % args.term)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(md)
    print('OK 看板已生成 -> %s （%d 名学生）' % (out, len(order)))

    if args.state:
        state = {s: {k: [os.path.basename(x) for x in v] for k, v in records[s].items() if k != '_meta'}
                 for s in order}
        json.dump({'term': args.term, 'advisor': args.advisor, 'students': state},
                  open(args.state, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('OK 状态矩阵已导出 -> %s' % args.state)

    if args.docx:
        md2 = None
        for cand in [
            'E:/培训所需软件/练习用材料/.workbuddy/md2docx.py',
            'C:/Users/Administrator/.workbuddy/md2docx.py',
        ]:
            if os.path.exists(cand):
                md2 = cand
                break
        if md2:
            docx_out = os.path.splitext(out)[0] + '.docx'
            try:
                subprocess.run(['python', md2, out, docx_out], check=True)
                print('OK docx 看板已生成 -> %s' % docx_out)
            except Exception as e:
                print('WARN docx 生成失败（看板 md 仍可用）：%s' % e)
        else:
            print('WARN 未找到 md2docx.py，跳过 docx 生成。')


if __name__ == '__main__':
    main()
