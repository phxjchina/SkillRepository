#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_lesson_docx.py — 格式保持的教案生成引擎

用法:
    python generate_lesson_docx.py --template T.docx --json lessons.json --outdir D

lessons.json 结构:
{
  "default_font": "宋体",          // 可选，默认 宋体
  "default_size": 10.5,            // 可选，默认 10.5pt（五号）
  "lessons": [
    {
      "output": "第1章-绪论教案.docx",
      "fills": [
        {"table": 0, "row": 0, "col": 1, "value": "智能科学与技术专业导论"},
        {"table": 1, "row": 0, "col": 1, "value": "第一章 绪论"},
        {"table": 1, "row": 5, "col": 1, "value": "知识目标：…\\n能力目标：…\\n素养目标：…"}
      ]
    }
  ]
}

机制:
    1) 每个 lesson 以「复制模板 → 打开副本」方式生成，从而 100% 保留
       模板的表格、合并单元格、整体版式；
    2) 对每个 fill：定位 table[row][col] 单元格，清空内容后以「首 run 的格式」
       重写（优先沿用单元格原有字体名/字号/加粗，否则用 default_font/size）；
    3) 显式设置 w:eastAsia 字体，保证中文在 Word 中显示为宋体而非默认西文字体；
    4) value 中的 \\n 换行转为段落内软换行（add_break），不改变表格结构；
    5) 合并单元格区域在 python-docx 中返回同一对象，填写一次即覆盖整片区域。
"""
import sys
import os
import json
import shutil
import argparse
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def set_cell_text(cell, value, ref_run=None, font="宋体", size=10.5):
    """清空单元格并以保留格式的方式写入文本。value 中 \\n 转为软换行。"""
    # 1) 删除多余段落（合并产生的空段等），保留第一段
    for p in list(cell.paragraphs[1:]):
        p._element.getparent().remove(p._element)
    p0 = cell.paragraphs[0]
    # 2) 清空首段所有 run
    for r in list(p0.runs):
        r._element.getparent().remove(r._element)

    # 3) 沿用参考 run 的格式
    if ref_run is not None:
        f_name = ref_run.font.name
        f_size = ref_run.font.size
        f_bold = ref_run.font.bold
        f_italic = ref_run.font.italic
    else:
        f_name, f_size, f_bold, f_italic = font, Pt(size), None, None

    # 4) 写入（支持 \n 软换行）
    lines = str(value).split("\n")
    run = p0.add_run(lines[0])
    for ln in lines[1:]:
        run.add_break()
        run2 = p0.add_run(ln)

    # 5) 应用字体（含东亚字体）
    for r in p0.runs:
        if f_name:
            r.font.name = f_name
        if f_size:
            r.font.size = f_size
        if f_bold is not None:
            r.font.bold = f_bold
        if f_italic is not None:
            r.font.italic = f_italic
        _set_eastasia(r, f_name or font)


def _set_eastasia(run, font):
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), font)
    rfonts.set(qn("w:ascii"), font)
    rfonts.set(qn("w:hAnsi"), font)


def main():
    ap = argparse.ArgumentParser(description="格式保持的教案生成引擎")
    ap.add_argument("--template", required=True, help="模板 docx 路径")
    ap.add_argument("--json", required=True, help="lessons.json 路径")
    ap.add_argument("--outdir", required=True, help="输出目录")
    args = ap.parse_args()

    cfg = json.load(open(args.json, encoding="utf-8"))
    default_font = cfg.get("default_font", "宋体")
    default_size = float(cfg.get("default_size", 10.5))
    lessons = cfg.get("lessons", [])

    os.makedirs(args.outdir, exist_ok=True)
    done = 0
    for les in lessons:
        out_path = os.path.join(args.outdir, les["output"])
        shutil.copyfile(args.template, out_path)
        doc = Document(out_path)
        for fill in les.get("fills", []):
            ti = fill["table"]
            ri = fill["row"]
            ci = fill["col"]
            val = fill.get("value", "")
            if ti >= len(doc.tables):
                print(f"  [跳过] {les['output']}: 表 {ti} 不存在", file=sys.stderr)
                continue
            tbl = doc.tables[ti]
            if ri >= len(tbl.rows) or ci >= len(tbl.columns):
                print(f"  [跳过] {les['output']}: 坐标 ({ri},{ci}) 越界", file=sys.stderr)
                continue
            cell = tbl.rows[ri].cells[ci]
            # 参考：单元格首段首 run 的格式
            ref = None
            if cell.paragraphs and cell.paragraphs[0].runs:
                ref = cell.paragraphs[0].runs[0]
            set_cell_text(cell, val, ref_run=ref,
                          font=default_font, size=default_size)
        doc.save(out_path)
        done += 1
        print(f"  生成: {out_path}")

    print(f"\n完成：共生成 {done} 个教案。")


if __name__ == "__main__":
    main()
