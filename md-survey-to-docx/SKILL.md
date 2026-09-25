---
name: md-survey-to-docx
description: 把学术 Markdown 稿件（综述/论文）转成 Word(.docx)，并把 `[论文标题]` 式内联引用统一换成 GB/T 7714 顺序编码制的数字上角标（如 [6]），自动校验引用与参考文献编号一一对应。当用户要求「md 转 word」「综述转 docx」「引用改成数字上角标」「参考文献编号化」时使用。
agent_created: true
---

# Markdown 学术稿 → Word（数字上角标引用）

把带 `[Paper Title]` 内联引用的 Markdown 综述，转成排版规范的 `.docx`，引用改为国标数字上角标。

## 适用前提

源 Markdown 需满足：

1. 文末有 `## 参考文献` 小节，条目格式为 `N. 论文标题 — 出处`（破折号为 `—`）。
2. 正文引用为下列任一形式（脚本两种都认）：
   - `` [`Paper Title`] ``
   - `` `[Paper Title]` ``
3. 引用标题与参考文献标题基本一致（脚本做归一化匹配，忽略大小写/标点/空格）。

## 工作流

### 1. 准备环境

本机通常没有 pandoc，且 pandoc 对中文字体与上角标控制粗糙。**用 python-docx 自建转换器**：

```bash
PYENV="C:/Users/Administrator/.workbuddy/binaries/python/envs/default"
"C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe" -m venv "$PYENV"   # 若不存在
"$PYENV/Scripts/pip.exe" install --quiet python-docx
```

### 2. 改脚本头部路径并运行

`scripts/md2docx.py` 顶部有 `BASE / SRC / OUT_MD / OUT_DOCX` 四个常量，改成目标路径后：

```bash
"$PYENV/Scripts/python.exe" scripts/md2docx.py
```

### 3. 核对输出日志（必做）

脚本会打印：

```
[refs] parsed N references
[scan] backticked citations: X, plain-bracket candidates: Y
[ok] every citation title matches a numbered reference     # 或列出 UNMATCHED
[cite] distinct references cited in body: A / N
[warn] references never cited inline: [...]                # 有孤立编号才出现
```

**验收标准**：无 UNMATCHED、无 never-cited 警告、`A == N`。
不达标就回去修正标题拼写或补引用，不要直接交付。

### 4. 抽查行文

转换后打开 `main_numbered.md`，grep `^[`，确认句子通顺（尤其列表项）。

## 关键实现要点

- **引用位置语义**：引用若紧跟在 `：` 之后充当句子主语，直接替换会产出「：[6] 提出…」的病句。脚本自动补「文献」二字 → 「文献[6]提出…」。引用在句中/句尾则直接贴上标并吃掉前置空格。
- **示例引用要先豁免**：文首「引用格式说明」里若举了 `` `[Some Title]` `` 做例子，必须在批量替换**之前**改写该句，否则会被当成真引用替换掉。这是最容易踩的坑。
- **中英文混排字体**：python-docx 只设 `run.font.name` 对中文无效，必须同时设 `w:eastAsia`：

  ```python
  rf = run._element.get_or_add_rPr().get_or_add_rFonts()
  rf.set(qn('w:ascii'), 'Times New Roman')
  rf.set(qn('w:hAnsi'), 'Times New Roman')
  rf.set(qn('w:eastAsia'), '宋体')
  ```

- **上角标**：`run.font.superscript = True`，整个 `[6]` 作为一个 run。
- **排版默认值**：A4、左右边距 3cm、正文小四 1.5 倍行距首行缩进 2 字符、`##` 黑体 15pt、`###` 黑体 13pt、参考文献 10.5pt 悬挂缩进 1.15cm。

## 产物

- `<原名>_numbered.md` —— 数字上角标版，便于人工核查
- `<标题>.docx` —— 交付物
- 原 `main.md` 保持不动（标题式引用可追溯，便于再次校验）

## 校验完成后

用 `present_files` 把 `.docx` 呈现给用户。
