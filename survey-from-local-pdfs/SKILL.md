---
name: survey-from-local-pdfs
description: >-
  Use when the user has a folder of downloaded academic PDFs and wants a
  Chinese systematic literature review (SLR) survey written from them as the
  ONLY citation source — no web retrieval, no hallucinated references. Triggers
  on "用这些论文写综述", "按系统文献综述范式写", "SLR 风格", or any request to
  synthesize a survey whose citations must map 1:1 to local PDFs.
---

# 本地 PDF 语料 → 系统文献综述（SLR）中文稿

把"一批本地下载的论文 PDF"当作唯一参考文献库，产出一篇**引用零幻觉**的中文
系统文献综述（SLR 范式）。适用于用户明确要求综述、且引用必须真实锚定已下载
文献、不可编造外部来源的场景。

## 何时用
- 用户有一批本地 PDF，要基于它们写综述，且**引用必须真实、可回溯到这些 PDF**。
- 用户要求"按系统文献综述（SLR）范式"写（研究问题、方法论、纳入/排除、数据表、
  效度威胁）——否则容易写成"粗线条随笔"。

## 工作流
1. **盘点语料**：用 PyMuPDF 读每个 PDF 首页，抽取标题/作者/年份/arXiv 号，建立
   结构化文献库。`scripts/extract_refs.py` 可一键生成 REFERENCES/STUDY 起始数组
   （best-effort，需人工补全作者/标题/分类）。
2. **多视角分析**（配合 `literature-review` 技能）：模拟 3–5 个专家视角
   （MDE / 形式化 / LLM-SE / 安全 RL / 系统工程）梳理主题、共性、分歧、研究空白。
3. **大纲**（配合 `survey-generation` 技能）：生成 SLR 结构——
   摘要 → 1 引言（背景/二次研究方法/问题陈述/贡献）→ 2 研究方法（RQ/来源与选择/
   纳入排除/质量评估/数据提取/流程）→ 3 执行 → 4 结果（文献计量 + 按 RQ 分析 +
   研究特征总表）→ 5 讨论（综合/启示/效度威胁）→ 6 结论 → 参考文献 →
   附录（研究特征总表）。
4. **分节撰写 + RAG 式写作**：每节只引用文献库中的论文，内联 `[n]` 上角标；
   量化数字（年度/类型/主题分布）由 STUDY 数组统计得出，可审计。
5. **引用校验**：脚本内置断言——所有 `[n]` 都有定义、所有文献至少被引一次
   （零悬空引用、零未引文献）。
6. **产出 docx**（用 python-docx，因无 TeX 环境且用户工作流是 Word）：真实
   Heading 1/2/3 样式、GB/T 7714 参考文献、研究特征总表。

## 脚本
- `scripts/survey_slr.py` — 完整可运行实现（示例：33 篇"机器学习元模型"论文）。
  `--out` 指定输出路径，默认复现用户原稿。包含内置引用校验。
- `scripts/extract_refs.py` — 对任意 PDF 文件夹生成 REFERENCES/STUDY 起始数组
  （best-effort 元数据抽取，需人工补全作者/标题/分类）。

## 关键经验（避坑）
- **零幻觉引用**：REFERENCES 必须来自本地 PDF 真实元数据；绝不调用网络检索补文献。
- **SLR 范式不能省的四块**：显式 RQ、方法论章节、研究特征总表、效度威胁；缺一则
  显得"粗"——这是用户明确点出的痛点。
- **量化数字要可审计**：分布表直接由 STUDY 数组统计，附录研究特征表逐篇可回溯。
- **中文 docx 标题用真实 Heading 样式**（非加粗普通段落），否则 Word 无导航大纲。
- **引用校验**：用正则 `\[(\d+)\]` 收集内联引用，与 `range(1, len(REFERENCES)+1)`
  比对并 `assert`；跑脚本时 stdout 会打印 used / defined / uncited，便于体检。

## 依赖
`pymupdf`、`python-docx`。若 venv 被清空，用阿里/清华 PyPI 镜像直连重装：
`pip install -i https://mirrors.aliyun.com/pypi/simple/ pymupdf python-docx`

## 示例
```bash
# 生成示例综述（33 篇 ML 元模型）
python scripts/survey_slr.py --out 机器学习元模型综述_SLR.docx

# 对任意 PDF 文件夹生成参考文献起始数组
python scripts/extract_refs.py "E:/科研/DSML+ML元建模" --out corpus_refs.py
```

## 与其他技能的关系
- `translate-pdf-to-zh-docx`：先把 PDF 翻译成中文稿，再据此写综述（可选前置）。
- `literature-review`：提供多视角专家对话的分析方法。
- `survey-generation`：提供大纲→分节撰写→引用校验的综述生成管线（本技能是其
  "纯本地语料、中文 docx 输出"的适配实现）。
