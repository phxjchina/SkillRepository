# -*- coding: utf-8 -*-
"""
论文(.docx)结构初筛 —— 毕业设计指导智能体 配套脚本
纯标准库（zipfile + xml），离线可用，不依赖 python-docx。

检查项（来自实跑发现的真实雷区）：
  1. 中文摘要是否被英文占据 / 摘要缺失
  2. 关键词是否缺失
  3. 是否有独立英文摘要（Abstract / Key words）
  4. 图号是否重复编号
  5. 章节编号是否连续（跳号 / 章号错）

用法：
  python review_thesis.py <论文.docx> [--title "期望题目"]
"""
import re, sys, zipfile, xml.etree.ElementTree as ET

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def read_docx(path):
    z = zipfile.ZipFile(path)
    xml = z.read('word/document.xml').decode('utf-8')
    # 拆段落
    paras = re.findall(r'<w:p[ >].*?</w:p>', xml, re.S)
    out = []
    for p in paras:
        texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.S)
        line = ''.join(texts)
        line = line.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        out.append(line)
    return out

def chinese_ratio(s):
    if not s:
        return 0.0
    cn = len(re.findall(r'[一-鿿]', s))
    return cn / max(1, len(s))

def find_block(paras, keyword):
    """返回 keyword 所在段之后的非空内容拼接（最多 8 段）"""
    for i, p in enumerate(paras):
        if keyword in p:
            buf = []
            for q in paras[i+1:i+9]:
                if q.strip():
                    buf.append(q.strip())
            return ' '.join(buf)
    return ''

def check(path, expected_title=None):
    paras = read_docx(path)
    full = '\n'.join(paras)
    issues = []

    # 1+2 摘要 / 关键词
    abs_block = find_block(paras, '摘要')
    if not abs_block:
        issues.append(('严重', '未找到中文摘要段落', '论文审核 C.2'))
    else:
        if chinese_ratio(abs_block) < 0.25:
            issues.append(('严重', '中文摘要疑似被英文占据或为空（中文占比 %.0f%%）' % (chinese_ratio(abs_block)*100), '论文审核 C.2'))
        if '关键词' not in abs_block and 'key' not in abs_block.lower():
            issues.append(('严重', '摘要后未见"关键词："', '论文审核 C.5'))

    # 3 英文摘要
    if 'abstract' not in full.lower() and 'key words' not in full.lower() and 'keywords' not in full.lower():
        issues.append(('严重', '未检出独立英文摘要（Abstract / Key words）', '论文审核 C.7'))

    # 4 图号重复
    figs = re.findall(r'图\s*(\d+)\s*[-–]?\s*(\d+)?', full)
    fig_nums = []
    for a, b in figs:
        fig_nums.append(a if not b else '%s-%s' % (a, b))
    dups = set([x for x in fig_nums if fig_nums.count(x) > 1])
    if dups:
        issues.append(('中', '图号重复编号：%s' % '、'.join(sorted(dups)), '论文审核 C.39'))

    # 5 章节编号连续性（顶层章 1..n）
    chaps = []
    for p in paras:
        m = re.match(r'^\s*(\d+)\s+[\u4e00-\u9fff一-鿿A-Za-z]', p)
        if m:
            chaps.append(int(m.group(1)))
    chaps = sorted(set(chaps))
    if chaps:
        missing = [c for c in range(1, max(chaps)+1) if c not in chaps]
        if missing:
            issues.append(('中', '顶层章号不连续，缺失：%s' % '、'.join(map(str, missing)), '论文审核 C.9'))

    # 题目一致性（可选）
    if expected_title:
        cover_hit = expected_title in full
        issues.append(('建议' if cover_hit else '严重',
                       ('封面/正文题目与期望一致' if cover_hit else '正文未检出期望题目：「%s」' % expected_title),
                       '铁律①'))

    return issues, len(paras)

def main():
    if len(sys.argv) < 2:
        print('usage: python review_thesis.py <论文.docx> [--title 期望题目]')
        sys.exit(1)
    path = sys.argv[1]
    expected = None
    if '--title' in sys.argv:
        expected = sys.argv[sys.argv.index('--title')+1]
    issues, n = check(path, expected)
    print('=== 论文结构初筛：%s ===' % path)
    print('段落数：%d' % n)
    if not issues:
        print('✅ 未检出结构性严重问题')
    else:
        for lvl, msg, ref in issues:
            print('[%s] %s  （%s）' % (lvl, msg, ref))
    print('\n说明：本脚本仅做结构初筛，内容质量仍由 LLM 按审核清单逐条审查。')

if __name__ == '__main__':
    main()
