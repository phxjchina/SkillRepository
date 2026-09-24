#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_defense_ppt.py — 生成毕业设计答辩PPT(.pptx)
标准 13 页结构（封面→目录→背景→现状→内容→方法→实现→测试→总结→致谢→问答准备），
中文占位【…】直接改字即可。需 python-pptx（托管 python 已内置）。
用法:
  python gen_defense_ppt.py --out 答辩PPT.pptx --title "题目" --name "学生" --advisor "教师" [--major "专业班级"]
"""
import argparse
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

FONT = "微软雅黑"
NAVY = RGBColor(0x1F, 0x3A, 0x5F)
ACCENT = RGBColor(0x2E, 0x74, 0xB5)
GRAY = RGBColor(0x59, 0x59, 0x59)


def add_slide(prs, title, bullets, title_size=28, body_size=16):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    # 标题条
    box = slide.shapes.add_textbox(Inches(0.5), Inches(0.35), Inches(9), Inches(0.9))
    tf = box.text_frame
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = title
    r.font.size = Pt(title_size)
    r.font.bold = True
    r.font.name = FONT
    r.font.color.rgb = NAVY
    # 下划线装饰
    line = slide.shapes.add_shape(1, Inches(0.55), Inches(1.25), Inches(8.9), Pt(2.5))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT
    line.line.fill.background()
    # 正文
    body = slide.shapes.add_textbox(Inches(0.7), Inches(1.55), Inches(8.7), Inches(5.2))
    btf = body.text_frame
    btf.word_wrap = True
    first = True
    for item in bullets:
        text, level = (item if isinstance(item, tuple) else (item, 0))
        p = btf.paragraphs[0] if first else btf.add_paragraph()
        first = False
        p.level = level
        p.space_after = Pt(10)
        r = p.add_run()
        r.text = ("• " if level == 0 else "– ") + text
        r.font.size = Pt(body_size if level == 0 else body_size - 2)
        r.font.name = FONT
        r.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    return slide


def cover(prs, a):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    band = slide.shapes.add_shape(1, Inches(0), Inches(2.0), Inches(10), Pt(4))
    band.fill.solid()
    band.fill.fore_color.rgb = ACCENT
    band.line.fill.background()
    box = slide.shapes.add_textbox(Inches(0.5), Inches(2.3), Inches(9), Inches(1.6))
    p = box.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = a.title or "【毕业设计题目】"
    r.font.size = Pt(34)
    r.font.bold = True
    r.font.name = FONT
    r.font.color.rgb = NAVY
    info = slide.shapes.add_textbox(Inches(0.5), Inches(4.3), Inches(9), Inches(1.6))
    itf = info.text_frame
    for line in ["答辩人：%s　　专业班级：%s" % (a.name or "【姓名】", a.major or "【专业班级】"),
                 "指导教师：%s" % (a.advisor or "【教师】"), "【学院名称】 · 【答辩日期】"]:
        pp = itf.add_paragraph() if itf.paragraphs[0].runs else itf.paragraphs[0]
        pp.alignment = PP_ALIGN.CENTER
        rr = pp.add_run()
        rr.text = line
        rr.font.size = Pt(18)
        rr.font.name = FONT
        rr.font.color.rgb = GRAY


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default=None)
    ap.add_argument("--name", default=None)
    ap.add_argument("--advisor", default=None)
    ap.add_argument("--major", default=None)
    a = ap.parse_args()

    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)
    cover(prs, a)

    add_slide(prs, "目录", ["研究背景与意义", "国内外研究现状", "研究内容与拟解决问题",
                            "方法与技术路线", "系统/项目实现", "测试与结果", "总结与展望"], 30)
    add_slide(prs, "一、研究背景与意义", [
        "【背景：该问题在什么场景下存在，1-2句】",
        "【痛点：现有做法哪里不够用】",
        "【意义：本课题解决后带来什么价值】"], 28)
    add_slide(prs, "二、国内外研究现状", [
        "【国外：代表性工作1-2项（一句话概括）】",
        "【国内：代表性工作1-2项】",
        "【评述：现有不足 → 本文切入点】（别堆文献，重点在评述）"], 28)
    add_slide(prs, "三、研究内容与拟解决问题", [
        "【内容1：…】", "【内容2：…】", "【内容3：…】",
        "【关键问题：2-3个技术难点】"], 28)
    add_slide(prs, "四、方法与技术路线", [
        "【总体技术路线图（贴图）】",
        "【选型：语言/框架/硬件 + 一句为什么】",
        "【与研究手段一致性：与开题报告/任务书一致】"], 28)
    add_slide(prs, "五、系统实现（重点·多图）", [
        "【总体架构图】",
        "【模块1：运行截图+一句说明】",
        "【模块2：运行截图+一句说明】",
        "【模块3：核心流程/关键代码思路】"], 28)
    add_slide(prs, "六、测试与结果", [
        "【测试环境与用例（表格）】",
        "【关键结果数据/对比（图表）】",
        "【结果说明：达到任务书指标没有】"], 28)
    add_slide(prs, "七、总结与展望", [
        "【完成的工作：对照任务书逐条】",
        "【不足：1-2条，诚实】",
        "【展望：如再给三个月会怎么做】"], 28)
    add_slide(prs, "致谢", ["感谢指导教师%s的悉心指导" % (a.advisor or "【教师】"),
                            "感谢各位评委老师，请批评指正！"], 28)
    add_slide(prs, "答辩问答准备（自用页，答辩前删）", [
        "【预判问题1：为什么选这个技术？】",
        "【预判问题2：和已有方法比创新在哪？】",
        "【预判问题3：图X是什么含义？】",
        "【预判问题4：数据库/协议细节？】",
        "心法：不会就说'这方面我后续会补充'，别硬编"], 24, 14)

    prs.save(a.out)
    print("[pptx] %s（%d 页）" % (a.out, len(prs.slides.__iter__.__self__._sldIdLst)))


if __name__ == "__main__":
    main()
