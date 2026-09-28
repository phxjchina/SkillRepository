# -*- coding: utf-8 -*-
"""公开发布版私人路径校验器（tech-book-pipeline 阶段 3）。

用法:
    python check_private_paths.py <目录或文件...> [--glob 0[5-9]-*.md]

对每个目标文件检查: 盘符路径 / "本机" / 内部文档名 / 本地特征路径。
有残留则打印文件与行号并以退出码 1 结束（可接在 CI / 脚本链里当闸门）。
"""
import sys, re, glob, os

PATTERNS = [
    r'[EeCeDd]:[/\\]',          # 盘符路径
    r'本机',                    # "本机"字样
    r'公众号及知乎文章',         # 本地资料目录名
    r'补充文献-',
    r'\.workbuddy',
    r'C:/Users',
    r'技术史档案/',             # 内部目录引用
    r'私人证据库',
    r'横向课题|无锡项目',        # 项目来源特征
]

def check(path):
    bad = []
    txt = open(path, encoding="utf-8", errors="ignore").read()
    for i, line in enumerate(txt.split("\n"), 1):
        for p in PATTERNS:
            if re.search(p, line):
                bad.append((i, line.strip()[:80]))
                break
    return bad

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    g = None
    if "--glob" in sys.argv:
        g = sys.argv[sys.argv.index("--glob") + 1]
    files = []
    for a in args:
        if os.path.isdir(a):
            files += sorted(glob.glob(os.path.join(a, g or "*.md")))
        else:
            files.append(a)
    total = 0
    for f in files:
        bad = check(f)
        if bad:
            total += len(bad)
            print("!! %s : %d 处" % (f, len(bad)))
            for ln, s in bad[:5]:
                print("   L%d: %s" % (ln, s))
    print("残留总数:", total, "| 检查文件数:", len(files))
    sys.exit(1 if total else 0)

if __name__ == "__main__":
    main()
