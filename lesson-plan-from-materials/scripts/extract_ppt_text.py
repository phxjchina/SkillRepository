#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_ppt_text.py — 从 PPT 提取文本（兼容 .pptx 与老二进制 .ppt）

用法:
    python extract_ppt_text.py <input.ppt|.pptx> [-o output.txt]
    python extract_ppt_text.py <input.ppt|.pptx> --preview      # 仅打印前 N 行

设计要点:
    1) .pptx: 直接用 python-pptx 读幻灯片文本 + 备注。
    2) .ppt (OLE 二进制老格式，python-pptx 读不了): 用 olefile 枚举所有流，
       对每个流逐一尝试 utf-16-le / gbk / big5 / utf-8 解码，
       用「常用汉字 + 领域词命中 - 乱码惩罚」打分选出最优解码，
       再按领域词过滤掉噪声流。PPT 里常混简体(GBK)与繁体(Big5，如台湾素材)，
       纯猜测解码会乱码，必须自动选优。
    3) 输出按「幻灯片/流」分块，便于据此撰写教案。
"""
import sys
import os
import re
import argparse
from pathlib import Path

# ------- 评分用词典 -------
# 领域词（智能科学/计算机/教学），命中越多越像正文
DOMAIN_WORDS = [
    "智能", "学习", "机器", "数据", "认知", "模式", "识别", "感知", "语言", "处理",
    "系统", "网络", "算法", "模型", "人工", "神经", "深度", "训练", "特征", "分类",
    "聚类", "传感", "定位", "云计算", "大数据", "机器人", "专家", "知识", "推理",
    "图像", "语音", "文本", "语义", "符号", "逻辑", "计算", "架构", "应用", "技术",
    "科学", "理论", "方法", "结构", "功能", "信息", "信号", "控制", "优化", "决策",
    "教学", "课程", "学生", "教师", "目标", "重点", "难点", "实验", "概念", "原理",
]
REPLACEMENT = "\ufffd"
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def extract_pptx(path: str):
    from pptx import Presentation
    prs = Presentation(path)
    blocks = []
    for i, slide in enumerate(prs.slides, 1):
        lines = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                t = shape.text_frame.text.strip()
                if t:
                    lines.append(t)
            if shape.has_table:
                tbl = shape.table
                for r in tbl.rows:
                    cells = [c.text.strip() for c in r.cells]
                    line = " | ".join(c for c in cells if c)
                    if line:
                        lines.append(line)
        # 备注
        if slide.has_notes_slide:
            nt = slide.notes_slide.notes_text_frame.text.strip()
            if nt:
                lines.append("[备注] " + nt)
        if lines:
            blocks.append((f"幻灯片 {i}", "\n".join(lines)))
    return blocks



# 行尾常黏着二进制乱码字符（藏文/缅甸文/私用区等），截断到第一个"非安全字符"
_SAFE = re.compile(
    r"[\u4e00-\u9fff"          # 汉字
    r"\u3000-\u303f\u3040-\u30ff"  # 中日标点/假名
    r"\u3400-\u4dbf"           # 扩展A
    r"a-zA-Z0-9\s"
    r"，。、；：？！“”‘’（）《》〈〉—…·．%％\-/\\:：,.!?()\[\]]+"  # 半角/全角标点
)


def _trim_garbage(line: str) -> str:
    """保留行首连续的安全字符（汉字/字母/数字/常见标点），截断尾部二进制乱码。"""
    m = _SAFE.match(line)
    if not m:
        return ""
    return m.group(0).strip()


def _clean_lines(txt: str):
    """从解码文本中筛出「干净中文行」：≥4 汉字、无替换符、含领域词或字数较多。"""
    out = []
    for ln in txt.splitlines():
        ln = _trim_garbage(ln)
        if not ln:
            continue
        cjk = CJK_RE.findall(ln)
        if len(cjk) < 4:
            continue
        if REPLACEMENT in ln:
            continue
        if any(w in ln for w in DOMAIN_WORDS) or len(cjk) >= 8:
            out.append(ln)
    return out


def _decode_stream_text(data: bytes):
    """对一个流字节，返回最佳可读文本。

    判别关键：按「干净中文行数」而非「整段领域词子串数」选编码——
    乱码的 UTF-16 整段解码里会随机命中大量 2 字领域词，导致错选乱码；
    而真正的正文（GBK/Big5 或 UTF-16LE）会产生大量干净行。逐编码统计
    干净行数，择多者即为正确编码。
    """
    cands = []
    for enc in ("utf-16-le", "gbk", "big5", "utf-8"):
        try:
            txt = data.decode(enc, errors="replace")
        except Exception:
            continue
        cl = _clean_lines(txt)
        cands.append((len(cl), enc, txt))
    if not cands:
        return ""
    cands.sort(key=lambda x: x[0], reverse=True)
    return cands[0][2]


def extract_ppt(path: str):
    """从老格式 .ppt 提取文本。

    关键事实：中文 .ppt 的幻灯片正文通常存放在 'PowerPoint Document' 流里，
    且多数以 GBK（简体）或 Big5（繁体，如台湾素材）单字节编码存储于文本记录中；
    字体名等少数字段才是 UTF-16LE。因此对每个流做 GBK/Big5/UTF16/UTF8 解码、
    用「领域词命中」择优选出可读文本，再按行清洗与过滤，避免把二进制误当正文。
    """
    import olefile
    ole = olefile.OleFileIO(path)
    blocks = []
    idx = 0
    for s in ole.listdir():
        full = "/".join(s)
        try:
            data = ole.openstream(s).read()
        except Exception:
            continue
        if len(data) < 16:
            continue
        # 'Pictures' 等纯二进制流跳过
        if "Picture" in full:
            continue
        txt = _decode_stream_text(data)
        if not txt:
            continue
        keep = _clean_lines(txt)
        if not keep:
            continue
        idx += 1
        blocks.append((f"文本块 {idx} ({full[:24]})", "\n".join(keep)))
    ole.close()
    return blocks


def main():
    ap = argparse.ArgumentParser(description="从 PPT(.ppt/.pptx) 提取文本")
    ap.add_argument("input", help="输入 PPT 文件路径")
    ap.add_argument("-o", "--output", help="输出 txt 路径（默认打印到 stdout）")
    ap.add_argument("--preview", action="store_true", help="仅预览前 60 行")
    args = ap.parse_args()

    ext = os.path.splitext(args.input)[1].lower()
    if ext == ".pptx":
        blocks = extract_pptx(args.input)
    elif ext == ".ppt":
        blocks = extract_ppt(args.input)
    else:
        print(f"不支持的扩展名: {ext}", file=sys.stderr)
        sys.exit(2)

    out_lines = []
    for title, body in blocks:
        out_lines.append(f"\n##### {title} #####")
        out_lines.append(body)

    text = "\n".join(out_lines)
    if args.preview:
        print("\n".join(out_lines.splitlines()[:60]))
        return
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"已写出 {len(blocks)} 个文本块 -> {args.output}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
