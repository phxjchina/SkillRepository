#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inject_comments.py — 向 .docx 注入真实 Word 批注（comments 气泡）

用途：毕业设计指导智能体在拿到学生原文档后，把每条审查意见作为 Word 批注
锚定到对应段落，生成「（原文档名）-批注.docx」。
学生/教师用 Word 打开即可在右侧看到批注气泡，等价于教师在原件上批改。

关键特性（v2）：
  * 若原文档**已含批注**（如彭老师批注过的"修改终稿版"），自动【保留原批注】
    并以 max(id)+1 接续追加新批注，绝不覆盖。
  * 若原文档无批注，按常规新建 comments.xml。
  * 全文档 media / 排版 / 样式原样保留（重写 zip 时包含所有 part）。

依赖：仅 lxml（本机托管 Python 已带）。不依赖 python-docx。

用法：
  python inject_comments.py --in 原文档.docx --out 批注文档.docx [--rules rules.json]
  rules.json: JSON 数组，元素为 [锚点关键词, 批注文本]，按关键词首次命中的段落挂批注。
  不传 --rules 时使用脚本内 DEFAULT_RULES（针对巩晶伟论文终稿）。
"""

import sys
import json
import zipfile
import datetime
import argparse
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
X = 'http://www.w3.org/XML/1998/namespace'
REL_COMMENTS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments'


def q(tag):
    return '{%s}%s' % (W, tag)


def para_text(p):
    return ''.join(t.text or '' for t in p.iter(q('t')))


DEFAULT_RULES = [
    ("摘要",
     "【🔴 格式红线】中文摘要缺失\n"
     "封面后「摘要：」之下直接是英文标题，无中文摘要正文，且关键词、独立英文摘要页全缺。\n"
     "建议：①补写中文摘要（约 300 字，含目的/方法/结果/结论四要素）；②补 3–5 个中文关键词；"
     "③新增独立英文摘要页（Abstract + 英文关键词），置于中文摘要之后。"),
    ("4.3.4",
     "【🔴 格式红线】章节编号严重错乱\n"
     "①4.2.3 之后出现「4.3.4 通过软件控制门和齿轮」（应为 4.2.4），层级错位；"
     "②4.2.4 之后直接跳「4.2.6 细化门式电动阀和齿轮电动阀」（缺 4.2.5）；③第 5 章测试章在目录误编为「4」。\n"
     "建议：全文统一重新编号 4.2.1→4.2.8 连续；第 5 章固定为「5 飞机起落架仿真控制系统功能测试」；"
     "同步修正正文与目录，用 Word 自动生成目录刷新页码。"),
    ("如图4-1",
     "【🔴 格式红线】图 4-1 重复编号\n"
     "4.1 总体设计架构图标「图 4-1 飞机起落架仿真控制系统总体设计架构」，"
     "4.2.1 起落架系统图又标「图 4-1 起落架系统」，同一章内两图同号。\n"
     "建议：后者改「图 4-2 起落架系统」，其后续图号全部顺延；"
     "全章图号重排后核对正文引用是否一致。"),
    ("OpenglGL",
     "【🟠 严重】英文/专业术语拼写错误\n"
     "①「OpenglGL」应为 OpenGL（出现在目录 2.2、正文 2.2 标题及图题）；"
     "②电动阀变量名「Value_door_op…」应为 Valve_；③「顶带着色器」应为「顶点着色器」。\n"
     "建议：全文检索并修正 OpenGL、Valve_、顶点着色器；外文刊名与专业词统一大小写"
     "（如 Event-B、Rodin、ProB、Assimp、Qt）。"),
    ("Value_door",
     "【🟠 严重】电动阀变量名拼写错误\n"
     "文中「Value_door_open / Value_door_close」等应为 Valve_（valve=阀），属于变量命名拼写错误，"
     "在形式化模型与仿真实现中前后必须一致，否则影响代码可追溯性。\n"
     "建议：全文检索 Value_ 替换为 Valve_（保留语义），并与第 4 章状态机、事件命名统一。"),
    ("表2-4",
     "【🟡 建议】图表编号跳跃\n"
     "表 2-4（OpenGL 通道表）之前无表 2-1～2-3，编号跳跃；部分图表编号不连续。\n"
     "建议：核查全文章节内图表编号连续性，补齐或顺延，确保「图 N-M / 表 N-M」按章连续无缺号。"),
    ("Dana Dghaym",
     "【🟡 建议】参考文献格式不规范\n"
     "外文文献（Dana Dghaym / Lukas Ladenberger / Richard Banach 等）刊名未斜体；"
     "作者超过 3 人未用「et al.」。\n"
     "建议：按 GB/T 7714—2015，外文刊名用斜体，作者 >3 人用「et al.」，全文统一上标引用 [n] 格式。"),
    ("功能测试",
     "【🟡 建议】第 5、6 章内容偏薄\n"
     "第 5 章「测试结果分析」与第 6 章「总结」内容偏薄：测试结果仅截图展示、缺量化数据"
     "（如模型证明义务通过率、仿真响应时延）；总结缺创新点凝练。\n"
     "建议：5.3 补充形式化证明义务通过数量/比例、仿真交互正确性判据；"
     "6.1 凝练 2–3 条创新点（如 Event-B 精化 + 三维可交互仿真闭环验证）。"),
]


def inject(in_path, out_path, rules, author='毕业设计指导智能体', initials='AI'):
    zin = zipfile.ZipFile(in_path, 'r')
    data = {n: zin.read(n) for n in zin.namelist()}
    zin.close()

    dt = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    doc_tree = etree.fromstring(data['word/document.xml'])
    paras = list(doc_tree.iter(q('p')))

    # ---- 解析已有批注，确定新批注起始 id（追加模式）----
    existing_ids = []
    if 'word/comments.xml' in data:
        eroot = etree.fromstring(data['word/comments.xml'])
        croot = eroot
        for c in eroot.findall(q('comment')):
            cidv = c.get(q('id'))
            if cidv and cidv.isdigit():
                existing_ids.append(int(cidv))
        print('INFO: 原文档已有 %d 条批注，将以 id=%d 起追加' %
              (len(existing_ids), (max(existing_ids) + 1) if existing_ids else 0))
    else:
        croot = etree.Element(q('comments'), nsmap={'w': W})
    next_id = (max(existing_ids) + 1) if existing_ids else 0

    comments = []
    cid = next_id
    for kw, text in rules:
        target = None
        for p in paras:
            if kw in para_text(p):
                target = p
                break
        if target is None:
            print('WARN: 锚点关键词未命中，跳过 ->', repr(kw))
            continue
        start = etree.Element(q('commentRangeStart'), {q('id'): str(cid)})
        ref = etree.Element(q('r'))
        cr = etree.SubElement(ref, q('commentReference'))
        cr.set(q('id'), str(cid))
        end = etree.Element(q('commentRangeEnd'), {q('id'): str(cid)})
        first_r = target.find(q('r'))
        if first_r is not None:
            idx = list(target).index(first_r)
            target.insert(idx, start)
            target.insert(idx + 1, ref)
        else:
            target.append(start)
            target.append(ref)
        target.append(end)
        comments.append((cid, text, author, initials))
        cid += 1

    data['word/document.xml'] = etree.tostring(
        doc_tree, xml_declaration=True, encoding='UTF-8', standalone=True)

    # ---- 追加新批注节点到 comments.xml ----
    for cid, text, a, ini in comments:
        c = etree.SubElement(croot, q('comment'))
        c.set(q('id'), str(cid))
        c.set(q('author'), a)
        c.set(q('date'), dt)
        c.set(q('initials'), ini)
        for line in text.split('\n'):
            cp = etree.SubElement(c, q('p'))
            cr = etree.SubElement(cp, q('r'))
            ct = etree.SubElement(cr, q('t'))
            ct.set('{%s}space' % X, 'preserve')
            ct.text = line
    data['word/comments.xml'] = etree.tostring(
        croot, xml_declaration=True, encoding='UTF-8', standalone=True)

    # ---- rels：已有 comments 关系则复用，否则新建 ----
    rels_tree = etree.fromstring(data['word/_rels/document.xml.rels'])
    has_comments_rel = any(REL_COMMENTS in (r.get('Type') or '')
                           for r in rels_tree)
    if not has_comments_rel:
        existing = {r.get('Id') for r in rels_tree}
        rid = 'rIdGdComments'
        while rid in existing:
            rid += 'X'
        rel = etree.SubElement(rels_tree, '{%s}Relationship' % PKG)
        rel.set('Id', rid)
        rel.set('Type', REL_COMMENTS)
        rel.set('Target', 'comments.xml')
        print('INFO: 新建 comments 关系 %s' % rid)
    else:
        print('INFO: 复用已有 comments 关系')
    data['word/_rels/document.xml.rels'] = etree.tostring(
        rels_tree, xml_declaration=True, encoding='UTF-8', standalone=True)

    # ---- Content_Types：已有 Override 则跳过 ----
    ct_tree = etree.fromstring(data['[Content_Types].xml'])
    has = any(ov.get('PartName') == '/word/comments.xml'
              for ov in ct_tree.findall('{%s}Override' % CT))
    if not has:
        ov = etree.SubElement(ct_tree, '{%s}Override' % CT)
        ov.set('PartName', '/word/comments.xml')
        ov.set('ContentType',
               'application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml')
    data['[Content_Types].xml'] = etree.tostring(
        ct_tree, xml_declaration=True, encoding='UTF-8', standalone=True)

    # ---- 重写 zip（保留全部 media/样式）----
    zout = zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED)
    for n in data:
        if n == 'word/comments.xml':
            continue
        zout.writestr(n, data[n])
    zout.writestr('word/comments.xml', data['word/comments.xml'])
    zout.close()
    print('OK 新增注入 %d 条批注（原 %d 条保留）-> %s' %
          (len(comments), len(existing_ids), out_path))
    return len(comments), len(existing_ids)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--rules', help='JSON 数组 [[关键词, 批注文本], ...]')
    ap.add_argument('--author', default='毕业设计指导智能体')
    ap.add_argument('--initials', default='AI')
    args = ap.parse_args()
    rules = json.load(open(args.rules, encoding='utf-8')) if args.rules else DEFAULT_RULES
    inject(args.inp, args.out, rules, args.author, args.initials)
