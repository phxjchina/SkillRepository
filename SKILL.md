---
name: ima-kb-rename-table
description: 为 ima 知识库（无重命名 API）下某一大类的 PDF 批量提取论文/报告标题，生成「原文件名 → 建议改名」对照表（CSV/XLSX/HTML）。覆盖递归列举、全文抓取、打分提取标题、符号清洗、作者尾注/截断/页脚垃圾修复、交付物生成全流程。
version: 1.0.0
description_zh: "为 ima 知识库批量 PDF 生成建议改名对照表（提取论文标题）"
description_en: "Generate a suggested-rename mapping table for batch PDFs in an ima knowledge base by extracting paper titles"
agent_created: true
visibility: private
---

# ima 知识库 PDF 批量改名对照表

## 一、目标与铁律

为 ima 知识库某一大类（如「科研库 / MBSE 大类」）下的**全部 PDF** 生成一份
「原文件名 → 建议改名（论文/报告标题）」对照表。

> ⛔ **ima 无重命名 API**。本技能交付物**只能是「建议改名对照表」**，由用户（彭老师）在 ima 里按列对照手动改名。
> 任何「自动重命名 ima 文件」的诉求都要先说清此限制，不要假装能改。

- 主表 5 列：`子文件夹路径 | 原文件名 | 建议改名(论文标题) | 置信度(高/中/低) | 备注`
- 用户最常要的是 2 列版：`原文件名 | 建议改名`。

## 二、何时使用

触发词：知识库改名、PDF 重命名对照表、ima 提取标题、批量整理 PDF 文件名、把知识库文件名变成论文标题。

## 三、环境与前置

- **Python**（managed，优先）：`C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe`
- **openpyxl** 在隔离包目录：`C:/Users/Administrator/.workbuddy/binaries/python/pkg`（导 xlsx 时 `sys.path.insert(0, 该路径)`）。
- **CSV 一律 utf-8-sig 读写**（Excel 打开中文不乱码）。
- **ima 读取走 connector-proxy**：直接调 ima OpenAPI 会报 `220004 invalid knowledge_base_id`，必须改用
  `mcp__connector-proxy__*` 或 `mcp__ima-mcp__*` 工具（URL / headers 从 `CODEBUDDY_MCP_CONFIG` 读，SSE 解析）。
  - 列举：`get_knowledge_list` / 递归列子文件夹 + `get_knowledge_list`（folder 级）。
  - 抓全文：`fetch_media_content`（拿到 SSE 流，解析出正文文本）。

## 四、全流程（8 阶段）

> 工作目录建议：`E:\...\练习用材料\.workbuddy\mbse_rename\`，所有中间产物、缓存都放这里。

### 阶段 1 — 递归列举整棵 KB 树

- `folder_id` **必须带 `folder_` 前缀**（如 `folder_7492938649073107`）。
- 分页 `limit ≤ 50`，循环直到 `is_end`。
- 输出 `json/_index.json`：每条含
  `path / filename / media_type / introduction / media_id / can_fetch_content`。
- 这是后续所有回写的**唯一可靠键**：用 `(子文件夹路径, 文件名)` 精确对，绝不用裸文件名（见铁律 §5）。

> **GBK 乱码修复**：代理返回的含重音文件名有时是 UTF-8 被当 GBK 解码的乱码（如 `S茅bastien`）。
> 还原：`s.encode('gbk').decode('utf-8')`；正常中文 UTF-8 该 round-trip 会抛异常，故 `try/except` 即可安全区分。

### 阶段 2 — 初拟候选标题（两层）

1. **文件名即标题**：文件名含中文 / 空格 / 明显英文标题词 → 直接作候选（高置信）。
2. **从 `introduction` 首页解析**：否则用首页文本，按下面的「打分提取」拿候选（中置信）。
   - 不要一上来就硬规则「必须含 MBSE/SysML 等领域词」——会漏掉无关键词的真实标题（法文 HAL、挪威论文）。

### 阶段 3 — 抓取全文缓存

- 对「文件名不像标题」或「首页解析失败」的子集，调 `fetch_media_content` 拉全文，
  存 `content/<media_id>.txt`（建议命名含 hash 防冲突）。
- 缓存是后续所有「重读修正」的依据——连接器中途可能离线，离线后只能对缓存做清洗。

### 阶段 4 — 打分提取标题（score-based ranking，核心）

候选源（按优先级合并打分，取最高分）：
- HAL `cite` 正则（`@inproceedings` / `title = {...}`）
- `before_marker`：期刊 DOI / `©` / "Received:" 上方几行（真正的标题常在这上面）
- heading 合并（去掉章节号 `17.`、图号 `Figure 1.` 后合并）
- `preabs`：Abstract 之前的标题区
- filename fallback

> **铁律**：用打分排序而非硬规则。候选标题要「语义完整」，但**避免把正文/作者/机构塞进来**。

### 阶段 5 — 符号清洗

- 在首个 `$`(LaTeX) / `✉`(邮件) / `▶`(箭头) 处**截断**。
- 移除制表符、控制符（`ord<32`）、方块符、上标 `¹²³`、中点 `·`、希腊字母、箭头等怪符号。
- 残留一般是「标题+作者挤一行」或「参考文献条目」，留到阶段 7 处理。

### 阶段 6 — 落盘 CSV（并列主表）

用 `(path, filename)` 精确键写回 5 列。UTF-8-sig。

### 阶段 7 — 校验与修复循环（最耗时，见 §五、§六）

- 作者尾注 run-on、截断、出版商页脚/冗余词、tag 文物、同名文件张冠李戴。
- 每修一批先 `cp rename_table.csv rename_table.pre_patchN.csv` 备份再改。

### 阶段 8 — 重生成交付物

```python
# regen_deliverables.py 骨架
import csv, sys
sys.path.insert(0, "C:/Users/Administrator/.workbuddy/binaries/python/pkg")
import openpyxl
rows = list(csv.reader(open('rename_table.csv', encoding='utf-8-sig', newline='')))
data = rows[1:]
# 1) 2col csv: [原文件名, 建议改名]
# 2) html: 折叠/搜索/按置信度筛选；高=绿底 中=黄底
# 3) xlsx: 三表 = 改名对照表(2列) / 完整主表(5列, 置信度色标) / 说明(含处理历程)
```

## 五、用户给的「四类分情况」修改框架（必读）

彭老师总结的修改思路，按问题归类处理：

| 类别 | 现象 | 正确处理 |
|---|---|---|
| ① 短名未读被误当第三类（怪符号类） | 文件名短又没读内部，直接拿原名当新名 | **打开全文**取真实标题，例 `06-jsw140301…` → 《A MDE-Based Approach to the Safety Verification of Extended SysML Activity Diagram》 |
| ② 标题后接大量文字 | 标题后跟了摘要/正文一大段 | **只保留标题本体**，例 `CCF-report-2019-2020` → 《人工智能系统的形式化验证技术研究进展与趋势》 |
| ③ 文件名本就是标题却被读成区块头 | `Cross-Platform…EMF.Cloud` 被当成 RESEARCH ARTICLE 区块 | 去掉下划线/连字符还原即论文名 |
| ④ 新名为空白 | 提取失败留空 | **重读全文**填充，例 `MBSE-SysML-First-Issue-V1` → 《MBSE, What is Wrong with SysML -First Issue. 2019》 |

> **总原则（用户原话）**：建议的新文件名必须是**语义完整的论文名称或报告名称**；
> 若不是，就**再次阅读该文件**提取完整标题；同时**避免把不必要的正文内容加进去**。

## 六、三类残留问题 & 修复手法

### A. 作者尾注 run-on（标题尾部粘作者名）

现象：`…Systems Roy Mendieta`、`…Ontologies Helna Wardhana`、`…Architecture Lattmann`。
- 检测：已知作者名集合 + 结尾「双大写词非领域名词」黑名单 + 末词英文后缀/词典判断。
- 修复：截掉尾部作者名（spaced 姓也要识别：Lattmann/Cardei/Parra/Bunting/Tang…）。
- 已知作者名扫描应 **0 残留** 才算过。

### B. 真截断 / 正文垃圾

- 真截断：`…discipline speci`、`1Motivationesa`、`Declaration of Competing Interest`。
- 诊断陷阱：`final_check.py` 的 **80 字符显示截断是伪影**——"Text Us" / "Diagr" 其实是完整标题被显示截断。**判定截断必须看完整标题**。
- 可靠检测：
  - 末词合法性：剥年份后缀（`-2019` 等）后，末词在 英文后缀表 / 领域词白名单 / 缩写词表 中 → 合法。
  - 内部断词签名扫描：`speci / technolog / concept / architectur / develop / implement / configur …` 等经典截断点，且不在标题末尾 → 真残留（应为 0）。
- 修复：回 `content/` 缓存或 `_index.json` 的 `introduction` 找回真实完整标题。

### C. tag / 出版商页脚文物

- 年份粘连：`Systems2016`、`Compatibilityr`、`Next-Gen IoT Systems-20201`。
- 缺括号、缺 ")"、`View project`、机构头（`TECHNISCHE UNIVERSITÄT MÜNCHEN` / `Lehrstuhl…`）、章节号、图注、参考文献条目。
- 出版商页脚垃圾（最隐蔽）：`Price includes VAT (Japan`、`© 20…`、`Available online`、`Received:`、`DOI:`、`https://`、`www.`、`.com/`。
  - 但注意**子串误报**：`vat`⊂`innovation`/`derivation`，`table`⊂`adaptable`，`citation`⊂某些词——命中后必须看完整标题确认，不要一刀切删。

### D. 同名文件张冠李戴（致命）

知识库里 `FULLTEXT01.pdf` / `document.pdf` / `download.pdf` 是**不同子文件夹下的不同论文**。
**任何按文件名回写 CSV 的逻辑都必须改用 `(子文件夹路径, 文件名)` 精确键**，否则会串台。

## 七、最终校验清单（交付前必跑）

```
INTEGRITY: TOTAL N | blanks 0 | orig==new 0 | ctrl 0 | overlong(>220) 0
JUNK: 出版商页脚/冗余词命中 → 0 真残留（误报须人工排除）
AUTHOR-RUNON: 已知作者名扫描 → 0 残留
TRUNC: 末词合法 + 内部断词签名 → 0 真残留
```
置信度分布（例：高 578 / 中 154 / 低 0）记入说明表。

## 八、交付物

- `rename_table.csv`（5 列主表）
- `rename_table_2col.csv`（用户要的两列）
- `rename_table.html`（可按文件夹折叠、搜索、按置信度筛选）
- `rename_table.xlsx`（3 表：改名对照表 / 完整主表 / 说明）

并明确告知用户：**ima 无重命名 API，需手动按表改名**。

## 九、经验教训速查

1. 标题提取核心 = **打分排序**，不要硬规则「必须含领域词」。
2. 同名文件去重铁律：**(子文件夹, 文件名)** 精确键。
3. 「截断」判定必须看**完整标题**，80 字显示截断是伪影。
4. 出版商关键词扫描必带**子串误报排查**（vat/table/citation）。
5. 修复逐批备份 `rename_table.pre_patchN.csv`，用 `norm()` 归一化（ﬂ→fl、'→'、–→-、小写）按 `norm(orig)` 精确匹配回写；中文/空格导致 `norm` 失配时改用 `if '关键字' in r[1]` 子串定位。
