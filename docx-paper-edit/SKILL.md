---
name: docx-paper-edit
description: 学术论文 Word/docx 的 XML 级精确编辑与投稿前整备技能（纯 Node.js，不依赖 python-docx）。用于：① 引用编号按 GB/T 7714 顺序编码制整体重排（首现顺序映射、文献列表物理重排、中文附录联动）；② 参考文献替换/新增/删除与正文上标引用修正；③ 共享短语改写等查重整改落地；④ 解包→精确修改→三层校验→重打包全链路。当用户要求修改论文 docx（改引用编号、改文献、改正文措辞、查重整改、投稿前整备）且需直接改 .docx 文件时使用。修改 Office/WPS 文档的其他常规任务请走 tencent-docs-routing。
agent_created: true
---

# Docx Paper Edit（论文 docx 精确编辑）

## Overview

对学术论文 `.docx` 做 XML 级手术：解包 → Node.js 精确修改 `word/document.xml` → 三层校验 → 重打包覆盖。旗舰能力是把引用编号按 **GB/T 7714 顺序编码制**（按正文首次出现顺序编码）整体重排，同时保证"只动编号、不动内容"。适用于中文期刊（软件学报、计算机学报等）投稿前整备。

**环境前提**：本机标准 Python Lib 损坏，一切操作用 Node.js（v22）+ Git Bash unzip + PowerShell Compress-Archive。详见 `references/pitfalls.md`（**每次执行前必读**，含全部实测踩坑与 run 模板）。

## 总工作流

1. **备份**：`cp 原.docx 原.docx.<标记>.bak`。
2. **解包**：`unzip -o 文件.docx -d 目录`（返回码 1 可能只是警告，以 `目录/word/document.xml` 存在为准）。
3. **修改**：按下方任务类型选路径（A 引用重排 / B 手术编辑）。
4. **校验**：见"三层校验"。
5. **重打包**：PowerShell `Compress-Archive -Path 目录\* -DestinationPath x.zip`，再 `Move-Item` 改名 `.docx` 覆盖交付。
6. **交付复检**：对交付的 docx 重新解包，重跑全部核验。

## 任务 A：引用编号整体重排（脚本化）

```bash
# 重排（自动：首现扫描→映射→正文替换→列表重排→附录联动→自校验→写盘+落盘映射报告）
node scripts/renumber_citations.js <解包目录> <最大文献号N> [--appendix "附中文参考文献"]

# 核验（可对任意解包目录跑，含交付后复检）
node scripts/verify_docx.js <解包目录> <N> [--appendix "附中文参考文献"]
# 跨版本内容等价（证明只动编号不动内容）：
node scripts/verify_docx.js <新目录> <N> --old <旧解包目录> --report <新目录>/renumber_report.json
```

- 脚本处理的引用形态：单条 `[n]`、相邻簇 `[n][m]`、合并式 `[n,m]`（兼容全角逗号）、区间式 `[a−b]`（**U+2212**）。数学区间 `[−1,1]`/`[0,1]` 自动排除（含负号或 0 即不算引用）。
- 幂等：对已重排文档重跑 = 恒等映射，安全。
- 任何校验失败即非零退出且不写盘。
- **先人工过目**：跑之前先用小脚本全量列出正文所有含数字括号组及其上下文，确认分类无误（参见 pitfalls.md 第二节）。

## 任务 B：手术编辑（替换/新增文献条目、改写短语、修正引用格式）

手工 Node.js 脚本，规范：

1. 每处修改**强制 exactly-one 匹配**：定位串唯一，找不到或多处匹配即报错退出。
2. 新增正文上标引用与文献条目，用 `references/pitfalls.md` 第四节的 **run 模板**（字号等参数以目标文档既有条目实测为准，勿照抄）。
3. 拆 run 插入时新串**不闭合**（由原 `</w:t></w:r>` 收尾），否则产生孤儿闭合标签。
4. 新增引用前逐条核实文献真实出处（作者/venue/年份/DOI）；招聘广告、非审稿报告须向用户说明。
5. 改后统计 `<w:p>`/`<w:r>`/`<w:t>` 开闭数验证平衡。

## 三层校验（缺一不可）

1. **改后自校验**：标签平衡、首现序列==1..N 严格单调、列表 1..N 有序、附录升序、无悬空引用（任务 A 脚本内置；任务 B 用 `verify_docx.js`）。
2. **跨版本内容等价**：新列表第 k 条文本 == 旧列表第 order[k-1] 条，逐条 strip 比对。
3. **交付复检**：重打包覆盖后对交付 docx 重新解包，ZIP 完整性 + 核验脚本重跑。

## Resources

- `scripts/renumber_citations.js` — 引用编号重排主脚本（参数化、幂等、带自校验与映射报告）。
- `scripts/verify_docx.js` — 引用体系核验脚本（基础核验 + 可选跨版本等价）。
- `references/pitfalls.md` — 实测踩坑清单：解包/重打包、引用四形态与数学区间排除、no-op 校验陷阱、拆 run 闭合陷阱、run 模板、三层校验。**执行前必读。**
