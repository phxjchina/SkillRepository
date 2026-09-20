#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
毕业设计文档离线结构审查脚本（纯标准库，无需 python-docx）。

对 .docx 做结构层初筛：章节齐全性、字数、参考文献数量、题目一致性、模板占位符（未填项）。
字体/手写签名等需肉眼或 Word 复核，本脚本不判定。

用法:
    python review_docx.py <文档.docx> --type task|opening|thesis \
        [--expected-title "题目"] [--expected-refs 10] [--min-chars 2000]

输出: Markdown 审查草稿，可直接作为 SKILL.md §七 的初筛输入。
"""
import argparse
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

# 各文档类型期望出现的章节关键词（任一缺失即提示）
EXPECT_SECTIONS = {
    "task": ["题目", "学生姓名", "学号", "专业", "班级", "课题目标", "主要内容",
             "进度安排", "建议参考文献", "指导教师签名", "教研室主任签名", "学生签名"],
    "opening": ["研究目的及意义", "国内外研究现状", "本课题要研究", "工作进度安排",
                "参考文献", "指导教师意见", "教研室意见"],
    "thesis": ["摘要", "Abstract", "目录", "参考文献", "结论", "致谢"],
}

DEFAULT_REFS = {"task": 5, "opening": 10, "thesis": 15}
DEFAULT_MINCHARS = {"task": 300, "opening": 2000, "thesis": 8000}


def para_text(p):
    """提取单个段落（w:p）的全部文本。"""
    return "".join(t.text or "" for t in p.iter(f"{W}t"))


def _walk(elem, out):
    """递归收集元素内所有段落文本（含表格 w:tbl / 单元格 w:tc / 嵌套表格），按文档顺序。"""
    for child in elem:
        if child.tag == f"{W}p":
            out.append(para_text(child))
        else:
            _walk(child, out)


def extract_paragraphs(xml_bytes):
    """返回 (full_text, [段落文本列表])。

    关键：同时收集正文段落与【表格单元格】内的段落文本。
    毕业设计模板大量用表格承载正文（开题报告正文、进度表、任务书表头），
    若只看 w:p 会丢失表格内容，造成"字数极少/章节全缺"的假阴性。
    """
    root = ET.fromstring(xml_bytes)
    body = root.find(f"{W}body")
    if body is None:
        return "", []
    paras = []
    _walk(body, paras)
    return "\n".join(paras), paras


def count_cjk(text):
    return len(re.findall(r"[一-鿿]", text))


def count_references(full_text):
    """尽量统计参考文献条数：取最后一个'参考文献'之后的内容，按年份+文献类型标记计数。"""
    idx = full_text.rfind("参考文献")
    if idx == -1:
        return 0, []
    bib = full_text[idx:]
    # 条目特征：含 4 位年份 且 含文献类型标记 [J][M][D][P][C][R][N][S][G] 或 "期刊/学位论文/专利/报告"
    pat = re.compile(
        r"(?:\[[A-Z]\])|(?:期刊|学位论文|专利|报告|标准|报纸|电子公告)", re.IGNORECASE)
    year_pat = re.compile(r"(?:19|20)\d{2}")
    lines = [l.strip() for l in bib.splitlines() if l.strip()]
    entries = []
    for ln in lines[1:]:  # 跳过"参考文献"标题行
        if year_pat.search(ln) and pat.search(ln):
            entries.append(ln[:60])
    # 交叉校验：全文 [1]..[n] 引用标记数量
    markers = len(re.findall(r"\[\d+\]", full_text))
    return max(len(entries), 0), entries[:8]


def detect_placeholders(full_text):
    """检测未填模板占位符：未填日期、空字段。"""
    flags = []
    if re.search(r"年\s{2,}月\s{2,}日", full_text):
        flags.append("存在未填写的'年  月  日'日期占位符（签名/日期未填）")
    if "学生姓名：" in full_text and re.search(r"学生姓名：\s*$", full_text):
        flags.append("'学生姓名'字段疑似为空")
    if re.search(r"指导教师签名[：:]\s*$", full_text):
        flags.append("'指导教师签名'处疑似未签名")
    return flags


def review(path, dtype, expected_title=None, expected_refs=None, min_chars=None):
    if not os.path.isfile(path):
        print(f"错误：文件不存在 {path}", file=sys.stderr)
        sys.exit(2)
    if not path.lower().endswith(".docx"):
        print("错误：仅支持 .docx（非 .doc）", file=sys.stderr)
        sys.exit(2)
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml")
    except Exception as e:
        print(f"错误：无法读取 docx（{e}）", file=sys.stderr)
        sys.exit(2)

    full, paras = extract_paragraphs(xml)
    cjk = count_cjk(full)
    total = len(re.sub(r"\s", "", full))
    refs, samples = count_references(full)
    placeholders = detect_placeholders(full)

    exp_refs = expected_refs or DEFAULT_REFS.get(dtype, 10)
    exp_min = min_chars if min_chars is not None else DEFAULT_MINCHARS.get(dtype, 1000)
    sections = EXPECT_SECTIONS.get(dtype, [])

    print(f"### 《{os.path.basename(path)}》结构初筛（类型={dtype}）\n")
    print(f"- 字数（中文）：{cjk}　总字符（去空白）：{total}　参考阈值：≥{exp_min}")
    print(f"- 参考文献约：{refs} 条　参考阈值：≥{exp_refs}\n")

    print("| 维度 | 结果 | 说明 |")
    print("|---|---|---|")

    # 1. 章节齐全
    missing = [s for s in sections if s not in full]
    status = "✅" if not missing else "⚠️"
    note = "关键章节齐全" if not missing else f"缺失疑似：{', '.join(missing)}"
    print(f"| 关键章节齐全性 | {status} | {note} |")

    # 2. 字数
    status = "✅" if cjk >= exp_min else ("⚠️" if cjk >= exp_min * 0.6 else "⛔")
    print(f"| 字数达标 | {status} | 实际 {cjk} / 要求 ≥{exp_min} |")

    # 3. 参考文献
    status = "✅" if refs >= exp_refs else ("⚠️" if refs >= exp_refs * 0.6 else "⛔")
    extra = f"（样例：{'; '.join(samples)}）" if samples else ""
    print(f"| 参考文献数量 | {status} | 实际约 {refs} / 要求 ≥{exp_refs} {extra}|")

    # 4. 题目一致性
    if expected_title:
        norm = lambda s: re.sub(r"\s", "", s)
        ok = norm(expected_title) in norm(full)
        print(f"| 题目一致性 | {'✅' if ok else '⛔'} | "
              f"期望含「{expected_title}」→ {'一致' if ok else '文档中未找到，可能不一致'} |")
    else:
        print("| 题目一致性 | ➖ | 未提供 --expected-title，跳过 |")

    # 5. 占位符
    if placeholders:
        print(f"| 模板占位符 | ⛔ | {'；'.join(placeholders)} |")
    else:
        print("| 模板占位符 | ✅ | 未发现明显未填项 |")

    print()
    print("> 说明：本脚本仅做结构层初筛。字体（宋体/Times New Roman）、手写签名、"
          "页眉页脚、三线表、图题位置、2/3 工作量占比等须按 SKILL.md / 审核清单全集.md 人工复核。")


def main():
    ap = argparse.ArgumentParser(description="毕业设计文档离线结构审查")
    ap.add_argument("docx")
    ap.add_argument("--type", required=True, choices=["task", "opening", "thesis"])
    ap.add_argument("--expected-title", default=None)
    ap.add_argument("--expected-refs", type=int, default=None)
    ap.add_argument("--min-chars", type=int, default=None)
    args = ap.parse_args()
    review(args.docx, args.type, args.expected_title, args.expected_refs, args.min_chars)


if __name__ == "__main__":
    main()
