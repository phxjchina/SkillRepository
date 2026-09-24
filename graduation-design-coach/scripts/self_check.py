#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""self_check.py — 毕业设计陪跑教练·阶段自检
读取 .docx 原件（含表格），按学生自检清单输出 必改/建议 两级问题。
用法:
  python self_check.py <文档.docx> --type task|opening|thesis [--expected-title "题目"] [--expected-refs 10]
"""
import argparse, os, re, sys
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_paragraphs(xml_bytes):
    """递归收集所有 w:p（含表格内），返回 (full_text, [段落文本])"""
    root = ET.fromstring(xml_bytes)
    body = root.find(f"{W}body")
    if body is None:
        return "", []
    paras, full = [], []
    for p in body.iter(f"{W}p"):
        line = "".join(t.text or "" for t in p.iter(f"{W}t"))
        paras.append(line)
        full.append(line)
    return "\n".join(full), paras


def read_docx(path):
    import zipfile
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    return extract_paragraphs(xml)


def sect(text, start_pat, end_pat):
    m1 = re.search(start_pat, text)
    if not m1:
        return ""
    m2 = re.search(end_pat, text[m1.end():])
    return text[m1.end():m1.end() + m2.start()] if m2 else text[m1.end():]


def refs_of(text):
    """参考文献条目：取最后一处“参考文献”标题（跳过说明页/目录里的匹配）。
    优先行首 [n]/［n］；若为 Word 自动编号（正文无编号文本），按连续非空行近似计数。"""
    ms = list(re.finditer(r"参\s*考\s*文\s*献", text))
    if not ms:
        return []
    tail = text[ms[-1].end():]
    for stop in ("致　谢", "致谢", "附　录", "附录"):
        i = tail.find(stop)
        if i >= 0:
            tail = tail[:i]
    items = re.findall(r"^\s*[\[［](\d+)[\]］]\s*(.+)$", tail, re.M)
    if items:
        return items
    entries, blank = [], 0
    for line in tail.splitlines():
        s = line.strip()
        if s:
            blank = 0
            if len(s) > 8:
                entries.append(("", s))
        else:
            blank += 1
            if blank >= 3 and entries:
                break
    return entries


def check(path, typ, expected_title=None, expected_refs=None, stage="final"):
    """stage: final(终稿/默认) | mid(中期稿) | draft(初稿)。
    中期/初稿阶段，论文结构项（摘要/目录/致谢等）缺失属阶段正常，降为“建议”。"""
    text, paras = read_docx(path)
    problems = []  # (位置, 问题, 级别, 修改方向)
    P = problems.append
    soft = stage in ("draft", "mid")  # 阶段感知
    def LV(base):
        return "建议" if soft else base

    # 通用：题目一致性
    if expected_title:
        clean = re.sub(r"\s+", "", text)
        if re.sub(r"\s+", "", expected_title) not in clean:
            P(("全文", "未找到期望题目《%s》——题目可能与任务书/封面不一致（铁律①）" % expected_title, "必改",
               "逐字复制题目到封面与正文标题，别手敲"))

    if typ == "task":
        if "系统说明书" in text:
            P(("成果形式", "出现禁用词“系统说明书”", "必改", "改为“XX系统一套，毕业设计论文一份”"))
        for m in re.finditer(r"(计算机\w*?\d*班)", text):
            P(("专业班级", "班级含“班”字：%s" % m.group(1), "必改", "按届口径写如“计算机科学2104”"))
        for kw, hint in [("课题目标", "课题目标及要求"), ("主要内容", "主要内容及成果形式"),
                         ("进度安排", "进度安排(6阶段)"), ("参考文献", "建议参考文献")]:
            if kw not in text:
                P(("结构", "缺少任务书必备块：%s" % hint, "必改", "按附件3模板补齐"))
        refs = refs_of(text)
        if len(refs) < 5:
            P(("参考文献", "仅 %d 篇(<5)" % len(refs), "必改", "补至≥5篇，近3年为主，≥1篇外文"))
        for i, (no, body) in enumerate(refs):
            label = "参考文献[%s]" % no if no else "参考文献第%d条" % (i + 1)
            authors = re.split(r"[,，]", body.split(".")[0])
            if len([a for a in authors if a.strip()]) > 3 and ",等" not in body and "，等" not in body and ", etc" not in body:
                P((label, "作者>3位未用“等”省略", "必改", "列前3位后加“,等”"))
            if re.search(r"(\d+)\s*:\s*(\d+)-\1-\2", body) or re.search(r"(\w+)-\1\b", body):
                P((label, "页码疑似重复著录", "必改", "改为 卷(期): 起页 或单页码"))

    elif typ == "opening":
        secs = [("1", r"研究目的及意义", r"国内外研究现状"),
                ("2", r"国内外研究现状", r"拟采用的研究手段|研究手段"),
                ("3", r"拟采用的研究手段|要研究或解决的问题", r"工作进度安排"),
                ("4", r"工作进度安排", r"参\s*考\s*文\s*献")]
        lens = {}
        for no, s, e in secs:
            lens[no] = len(sect(text, s, e)) if re.search(s, text) else 0
        for no, s, _ in secs:
            if not re.search(s, text):
                P(("章节", "缺少固定章节：%s" % s, "必改", "按附件5固定章节补齐"))
        if lens.get("3") and (lens.get("1", 0) + lens.get("2", 0)):
            if lens["3"] <= lens["1"] + lens["2"]:
                P(("第3部分", "篇幅(%d字)未超过第1+2部分之和(%d字)" % (lens["3"], lens["1"] + lens["2"]),
                   "必改", "第3部分写到全文一半以上：内容/问题/手段写实"))
        total = len(re.sub(r"\s", "", text))
        if total < 2000:
            P(("全文", "约 %d 字(<2000)" % total, "必改", "扩写至≥2000字，重点第3部分"))
        if re.search(r"20\s{2,}年\s{2,}月\s{2,}日", text):
            P(("封面", "完成时间疑似留空模板", "必改", "填阿拉伯数字日期"))
        for bad in ["研究目的应该出现在这里", "请在此填写", "此处填写"]:
            if bad in text:
                P(("正文", "残留模板提示文字“%s”" % bad, "必改", "删净所有模板提示"))
        refs = refs_of(text)
        n = len(refs)
        minr = expected_refs or 10
        if n < minr:
            P(("参考文献", "仅 %d 篇(<%d)" % (n, minr), "必改", "补至≥10篇，≥2篇外文，含任务书文献"))
        nums = [int(no) for no, _ in refs if no]
        if len(nums) != len(set(nums)):
            P(("参考文献", "编号重复（可能同一文献列两次）", "必改", "去重后重新编号"))
        if "客服" in text:
            P(("正文", "“客服”疑为“克服”错别字", "必改", "通读校对"))
        if not re.search(r"工作进度安排", text):
            P(("第4部分", "缺“工作进度安排”", "必改", "与任务书6阶段逐条一致"))

    elif typ == "thesis":
        # 标题常带空格排版（“摘  要”“目  录”“致    谢”），必须用空格容忍正则，否则大面积误报
        has = lambda pat: re.search(pat, text)
        stage_note = "（中期/初稿阶段正常，终稿前补齐）" if soft else ""
        if not has(r"摘\s*要"):
            P(("结构", "缺 中文摘要%s%s" % ("含“摘 要”间隔排版均计" if not soft else "", stage_note), LV("必改"), "按学校论文结构补齐"))
        if not has(r"关\s*键\s*词"):
            P(("结构", "缺 关键词%s" % stage_note, LV("必改"), "“关键词：”3-5个，分号分隔"))
        if not has(r"(?i)abstract"):
            P(("结构", "缺 英文摘要（Abstract）%s" % stage_note, LV("必改"), "另起一页，Times New Roman"))
        if not has(r"目\s*录"):
            P(("结构", "缺 目录%s" % stage_note, LV("必改"), "自动生成目录并与正文核对"))
        if not has(r"致\s*谢"):
            P(("结构", "缺 致谢%s" % stage_note, LV("必改"), "末尾学生署名+含指导教师姓名"))
        refs = refs_of(text)
        n = len(refs)
        minr = expected_refs or 15
        if n < minr:
            P(("参考文献", "仅 %d 篇(<%d)%s" % (n, minr, "（Word自动编号文献会漏计，请人工复核）" if n == 0 else ""), LV("必改"),
               "补至≥15篇，≥2篇外文，含开题文献"))
        # 只统计图题（行首“图x-y …”）；并排除图表目录行（点引线/行尾页码），否则目录+正文图题=假重复
        def caption_lines(pat):
            out = []
            for l in text.splitlines():
                if re.match(r"\s*" + pat, l):
                    s = l.strip()
                    if not re.search(r"(\.{2,}\s*\d+\s*|\s\d{1,3}\s*)$", s):
                        out.append(l)
            return out
        figs = [re.match(r"\s*图\s*(\d+)[-－]\s*(\d+)", l).groups() for l in caption_lines(r"图\s*\d+[-－]\s*\d+")]
        dup = [f for f in set(figs) if figs.count(f) > 1]
        if dup:
            P(("图表", "图号重复：%s" % ", ".join("图%s-%s" % f for f in sorted(dup)[:5]), "必改", "按章编排，同章内图号唯一"))
        tabs = [re.match(r"\s*表\s*(\d+)[-－]\s*(\d+)", l).groups() for l in caption_lines(r"表\s*\d+[-－]\s*\d+")]
        dupt = [t for t in set(tabs) if tabs.count(t) > 1]
        if dupt:
            P(("表格", "表号重复：%s" % ", ".join("表%s-%s" % t for t in sorted(dupt)[:5]), "必改", "按章编排，三线表"))
        if "心得" in text or "收获" in text:
            P(("摘要/结论", "出现“心得/收获”字样", "建议", "结论写工作与结果，不写体会"))
        en = re.findall(r"[A-Za-z]{4,}", text)
        for term in ("OpenGL", "opengl"):
            if term == "OpenGL" and "OpenglGL" in text:
                P(("术语", "英文拼写不一致 OpenglGL", "必改", "统一为 OpenGL"))
        P(("工作量", "“本人设计与实现≥全文2/3”无法自动判定", "建议",
           "自查：第4-5章实现内容是否覆盖任务书主要功能，概念综述是否挤占篇幅"))

    elif typ == "translation":
        # 外文翻译：不是论文，别用论文结构检查（曾误报“缺英文摘要/目录/致谢”）
        total = len(re.sub(r"\s", "", text))
        if total < 3000:
            P(("全文", "约 %d 字(<3000)" % total, "必改", "外文翻译正文一般要求≥3000汉字"))
        if not re.search(r"(19|20)\d{2}", text[:2000]):
            P(("出处", "未见原文年份信息", "建议", "文首注明原文标题/作者/出处/年份，便于教师核对"))
        for bad in ["请在此填写", "此处填写", "XXX"]:
            if bad in text:
                P(("正文", "残留模板提示文字“%s”" % bad, "必改", "删净模板提示"))
        if re.search(r"(机翻|机器翻译|google翻译|百度翻译)", text, re.I):
            P(("正文", "出现“机器翻译”等字样", "必改", "通读润色，逐句改写为通顺中文"))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("doc")
    ap.add_argument("--type", required=True, choices=["task", "opening", "thesis", "translation"])
    ap.add_argument("--stage", default="final", choices=["final", "mid", "draft"],
                    help="终稿final(默认)/中期mid/初稿draft——中期与初稿的结构缺项降为建议")
    ap.add_argument("--expected-title", default=None)
    ap.add_argument("--expected-refs", type=int, default=None)
    a = ap.parse_args()
    if not os.path.exists(a.doc):
        print("文件不存在：%s" % a.doc)
        sys.exit(1)
    probs = check(a.doc, a.type, a.expected_title, a.expected_refs, a.stage)
    name = {"task": "任务书", "opening": "开题报告", "thesis": "毕业论文", "translation": "外文翻译"}[a.type]
    print("### 《%s》学生自检（%s）\n" % (os.path.basename(a.doc), name))
    print("总体：%s" % ("✅ 自检通过，可请教师审" if not probs else "⚠️ 有 %d 项待处理（必改 %d）" % (
        len(probs), sum(1 for p in probs if p[2] == "必改"))))
    if probs:
        print("\n| 位置 | 问题 | 级别 | 修改方向 |")
        print("|---|---|---|---|")
        for pos, q, lv, fix in probs:
            print("| %s | %s | %s | %s |" % (pos, q, lv, fix))
    print("\n> 只辅导不代写：按“修改方向”自己改，改完再跑一遍自检。")


if __name__ == "__main__":
    main()
