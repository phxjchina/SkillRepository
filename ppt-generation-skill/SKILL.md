---
name: ppt-generation-skill
displayName: PPT Generation Skill
description: 根据研究报告/论文/作业/项目方案，创建结构清晰、要点精炼的 PowerPoint 演示文稿（含幻灯片大纲、简洁要点、演讲者备注与视觉设计建议）。适用于课堂、学术汇报、开题、答辩、业务汇报等场景；可产出真实 .pptx 文件。无需外部 API，离线可用（本机用 python-pptx 落地）。
source: clawhub (scc-nyy)
version: "1.0.0"
requires_api_key: false
---

# PPT Generation Skill

Create clear, structured, and visually coherent PowerPoint presentations for academic, research, classroom, business, and project-based purposes. Especially useful when the user needs to turn research notes, papers, reports, assignments, experimental designs, or project plans into a presentation-ready slide deck.

## When to Use

- 从零创建 PowerPoint 演示文稿。
- 把论文 / 报告 / 文献 / 开题报告整理成幻灯片。
- 设计课堂演示、导师汇报、开题、答辩、会议演讲。
- 把一篇研究文章摘要成幻灯片。
- 生成演示大纲与演讲者备注。
- 优化幻灯片的逻辑、结构与视觉层次。
- 把密集文本改写成精简 bullet。
- 设计 Q&A 页、结语页、过渡页。

## Inputs

用户可提供：
- 主题或标题；
- 论文 / 报告 / 大纲 / 作业内容；
- 需要的幻灯片数量；
- 演示时长；
- 目标受众；
- 语言偏好；
- 视觉风格（学术 / 简洁 / 极简 / 专业 / 活泼 / 正式）；
- 是否需要演讲者备注；
- 最终产出是"大纲"还是"可下载的 .pptx 文件"。

## Core Workflow

### 1. 明确演示目标
先确认：演示想达成什么、受众是谁、受众背景知识多少、用途是教学 / 汇报 / 说服 / 答辩 / 总结。

### 2. 搭幻灯片结构
典型结构：
- 标题页
- 背景 / 问题陈述
- 关键概念或理论框架
- 研究问题 / 目标
- 方法 / 设计
- 发现 / 分析 / 预期结果
- 讨论 / 意义
- 局限
- 结论
- Q&A
短演示优先保证清晰，减少节数。

### 3. 把内容改写成"幻灯片语言"
幻灯片内容应：
- 精简（concise）
- 有层次（hierarchical）
- 易扫读（scannable）
- 每页一个中心思想
- 适当配图：流程图 / 表格 / 时间轴 / 图标 / 高亮框 / 关系图 / 数据图
**严禁把长段落直接整段贴到幻灯片上。**

### 4. 设计视觉逻辑
- 流程 → 流程图
- 对比 → 表格
- 研究计划 → 时间轴
- 分类 → 图标
- 重点 → 高亮框
- 理论关系 → 关系图
- 数据/结果 → 图表

### 5. 加演讲者备注
- 用自然口语解释本页；
- 帮主讲人流畅表达，不要照读幻灯片；
- 需要时在页间加过渡语。

## Output Requirements

按用户请求，可提供以下一种或多种：
- 逐页完整大纲；
- 幻灯片标题 + bullet 要点；
- 演讲者备注；
- 视觉设计建议；
- 一份完整的 `.pptx` 文件；
- 对已有演示的修订版；
- 更短 / 更正式的精简版。

## Style Guidelines

- 标题要能传达本页要点；
- 避免一页过载；
- bullet 要短；
- 全篇术语一致；
- 学术内容要让外行也能懂，但不弱智化；
- 研究类逻辑：背景 → 空白 → 目标 → 方法 → 结果/预期结果 → 意义；
- 对非专业受众，简要解释术语。

## Example User Requests

- "帮我根据这篇文献做一份 10 页 PPT。"
- "请把我的开题报告整理成 8 分钟汇报 PPT。"
- "帮我优化这份 PPT，让完全不懂这个项目的人也能听懂。"
- "请帮我写每一页的中文讲稿。"
- "帮我把这一段内容变成适合放在 PPT 上的简短 bullet points。"
- "请帮我生成一份可下载的 PowerPoint 文件。"

---

## Local Usage (offline, WorkBuddy 本机落地指引)

本机无外网、无 PowerPoint COM 时，按此落地真实 `.pptx`：

1. **引擎**：用托管 venv 的 `python-pptx` 直接写 `.pptx`
   - 解释器：`C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe`
   - 已验证可 `import pptx` 并打开/生成文件。
2. **配图**：ImageGen 生成的 PNG 直接 `slide.shapes.add_picture()` 插入（绝对路径），**不要**走会丢图的 DSL upsert 通道。
3. **文字密度**：严格遵循上面"幻灯片语言"——每页 ≤ 4 段、每点 ≤ 2 行；多用图表/表格/图片承载信息。
4. **演讲备注**：`slide.notes_text_frame.text = ...` 写入备注，满足"带讲稿"需求。
5. **冷色调浅色背景**：页底色用浅蓝/浅紫渐变，正文深藏蓝，强调色青/紫/琥珀。
