---
name: ima-kb-rename-table
description: 为 ima 知识库（无重命名 API）或本地磁盘 PDF/Word 批量提取论文/报告标题，生成「原文件名 → 建议改名」对照表；本地文件可进一步落地真实改名（带可回退日志）。覆盖递归列举、内容抽取、打分/版面定位标题、符号清洗、各类误抓护栏、同名配对、交付物生成、诊断量化、原地改名全流程。
version: 2.0.0
description_zh: "批量提取 PDF/Word 论文标题 → 生成改名对照表；本地文件可落地真实改名（可回退）"
description_en: "Extract paper titles from PDF/Word to build a rename mapping; local files can be physically renamed with rollback log"
agent_created: true
visibility: private
---

# 批量改名对照表生成（ima 知识库 / 本地磁盘）

## 一、适用范围与铁律

| 目标 | 能力 | 铁律 |
|---|---|---|
| **ima 知识库** | 只能生成「建议改名对照表」 | ⛔ ima **无重命名 API**，交付物只能是表，由用户按列手动改名。绝不要假装能自动改。 |
| **本地磁盘 PDF/Word** | 可生成表 + **真实原地改名** | 改名前必须生成 `rename_log` + `revert.py`，原地改、不复制整棵树、可一键回退。 |

- 主表 5 列：`子文件夹路径 | 原文件名 | 建议改名(论文标题) | 置信度(高/中/低) | 备注`
- 用户最常要 2 列版：`原文件名 | 建议改名`。

## 二、何时使用

触发词：知识库改名、PDF/Word 重命名对照表、提取论文标题、批量整理文件名、把文件名变成论文标题、本地文件批量改名。

## 三、执行模式（彭老师决策三原则，必守）

> 今天（2026-08-13）实战验证：6229 文件规模下，先试点审表再全量，能避免一次性把错误名烘焙进几千个文件。

1. **试点 → 审表 → 全量**：先挑 1–2 个有代表性的子文件夹（约 650 文件）跑通管线，出对照表给用户审；用户确认无误后再扩到全量。
2. **先审表再改名**：任何真实改名动作前，先把对照表（HTML 可筛选）交用户复核；用户的反馈（如"正文当标题""中文文件名误判"）要回流成护栏再重跑。
3. **可回退、不复制整树**：原地改名 + `rename_log` + `revert.py`；不复制整棵目录，磁盘空间与风险都最低。

## 四、环境与前置

- **Python（managed 优先）**：`C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe`
- **隔离 venv**：`python.exe -m venv C:/Users/Administrator/.workbuddy/binaries/python/envs/default`，在其中 `pip install pdfminer.six python-docx openpyxl`。
- **CSV 一律 utf-8-sig 读写**（Excel 中文不乱码）。
- **ima 读取走 connector-proxy**：直接调 ima OpenAPI 会报 `220004 invalid knowledge_base_id`，必须改用 `mcp__connector-proxy__*` 或 `mcp__ima-mcp__*`。

## 五、工作目录与脚本清单

工作目录（例）：`E:\科研\.workbuddy\rename_table\`，子目录 `json/ content/ deliverables/ logs/`。
完整管线 8 脚本：

| 脚本 | 职责 |
|---|---|
| `build_index.py` | 递归列举全部 PDF/Word，输出 `json/_index.json`，键 `(rel_dir, filename)` 唯一 |
| `extract_titles.py` | 两层候选 + 护栏 + PDF↔DOCX 配对，输出 `json/_titles.json` |
| `clean_rename.py` | 修复章节文物、同名消歧（按扩展名）、空名兜底、标记类退回，输出 `json/_table.json` |
| `gen_deliverables.py` | 生成 CSV/HTML/XLSX + 完整校验 |
| `analyze.py` / `diag*.py` | **诊断量化**（见 §十），非交付必备 |
| `do_rename.py` | 读 `_table.json` 真实改名 + 写 `rename_log` + 长路径/碰撞保护 |
| `revert.py` | 读 `rename_log` 一键还原 |
| `list_not_renamed.py` | 导出未改名清单（保留原名的 + 真冲突跳过的） |

## 六、阶段 1 — 递归列举（build_index.py）

- 本地：`os.walk(root)`，**务必排除 `.workbuddy` 自身目录**（否则把工作区缓存扫进去）。支持 `--all` 全量开关（试点时限定子文件夹）。
- 输出每条：`rel_dir / filename / ext / key=(rel_dir, filename)`。
- 这是后续所有回写的**唯一可靠键**：绝不用裸文件名（否则 `FULLTEXT01.pdf` 在不同子文件夹下会张冠李戴）。
- ima 变体：`folder_id` 必须带 `folder_` 前缀；分页 `limit ≤ 50`；输出 `path/filename/media_type/introduction/media_id`。

## 七、阶段 2 — 抽取标题（extract_titles.py，核心）

### 7.1 两层候选
1. **文件名即标题（高置信）**：仅当 `looks_like_title_filename(base)` 为真才直接用文件名（见 7.2）。
2. **内容提取（中置信）**：否则读文件内部抽标题（PDF 版面 / DOCX 字号）。
3. **fallback（低置信）**：内容抽不出 → 保留原名待人工，**绝不拿碎片当新名**。

### 7.2 `looks_like_title_filename`（关键护栏，dlcontract 教训）
> 中文文件名（如 `dlcontract--深度学习契约.pdf`）**一律不当标题**，强制内容提取——否则会把"文件名"误判成"论文名"。
返回 False（强制内容提取）的情形：
- 含中文（HAN_RE）→ 几乎都不是规范英文标题
- 首字母小写（可能是从词中间截断）
- 末尾数字编号 `[_- ]\d{1,3}$`
- 期刊卷期 `_v\d / _i\d / _p\d`
- 全大写缩写+数字 `^[A-Z]{2,}\d`
- 词数 < 3 或长度不在 12–160
仅**规范英文标题**（不含中文、首字母大写、长度词数达标、无编号卷期）才直接用文件名作候选。

### 7.3 PDF 抽取（extract_pdf / title_from_lines）
- 先 `pdf_meta_title`（元数据），再 `title_from_lines`（版面：按字号+位置定位标题块）。
- `title_from_lines` 要点：取首页顶部、字号 ≥ `0.62*maxfs` 的连续行；多行合并（主+副标题）；**遇作者/单位/年份行即收尾**（作者检测忽略 `(cid)` 字形残片，且姓名列表严格到"每段 名 姓"才认，避免把带逗号的标题 "Deductive Verification, the Inductive Way" 误判作者）；跳过 GitHub/中文网页噪声明行。
- 单字碎片不回退纯文本（损坏页眉不稳定）。

### 7.4 DOCX 抽取（extract_docx）
- 先 `core_properties.title`，但**拦截 META_JUNK**（如 "PowerPoint Presentation"）不用。
- 否则按段落字号 `_para_size` 定位标题块；遇 `SECTION_RE`（章节号）/ `NUMBERED_RE`（编号列表）/ `AUTHORISH`（作者署名）截断；多行合并。

### 7.5 护栏集（process 阶段串接）
- `clean_text()`：连字归一化(fi→fi)、去控制符/中点、剔除 `(cid:NN)` 字形残片、截断 `$/✉/▶/http` 残片。
- `strip_template()`：模板前缀 `Noname manuscript No. (will be inserted by the editor)` 等 → **剥离后保留真标题**，不要整条丢弃。
- `looks_truncated()` 末词截断检测：**白名单常见短词** `so/of/to/in/on/by/is/as/at/or/an/it/up/we/he/no/go/do/be/me/my…`；**中文(CJK)标题整体跳过**（中文无拉丁元音，否则误判截断）；末词纯数字（年份）不算碎片。
- `NON_TITLE_EXACT` 短名单：整串命中 "contributed articles / Information and Software Technology / editorial / abstract…" 直接丢弃。
- `looks_like_body_text()` 正文/网页文本拦截（高发误抓，见 §十二.A）。
- 小写开头项目名（alpha-beta-CROWN、zkCNN、iSAT）→ 保留（标"中"请复核），不一刀切丢。
- 含大写/数字/`+` 的（ThingML+、iSAT）视为缩写保留，不按"单字"丢弃。

### 7.6 PDF↔DOCX 同名配对
- Word 多由 PDF 转来，同 `(rel_dir, base)` 即同一篇不同格式。按组选**已成功抽取者（优先 .pdf）**作锚点，把锚点标题**统一应用到同组所有格式**（救回抽取失败的、并让成对文件同名）。
- 同名消歧**按扩展名区分** `(rel_dir, base, ext)`：`Title.pdf` 与 `Title.docx` 不同文件可共存，否则误加 `_2` 破坏配对。

## 八、阶段 3 — 清洗消歧（clean_rename.py）

- `repair()`：剥离章节文物（LEAD_SEC 正则须带 `\b` 词边界，否则 `^Abstract` 会把 "Abstraction" 截成 "ion based…"）、页脚、尾注。fallback 行跳过 repair（避免 `2021`→`2` 变形）。
- **同名消歧按扩展名**区分（见 7.6）。
- **空名兜底**：`repair()` 可能剥光成空 → `proposed_base=""` → 生成 `.pdf` 非法名。须 `if not base or len(base)<2: base=orig_base` 兜底。
- **不确定标记类退回**：`author-runon` / `trunc` 标记行 → `rename=False` 保留原名待人工，避免批量烘焙错误名。

## 九、阶段 4 — 交付物（gen_deliverables.py）

- `rename_table.csv`（5 列主表，utf-8-sig）
- `rename_table_2col.csv`（2 列）
- `rename_table.html`（文件夹折叠 / 搜索 / 按置信度筛选；高=绿底 中=黄底 低=红底）
- `rename_table.xlsx`（3 表：改名对照表 / 完整主表(色标) / 说明）
- **XLSX 写盘陷阱**：原始文件名/备注可能含 XML 非法字符（C1 控制区 `\x7f-\x9f`、NULL）→ 用白名单 `re.sub(r"[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]","",v)` 净化每个单元格字符串。
- 校验全绿：`blanks=0 / ctrl=0 / overlong(>220)=0 / 截断=0 / author-runon=0`。

## 十、诊断量化方法论（反复用，必做）

> 改护栏前先**量化**，用数据定位瓶颈，别靠猜。今天实战：先 `analyze.py` 看失败项分布，发现"失败 PDF 其实有文字"→ 再 `diag_pdf.py` 看是否有文字层 → 再抽查代表文件 → 再 debug 具体 bug。

- **`analyze.py`**：统计 高/中/低 分布、DOCX vs PDF 失败数、可同名配对救回数。
- **`diag_pdf.py`**：对失败 PDF，用 pdfminer 取首页文本，判断"真无文字层(扫描件)"还是"有文字被护栏误杀"。
- **`check_rescue.py` / `debugN.py`**：抽查代表文件的新旧抽取结果，定位具体 bug（正则、截断、作者行没收住等）。
- 量化结论驱动修复优先级（如：多数"失败"实为有文字被误杀 → 放宽护栏而非加 OCR）。

## 十一、阶段 5 — 执行改名（do_rename.py / revert.py / list_not_renamed.py）

- **Windows 260 字符路径上限是最大陷阱**：深层嵌套 + 长标题，完整路径易 >260，`os.rename` 报 `WinError 3`（实为超长）。**必须用 `\\?\` 扩展前缀**：
  `PREFIX="\\\\?\\"; lp=lambda p: PREFIX+os.path.abspath(p)`，对 `os.path.exists` 与两次 `os.rename` 都套 `lp()`。不加前缀 6229 文件中失败 ~84/4502。
- **临时名中转**：`src → src.renaming_tmp → dst`。任一步 `OSError` 立即把 tmp 还原回 src，**绝不破坏源文件**。绝不可直接 `src → dst`。
- **碰撞预检**：`os.path.exists(lp(dst))` 且不是 `src` 自身 → 跳过不覆盖（多为 `_2021` 副本、`.en.zh-CN` 翻译版与英文原版并列同名）。预检须排除"已在历史 rename_log 的 (src,dst)"，否则重跑会把已改名项误判冲突而漏记日志。
- **累积日志**：重跑时合并 `logs/rename_log.json` 历史 ok 条目（目标仍存在则结转），保证回滚日志始终完整。若因长路径补跑，务必先合并两次日志再重跑，否则 `rename_log.json` 只剩补跑的少数几条。
- **未改名清单**：`list_not_renamed.py` 从 `_table.json` + `logs/rename_log*.json` 反查：未改名 = `(rename=False)` ∪ `(rename=True 但 src 不在 log ok 集合)`。输出 `not_renamed.csv`（结构化）+ `not_renamed.txt`（纯列表）到工作区。
- 实战结果（6229 文件）：高 2324 / 中 3037 / 低 868；实际改名 **4489**，真冲突保留原名 13，失败 0。

## 十二、护栏与 Bug 模式库（踩坑必记）

### A. 正文/网页文本误当标题（高发，李仁素教训）
网页另存 PDF / 项目介绍页被抽成数百字"标题"。`looks_like_body_text()` 命中即**退回原名（低置信）**：
- 含中文句末标点 `。`/`；` → 必为正文段落（标题几乎不含）。
- 网页导航词 `首页/研究 教学/团队 论文发表/登录/网站/项目页面/当前项目/过去项目` 或英文 `current projects/project page/home research`。
- 论述标记 `我们的方法/本项目/本提案/该项目/本文提出/我们提出/旨在/开发了/相结合/正在招聘/this paper (presents|proposes)/we (propose|present|develop)/our (approach|method|framework)`（且整体 >30 字）。
- 超长（>100 字）且含 ≥3 个中文逗号 `，`。
- **注意**：长英文真实标题（如 "Towards Robust and Verified AI Specification Testing…"）虽长但无上述特征，必须保留，勿误伤。

### B. ima 三类残留（知识库 PDF 同样适用）
- **作者尾注 run-on**：`…Systems Roy Mendieta` → 截掉尾部作者名，已知作者名扫描须 0 残留。
- **真截断/正文垃圾**：末词合法性（剥年份后缀后查英文后缀/领域词/缩写白名单）+ 内部断词签名扫描（`speci/technolog/architectur…`）。**截断判定必须看完整标题**，80 字显示截断是伪影。
- **tag/出版商页脚文物**：`Systems2016`/`View project`/`Received:`/`DOI:`/`https://`。**子串误报排查**：`vat`⊂`innovation`、`table`⊂`adaptable`——命中后看完整标题确认，不一刀切删。

### C. 同名文件张冠李戴（致命）
`FULLTEXT01.pdf` / `document.pdf` 是不同子文件夹下的不同论文。任何回写都必须用 `(子文件夹路径, 文件名)` 精确键。

### D. 正则无词边界误杀（隐蔽）
`LEAD_SEC = ^Abstract` 无 `\b` 会把 "Abstraction" 截成 "ion based…"；`TRUNC_STEMS` 词干匹配会误杀 systems/networks/learning。一律用精确边界 + 短词白名单，不靠词干猜测。

### E. 中文文件名不误判（dlcontract 教训）
见 §7.2：中文文件名一律强制内容提取，绝不直接当标题。

## 十三、最终校验清单（交付前必跑）

```
INTEGRITY: TOTAL N | blanks 0 | orig==new 0 | ctrl 0 | overlong(>220) 0
JUNK: 出版商页脚/冗余词命中 → 0 真残留
AUTHOR-RUNON: 已知作者名扫描 → 0 残留
TRUNC: 末词合法 + 内部断词签名 → 0 真残留
BODY: 正文/网页误抓 → 0 残留
```
置信度分布记入说明表。

## 十四、彭老师偏好与决策记录

- **增量迭代**：基于样例反馈逐步补护栏（先试点小批 → 审表 → 提问题 → 修 → 重跑），不要一次想完美。
- **文件名不像标题 → 打开文件取真实标题**，而非保留原名蒙混（dlcontract、s10270 等）。
- **正文/网页误抓 → 全部退回原名**待人工，绝不烘焙错误名。
- **不确定就退回原名**：author-runon / trunc / 单字碎片等标记类一律 `rename=False`。
- **中文文件名不当标题**；长英文真实标题不被误伤。
- 称呼：彭老师；输出结构化、可溯源。

## 十五、经验教训速查

1. 标题提取核心 = **打分/版面定位**，不靠硬规则「必须含领域词」。
2. 同名去重铁律：**(子文件夹, 文件名)** 精确键。
3. 截断判定看**完整标题**，80 字显示截断是伪影。
4. 出版商关键词扫描必带**子串误报排查**（vat/table/citation）。
5. 修复逐批备份 `rename_table.pre_patchN.csv`，用 `norm()` 归一化（ﬂ→fl、'→'、–→-、小写）按 `norm(orig)` 精确匹配回写。
6. 中文文件名不误判标题；正文/网页误抓退回原名。
7. 本地改名：临时名中转 + `\\?\` 长路径 + 碰撞预检 + 累积 `rename_log` + `revert.py`。
8. **改护栏前先量化诊断**（analyze/diag），用数据定位瓶颈，别靠猜。
