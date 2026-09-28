# -*- coding: utf-8 -*-
"""知乎系列发布排期清单生成器（tech-book-pipeline 阶段 5）。

从系列目录各篇 md 里自动提取 `# 标题` 与 `**一句话摘要**：…`,
生成 00-发布排期清单.md(排期表 + 发布要点)。

用法:
    python gen_publish_list.py <系列目录> [起始日 YYYY-MM-DD] [间隔天数]

默认起始日 = 明天, 间隔 1 天(每日一篇)。
各篇归属(篇目分组)按文件名前两位序号均分到 5 组, 可按需改 pos()。
"""
import sys, os, re, glob
from datetime import date, timedelta

def pos(n, total):
    # 5 组: 基座 / 史 / 图谱 / 收敛 / 完结, 按比例切
    marks = [int(total * k / 5) for k in (1, 2, 3, 4)]
    names = ["基座篇", "主体篇", "图谱篇", "收敛篇", "完结篇"]
    for k, mk in enumerate(marks):
        if n <= mk:
            return names[k]
    return names[-1]

def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    d0 = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today() + timedelta(days=1)
    step = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    rows = []
    for f in sorted(glob.glob(os.path.join(d, "[0-9][0-9]-*.md"))):
        if os.path.basename(f).startswith("00-"):
            continue
        t = open(f, encoding="utf-8").read()
        m_t = re.search(r'^# (.+)$', t, re.M)
        m_a = re.search(r'\*\*一句话摘要\*\*：(.+)$', t, re.M)
        n = os.path.basename(f)[:2]
        rows.append((n, m_t.group(1).strip() if m_t else "",
                     m_a.group(1).strip() if m_a else "（无摘要行）"))

    lines = ["# 知乎系列 · 发布排期清单\n",
             "> 节奏：每日一篇（隔 N 天改参数）。发布时：标题/摘要直接从表复制，封面上传 `配图/NN.png`。\n",
             "| 序 | 建议发布日 | 篇目 | 标题 | 一句话摘要 | 封面 |",
             "|---|---|---|---|---|---|"]
    for n, title, ab in rows:
        k = int(n)
        dt = (d0 + timedelta(days=(k - 1) * step)).strftime("%m-%d %a")
        lines.append("| %s | %s | %s | %s | %s | 配图/%s.png |" %
                     (n, dt, pos(k, len(rows)), title, ab, n))
    lines += ["\n## 发布要点\n",
              "- **01 篇是导流关键**：建议固定早 8 点前发出；",
              "- 各篇结尾「下一篇」预告已内嵌，无需另加；",
              "- 完结篇发出后评论区置顶引流（如领全书/专栏）；",
              "- 建议建知乎专栏按序收录，形成追更链；断更顺延即可。"]

    out = os.path.join(d, "00-发布排期清单.md")
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("已生成:", out, "| 篇数:", len(rows))

if __name__ == "__main__":
    main()
