---
name: lesson-plan-from-materials
description: "Batch-generate Word lesson plans (教案) from existing teaching materials such as PowerPoint files (.ppt/.pptx) or other documents, while mirroring a given lesson-plan template's exact format (tables, merged cells, fonts like 宋体 10.5pt). This skill should be used when a user asks to turn each PPT/slide deck into a lesson plan, generate lesson plans from course materials, or fill a teaching syllabus's course info into plan templates. It handles the hard parts automatically: robust text extraction from legacy binary .ppt (GBK/Big5/UTF-16 multi-codec auto-selection), format-preserving cell filling, and output verification."
agent_created: true
---

# 从素材批量生成教案 (Lesson Plan From Materials)

## Overview

把一批教学素材（通常是 PPT/PPTX，也可能是其他文档）逐章生成 Word 教案，并**严格套用**用户指定的教案模板版式（课程信息表 / 教案主体表 / 教学内容表的表结构、合并单元格、宋体 10.5pt 字体全部继承）。可进一步把教学大纲（syllabus.docx）里的课程编号、周次、考核方式、教材等信息回填进每份教案。

适用触发语：「把每个 PPT 都做成教案」「根据模板生成教案」「从素材批量生成教案」「按教学大纲把课程信息填进教案」。

## 何时使用

- 用户给出若干 `.ppt` / `.pptx` 和一个教案模板 `.docx`，要求逐份生成教案。
- 用户额外给出教学大纲 `.docx`，要求提取课程信息回填到生成的教案中。
- 源文件是**老格式 `.ppt`**（python-pptx 读不了）时尤其必要——本技能自带多编码自动选优提取。

## 核心脚本（scripts/）

| 脚本 | 作用 |
|------|------|
| `extract_ppt_text.py` | 从 `.pptx` 或老二进制 `.ppt` 提取文本。`.ppt` 用 olefile 枚举流 + GBK/Big5/UTF-16/UTF-8 多编码打分选优 + 领域词过滤乱码。**这是解决老 PPT 乱码的关键。** |
| `analyze_template.py` | 打印模板所有表格的 (行,列) 坐标与文本，定位课程信息表/教案主体表字段。 |
| `generate_lesson_docx.py` | 生成引擎：复制模板 → 按 JSON 里的坐标 fills 填充，**格式 100% 保持**（合并单元格不错位、宋体不变）。 |
| `verify_lessons.py` | 校验输出 docx 可打开、表格数、关键字段是否填对。 |

环境要求（在隔离 venv 中）：`python-docx`、`olefile`、`python-pptx`。
示例：`C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe`。

## Workflow

### Step 1 — 选对模板并探查坐标
- 课程目录里可能同时有「内容稿 docx」和「格式模板 docx」。**格式模板是含完整多表格的那份**，内容稿只是某章文字，不是蓝本。
- 运行 `analyze_template.py 模板.docx`，记录：表0=课程信息表、表1=教案主体表、表2=教学内容表的字段坐标。坐标因模板而异，必须实地探查，**不可硬编码记死**。

### Step 2 — 提取源素材文本
- `.pptx` 直接 `extract_ppt_text.py file.pptx`。
- `.ppt` 用 `extract_ppt_text.py file.ppt`（自动走 olefile 多编码选优）。
- **务必人工抽查前 1~2 章提取结果**，确认无乱码再写教案（老 PPT 内常混简体 GBK 与繁体 Big5 台湾素材）。

### Step 3 — 撰写每章教案内容
- 依据提取文本 + 课程定位，逐章撰写：授课题目、教学目标（知识/能力/素养三维度，可加思政）、教学任务、重点难点与突破、教学方法、5 步教学过程设计（时间/内容/师生活动/目标）、作业、总结分析。
- 多行文本用 `\n` 表示单元格内软换行，引擎会转成软换行且不破坏表格结构。
- 章号建议统一中文数字（第一章…第九章）贴合模板。

### Step 4 — 回填教学大纲的课程信息（可选）
- 若用户给了 syllabus.docx：用 python-docx 读取课程代码、学分/总学时、课程类别/性质、考核方式（含比例）、教材（书名+作者+出版社+年份）、参考资料、教学进度周次。
- 把周次摊回各章（注意大纲常按「教学单元」给，可能末两章合并为 1 单元 → 同落一周）。
- **编号差位必提示用户与教务数据核对**（用户口述与大纲印刷不一致是高频坑）。

### Step 5 — 构造 lessons.json 并生成
- 为每章构造一个 lesson 对象：`output` 文件名 + `fills` 列表（`{"table","row","col","value"}` 坐标来自 Step 1）。
- 运行 `generate_lesson_docx.py --template 模板.docx --json lessons.json --outdir 输出目录`。
- 引擎「先复制模板再填空」，因此合并单元格、字体、版式全部继承。

### Step 6 — 校验并交付
- 运行 `verify_lessons.py 输出目录` 确认每个 docx 可打开、表格数 >= 2、关键字段已填。
- 抽查 1 份在 Word 打开看版式（合并单元格、宋体）。
- 列出仍需用户确认的占位项（见下文），避免编造错误数据。

## 必须向用户确认的占位项（不要擅自编造）
1. 课程编号（与大纲差位时）；
2. 教材具体版本与作者（模板常留占位）；
3. 学分/总学时/周次/考核方式（沿用模板值前需确认）；
4. 授课进度周次（末两章是否拆两次课 → 周次 +1）；
5. 授课教师姓名/职称/教师类别（模板默认值）；
6. 封面校名/学期（模板默认值，如「西安航空学院 / 2026-2027-1」）。

## 踩坑速查
- **老 `.ppt` 乱码**：别用单一编码硬解，必须用 `extract_ppt_text.py` 的多编码打分选优；若无该脚本，退路是 PowerPoint COM 转 pptx（但隔离沙箱里 pywin32 post-install 常注册失败、GUI 可能被拦，优先 olefile 路线）。
- **误把内容稿当模板**：会导致生成的教案没有表格。先 `analyze_template.py` 确认模板有 >=2 个表。
- **合并单元格错位**：只要用「复制模板 + 坐标填空」方式（本技能引擎），就不会错位；切勿新建表格重画。
- **中文变西文字体**：填充时务必显式设 `w:eastAsia` 为宋体（引擎已处理）。

## 参考
详细工作流、真实任务示例与 syllabus→课程信息映射经验见 `references/workflow.md`。
