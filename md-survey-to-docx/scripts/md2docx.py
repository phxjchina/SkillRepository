# -*- coding: utf-8 -*-
"""
把 survey/main.md 转成 Word(.docx)：
1) 将 [论文标题] 形式的内联引用统一替换为 GB/T 7714 顺序编码制的数字上角标 [n]
2) 输出 main_numbered.md（可核查）与 模型驱动工程与机器学习融合综述.docx
"""
import re, sys, os, json
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn

BASE = r"D:\WorkBuddy_workspace\2026-08-08-18-12-23\survey"
SRC = os.path.join(BASE, "main.md")
OUT_MD = os.path.join(BASE, "main_numbered.md")
OUT_DOCX = os.path.join(BASE, "模型驱动工程与机器学习融合综述.docx")

raw = open(SRC, encoding="utf-8").read()

# ---------------- 1. 解析参考文献列表，建立 标题 -> 编号 ----------------
ref_section = raw.split("## 参考文献")[1]
ref_re = re.compile(r"^(\d+)\.\s+(.+?)\s+—\s*(.*)$", re.M)
refs = []  # (num, title, source)
for m in ref_re.finditer(ref_section):
    refs.append((int(m.group(1)), m.group(2).strip(), m.group(3).strip()))
print(f"[refs] parsed {len(refs)} references")


def norm(s: str) -> str:
    s = s.lower()
    s = s.replace("’", "'").replace("—", " ").replace("–", " ")
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", s)
    return s


title2num = {}
for num, title, _src in refs:
    title2num[norm(title)] = num

# ---------------- 2. 找出正文中的引用 ----------------
body, tail = raw.split("\n## 参考文献", 1)

CITE_PATTERNS = [
    re.compile(r"\[`([^`\]]+)`\]"),      # [`Title`]
    re.compile(r"`\[([^`\]]+)\]`"),      # `[Title]`
]
# 纯 [Title] （英文、含空格、长度>15），排除 markdown 链接
PLAIN = re.compile(r"(?<!`)\[([A-Za-z][^\[\]\n]{15,})\](?!\()")

found = []
for p in CITE_PATTERNS:
    found += [m.group(1) for m in p.finditer(body)]
plain_hits = [m.group(1) for m in PLAIN.finditer(body)]
print(f"[scan] backticked citations: {len(found)}, plain-bracket candidates: {len(plain_hits)}")

unmatched = sorted({t for t in found if norm(t) not in title2num})
if unmatched:
    print("\n[!! UNMATCHED CITATIONS !!]")
    for t in unmatched:
        print("   -", t)
else:
    print("[ok] every citation title matches a numbered reference")

# ---------------- 3. 替换为上标占位符 ----------------
SUP_OPEN, SUP_CLOSE = "\x00SUP[", "]\x00"


def to_sup(title: str) -> str:
    n = title2num.get(norm(title))
    if n is None:
        return f"{SUP_OPEN}?{SUP_CLOSE}"
    return f"{SUP_OPEN}{n}{SUP_CLOSE}"


def sub_all(text: str) -> str:
    for p in CITE_PATTERNS:
        text = p.sub(lambda m: to_sup(m.group(1)), text)
    return text


# 头部说明句先行改写（其中含示例引用，不能被当成真引用替换）
body = body.replace(
    "所有引用均以来源库中的论文标题标记，如 `[A domain-specific language for describing machine learning datasets]`，且只为已确认收录的论文提供引用。",
    "全文文献引用采用 GB/T 7714 顺序编码制，以方括号数字上角标标注，编号与文末「参考文献」一一对应；且只为源库中已确认收录的论文提供引用。",
)

body = sub_all(body)

# 引用前的空格去掉：正文 [1] -> 正文[1]
body = re.sub(r"[ \u3000]+(?=\x00SUP\[)", "", body)
# 引用位于「：」之后作主语时，补「文献」二字，避免「：[6] 提出…」读不通
body = re.sub(r"(?<=：)(\x00SUP\[\d+\]\x00)\s*", lambda m: "文献" + m.group(1), body)
# 上标后紧跟空格再接中文的，去掉空格
body = re.sub(r"(\x00SUP\[\d+\]\x00) +(?=[\u4e00-\u9fff（])", r"\1", body)

# ---------------- 4. 改写参考文献小节说明 ----------------
tail = sub_all("\n## 参考文献" + tail)
tail = tail.replace("## 参考文献（按引用标题索引）", "## 参考文献")
tail = tail.replace(
    "> 完整 BibTeX 见 `references.bib`。以下为便于核查的标题—出处对照（仅列本综述实际引用的 42 篇）。",
    "> 按正文首次出现顺序编号，共 42 篇；完整 BibTeX 见 `references.bib`。",
)

full = body + tail

# 统计使用情况
used = sorted({int(x) for x in re.findall(r"\x00SUP\[(\d+)\]\x00", body)})
print(f"[cite] distinct references cited in body: {len(used)} / {len(refs)}")
missing = [n for n, _t, _s in refs if n not in used]
if missing:
    print("[warn] references never cited inline:", missing)

# 输出可核查的 md（把占位符写成 ^[n]^）
md_out = full.replace(SUP_OPEN, "^[").replace(SUP_CLOSE, "]^")
open(OUT_MD, "w", encoding="utf-8").write(md_out)
print(f"[write] {OUT_MD}")

# ---------------- 5. 生成 docx ----------------
CN_BODY = "宋体"
CN_HEAD = "黑体"
EN_BODY = "Times New Roman"


def set_run(run, cn=CN_BODY, en=EN_BODY, size=12, bold=False, sup=False,
            italic=False, color=None):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = en
    rpr = run._element.get_or_add_rPr()
    rf = rpr.get_or_add_rFonts()
    rf.set(qn("w:ascii"), en)
    rf.set(qn("w:hAnsi"), en)
    rf.set(qn("w:eastAsia"), cn)
    if sup:
        run.font.superscript = True
    if color:
        run.font.color.rgb = color


INLINE = re.compile(
    r"(\x00SUP\[\d+\]\x00)"      # 1 上标
    r"|(\*\*(.+?)\*\*)"           # 2/3 加粗
    r"|(`([^`]+)`)"               # 4/5 代码
)


def add_inline(par, text, size=12, base_bold=False, cn=CN_BODY):
    pos = 0
    for m in INLINE.finditer(text):
        if m.start() > pos:
            r = par.add_run(text[pos:m.start()])
            set_run(r, size=size, bold=base_bold, cn=cn)
        if m.group(1):
            n = re.search(r"\d+", m.group(1)).group(0)
            r = par.add_run(f"[{n}]")
            set_run(r, size=size, sup=True, cn=cn)
        elif m.group(2):
            r = par.add_run(m.group(3))
            set_run(r, size=size, bold=True, cn=CN_HEAD if cn == CN_BODY else cn)
        elif m.group(4):
            r = par.add_run(m.group(5))
            set_run(r, size=size - 0.5, en="Consolas", cn=cn, bold=base_bold)
        pos = m.end()
    if pos < len(text):
        r = par.add_run(text[pos:])
        set_run(r, size=size, bold=base_bold, cn=cn)


doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(3.0)
sec.top_margin = sec.bottom_margin = Cm(2.5)

# 默认样式
st = doc.styles["Normal"]
st.font.name = EN_BODY
st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), CN_BODY)


def new_par(space_before=0, space_after=6, line=1.5, align=None,
            indent_first=0, indent_left=0, hanging=0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = line
    if align is not None:
        p.alignment = align
    if indent_first:
        pf.first_line_indent = Pt(indent_first)
    if indent_left:
        pf.left_indent = Cm(indent_left)
    if hanging:
        pf.left_indent = Cm(hanging)
        pf.first_line_indent = Cm(-hanging)
    return p


lines = full.split("\n")
i = 0
in_ref_list = False
while i < len(lines):
    ln = lines[i].rstrip()
    i += 1

    if not ln.strip():
        continue
    if re.fullmatch(r"-{3,}", ln.strip()):
        continue

    # 标题
    if ln.startswith("# "):
        p = new_par(space_before=0, space_after=18, line=1.4,
                    align=WD_ALIGN_PARAGRAPH.CENTER)
        r = p.add_run(ln[2:].strip())
        set_run(r, cn=CN_HEAD, size=18, bold=True)
        continue
    if ln.startswith("### "):
        p = new_par(space_before=12, space_after=6, line=1.4)
        r = p.add_run(ln[4:].strip())
        set_run(r, cn=CN_HEAD, size=13, bold=True)
        continue
    if ln.startswith("## "):
        t = ln[3:].strip()
        in_ref_list = t.startswith("参考文献")
        p = new_par(space_before=16, space_after=8, line=1.4)
        r = p.add_run(t)
        set_run(r, cn=CN_HEAD, size=15, bold=True)
        continue

    # 引用块
    if ln.startswith("> "):
        p = new_par(space_before=4, space_after=8, line=1.4, indent_left=0.8)
        add_inline(p, ln[2:].strip(), size=10.5)
        for r in p.runs:
            r.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
        continue

    # 无序列表
    if ln.startswith("- "):
        p = new_par(space_before=0, space_after=4, line=1.45, hanging=0.9)
        r = p.add_run("• ")
        set_run(r, size=12)
        add_inline(p, ln[2:].strip(), size=12)
        continue

    # 有序列表
    m = re.match(r"^(\d+)\.\s+(.*)$", ln)
    if m:
        if in_ref_list:
            p = new_par(space_before=0, space_after=3, line=1.3, hanging=1.15)
            r = p.add_run(f"[{m.group(1)}] ")
            set_run(r, size=10.5)
            add_inline(p, m.group(2), size=10.5)
        else:
            p = new_par(space_before=0, space_after=4, line=1.45, hanging=0.9)
            r = p.add_run(f"{m.group(1)}. ")
            set_run(r, size=12)
            add_inline(p, m.group(2), size=12)
        continue

    # 普通段落
    p = new_par(space_before=0, space_after=8, line=1.6, indent_first=24)
    add_inline(p, ln.strip(), size=12)

doc.save(OUT_DOCX)
print(f"[write] {OUT_DOCX}")
print("DONE")
