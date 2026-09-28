# -*- coding: utf-8 -*-
"""章节结构修复器（tech-book-pipeline 阶段 2/3）。

解决两个实战坑:
1. 增厚片段被插到"参考文献"之后 → 把文献条目之后的正文块整体搬回文献节之前;
2. 插入节用 ### 且与正文重号 → 统一升级为 ## 并在正文最大节号后顺延重编号,
   同时盘点正文里对这些旧节号的交叉引用(供人工核对)。

用法:
    python fix_chapter_structure.py 第5章.md [第6章.md ...]

幂等可重跑; 只处理形如 "### N.M 标题" 的编号节, 其他 ### 原样保留。
"""
import sys, re

def fix(f):
    lines = open(f, encoding="utf-8").read().split("\n")
    R = next((i for i, l in enumerate(lines) if re.match(r'^#{2,3} .*参考文献', l)), None)
    moved_report = []

    # ---- 1) 参考文献后的正文块搬回文献前 ----
    if R is not None:
        F = None
        for i in range(len(lines) - 1, R, -1):
            if re.match(r'^\*（.*）\*$', lines[i].strip()):
                F = i; break
        if F is None:
            print("!! 未找到页脚:", f); return
        i = R + 1
        ref_lines = []
        while i < F:                       # 收集连续的 [ 开头文献条目(允许空行)
            l = lines[i]
            if l.strip() == "":
                j = i
                while j < F and lines[j].strip() == "":
                    j += 1
                if j < F and lines[j].lstrip().startswith("["):
                    ref_lines.extend(lines[i:j]); i = j; continue
                break
            elif l.lstrip().startswith("["):
                ref_lines.append(l); i += 1
            else:
                break
        body_after = lines[i:F]
        while body_after and not body_after[0].strip(): body_after.pop(0)
        while body_after and not body_after[-1].strip(): body_after.pop()
        if body_after:
            lines = lines[:R] + [""] + body_after + [""] + [lines[R]] + ref_lines + lines[F:]
            moved_report.append("搬移正文 %d 行" % len(body_after))

    # ---- 2) ### N.M → ## 顺延重编号 ----
    ch_m = re.search(r'第(\d+)章', f)
    ch = int(ch_m.group(1)) if ch_m else 0
    body_max = max([int(m.group(2)) for l in lines
                    if (m := re.match(r'^## (\d+)\.(\d+) ', l))] or [0])
    mapping = {}
    out = []
    for l in lines:
        m = re.match(r'^### (\d+)\.(\d+) (.+)$', l)
        if m:
            old = "%s.%s" % (m.group(1), m.group(2))
            body_max += 1
            mapping[old] = "%d.%d" % (ch, body_max)
            out.append("## %d.%d %s" % (ch, body_max, m.group(3)))
        else:
            out.append(l)
    open(f, "w", encoding="utf-8", newline="\n").write("\n".join(out))

    print(f, "|", "; ".join(moved_report) or "顺序正常", "| 重编号:", mapping or "无")
    for old in mapping:                    # 交叉引用盘点(不自动改, 供人工核对)
        for i, l in enumerate(out):
            if re.match(r'^#{1,3} ', l):
                continue
            if re.search(r'(?<![\d.])%s(?![\d])' % re.escape(old), l):
                print("   引用@%d: %s" % (i + 1, l.strip()[:66]))

if __name__ == "__main__":
    for f in sys.argv[1:]:
        fix(f)
