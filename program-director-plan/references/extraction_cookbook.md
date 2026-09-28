# 材料提取与转换配方（已验证·Windows 环境）

> 培养方案材料常是 .doc/.docx/.pdf 混排，先统一提取为纯文本再分析。本环境无 pandoc，以下为 python-docx + Word COM + pymupdf 的已验证路径。

## 0. 环境（managed Python，隔离、不污染系统）

```
PY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python"
# 首次：建 venv 并装包
"$PY" -m venv C:/Users/Administrator/.workbuddy/binaries/python/envs/default
"$PY" -m pip install python-docx pymupdf
```

## 1. .docx 提取（最稳）

```python
from docx import Document
def extract(path):
    d = Document(path)
    out = [p.text for p in d.paragraphs if p.text.strip()]
    for t in d.tables:
        for row in t.rows:
            out.append(" | ".join(c.text.strip() for c in row.cells))
    return "\n".join(out)
```

## 2. .doc 提取（无 docx 接口 → 走 Word COM）

PowerShell 调 Word 另存为 .docx（wdFormat=16），再走 §1：

```powershell
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open("C:\abs\path\file.doc")
$doc.SaveAs("C:\abs\path\file.docx", 16)   # 16 = wdFormatDocumentDefault(.docx)
$doc.Close(); $word.Quit()
```

> 坑：路径必须绝对、用反斜杠；Word 须已安装。pywin32 在本环境有噪声（pywin32_bootstrap 缺失）但 python-docx 提取不受影响，可忽略报错。

## 3. .pdf 提取

```python
import fitz  # pymupdf
def pdf_text(path):
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)
```

## 4. Markdown → Word（保留表格/图片）

- 用本技能 `scripts/md_to_docx.py`：解析标题/引用/水平线/GFM 表格(边框+表头底纹+对齐)/有序无序列表(含嵌套)/行内加粗与代码，并嵌入图片。
- **图片处理**：md 内 `![...](...)` 自动嵌入；若是独立 SVG 大图，先转 PNG 再作为"附图"嵌入：
  - SVG→PNG（本环境无 cairosvg/rlPyCairo，用 Chrome 无头截图最稳）：
    ```
    chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars ^
           --screenshot="C:\abs\out.png" --window-size=W,H "file:///c:/abs/x.svg"
    ```
    输出路径用 Windows 反斜杠绝对路径（Unix 风格会写不进）。尺寸取 SVG 根标签 `width/height`。
  - 也可 `python-docx` 的 `run.add_picture(path, width=Inches(6.0))` 嵌入 PNG。

## 5. 通用坑

- 相对路径易踩（`Package not found`）→ 一律用绝对路径。
- 中文路径在 URL/命令行里优先复制到 ASCII 临时目录（如 `C:\tmp\`）再处理。
- 大文件提取后先 `grep` 关键信息（课程名/学期/章节）再精读，省 token。
- SVG 写标签属性时只能用合法 XML（`font-weight="bold"`），**禁止**写 CSS 写法 `font-weight:bold;`（会触发 "Unexpected token inside qualified name" 导致整页打不开）。生成后务必用 `xml.dom.minidom.parse()` 逐张校验。
