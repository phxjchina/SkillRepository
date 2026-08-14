---
name: translate-pdf-to-zh-docx
description: "Translates English or other-language academic PDF papers into structured Chinese Word documents, preserving section headings, figures, tables and equations, at Google-Translate quality. Use this skill when a user asks to translate one or many papers or PDFs into Chinese Word (.docx), batch-translate a folder of academic PDFs, or needs a reliable translation pipeline that works behind China network restrictions where onlinedoctranslator, Bing, or MyMemory quality or availability is poor, or where antivirus (360) blocks browser automation. Provides a self-contained pipeline: PyMuPDF text/layout/figure/table/math extraction, Google Translate free web endpoint via local proxy, and python-docx reconstruction. Documents known dead-ends (onlinedoctranslator headless limitation, 360 blocking Chrome CDP) so they are not repeated."
agent_created: true
---

# Translate PDF → Chinese Word (.docx)

## Purpose
Translate academic PDFs into clean, structured Chinese Word documents at
Google-Translate quality. Output: `<basename>-翻译.docx` (true Office Open XML)
next to each source PDF. The pipeline produces
readable academic formatting: real heading hierarchy, figures embedded in
reading order, tables translated into real Word tables, display equations
rendered as clean images, page-number/header/footer garbage stripped, proper
CJK fonts, first-line indent, 1.5 line spacing.

## When to use
- A user asks to translate one or many papers/PDFs into Chinese Word.
- A user complains about messy earlier translation (broken paragraphs,
  headers/footers mixed into body, garbled tables, deformed formulas) — this
  pipeline fixes all four.
- NOT for: scanned PDFs without a text layer (run OCR first), or when a literal
  legacy `.doc` binary format is required (python-docx can only write .docx; a true
  binary `.doc` needs LibreOffice/Word conversion, out of scope).

## Workflow
1. Confirm environment: Python 3.10+ with `pymupdf` (import fitz) and `python-docx`.
   Use the managed venv. A local HTTP proxy is REQUIRED for the Google endpoint
   from mainland China (default `http://127.0.0.1:7897`; override with env var
   `TRANSLATE_PROXY`).
2. Run the pipeline:
   `python scripts/translate_pipeline.py --force <pdf_or_dir> [more ...]`
   - Pass a single PDF or a directory (recurses; with `--force` it regenerates
     even existing `-翻译.docx`, otherwise skips them).
   - Translates each paper concurrently (12 workers). A 12-page paper ~2 min; a
     57-page math-heavy survey ~90s (display equations are rendered, not
     translated, which keeps it fast).
3. Validate outputs (mandatory — see QA):
   `python scripts/verify_outputs.py <dir>`
   Fix any corrupt/missing file by deleting the bad one and re-running the
   pipeline (it skips existing valid files and only regenerates the bad/missing).

## Core script (`scripts/translate_pipeline.py`, v5)
Extraction per page, then assembled in reading order:
- **Two-column reading order**: detects a central empty band and orders text
  blocks / tables / figures left-column-then-right-column, so a left-column
  paragraph is never broken by the right column.
- **Paragraph re-assembly BEFORE translation** (two rules, both on):
  1. *Cross-line sentence heal*: adjacent blocks where the previous one has no
     terminal punctuation and the next is a continuation (or the previous ends
     with `, ; — -`) are merged — heals cross-block and cross-page splits.
  2. *Same-paragraph merge (v5, fixes "one sentence per line")*: consecutive
     **body** blocks on the SAME page + SAME column with only a normal line gap
     between them (`-2 ≤ gap ≤ fontsize×1.6`, no blank line) are joined into one
     paragraph. This is what fixes Chinese/dual-language journals (e.g.
     Intelligent_Vehicle) that put one sentence per text block. Headings, list
     items, and section-number starts are never merged.
- **Figures**: every embedded raster image is cropped from its real page
  position (`page.get_image_info`) and embedded centered in reading order
  (tiny decorations <12pt skipped).
- **Tables**: cells are extracted with `find_tables().extract()`; each cell is
  translated and rebuilt as a **real Word table** (Table Grid, 9pt CJK). Only
  if extraction fails does it fall back to a cropped image.
- **Math formulas (v5, fixes two complaints)**:
  - *Display-equation detection is tightened*: a line is a standalone equation
    ONLY when it is **essentially all math** — no readable prose word (≥2 CJK
    chars OR a run of ≥3 ASCII letters) may appear in it. Mixed "text + formula"
    lines stay as translated text, so surrounding words are **never swept into
    the formula image**.
  - *Crop only the math spans' union*: when a line qualifies, only the union of
    its math-font spans is cropped (NOT the whole-line bbox) — a formula next to
    inline words is isolated correctly.
  - *Sizing (no oversized blocks)*: each formula is rendered at its **natural
    on-page width**, capped to ≤15 cm and **never upscaled** → short formulas
    stay small, wide ones shrink to fit, nothing deforms.
  - Inline math (variables inside a sentence) stays as translated text — it is
    cheap and usually readable; rendering every symbol would bloat the file and
    was the cause of 16-minute runs on math-heavy papers (VNN-COMP 113k
    symbols), so it is deliberately avoided. Inline-as-images is an opt-in.
- **Header/footer / running-head removal**: position bands (top<9% / bottom>93%
  of page), cross-page repeated text (≥3× = running head), explicit meta phrases
  ("Manuscript submitted", "Preprint", "©", "arXiv:", "doi:", "Published as a
  conference paper" …) and footnote markers (★ † ‡ * ¹ ² ³ ⋆) — including
  trailing markers on title/heading lines. Footnote/reference URLs are
  collected once under a "参考链接" appendix.
- **Headings**: detected by BOTH section-number pattern (e.g. `2.1 Background`)
  and font size (≥1.5× median → H1, ≥1.2× → H2). Enumerated *lists* (e.g.
  CRISP-DM "1. Business Understanding") are demoted to body. Multi-line titles
  are merged into one Title.
- Translates via
  `https://translate.google.com/translate_a/single?client=gtx&sl=auto&tl=zh-CN&dt=t`
  through the proxy, concurrently (12 workers).
- Body 宋体 + Times New Roman 11pt, first-line indent, 1.5 line spacing;
  headings 黑体 + Arial. Control characters stripped before writing.
- Saves to `.docx` (true docx; python-docx cannot write legacy `.doc` binary).

## Known dead-ends (DO NOT repeat)
- **onlinedoctranslator.com**: fully reverse-engineered but headless jobs never
  start (stuck at `LANGUAGE_PAIR_SELECTED`); needs a real browser flow. Abandon.
- **Browser automation (agent-browser / Chrome CDP)**: 360 antivirus blocks
  Chrome's debug port (9222). Do not attempt.
- **Argos (offline)**, **Bing**, **MyMemory**: lower quality; user rejected.
- **Old gtx format-preserving hack**: poor formatting. PyMuPDF+docx is the fix.
- **Rendering every math span as an image**: on math-heavy papers (100k+
  symbols, e.g. VNN-COMP) this explodes runtime and file size. Render only
  display-equation lines.

## QA / pitfalls
- **Always run `verify_outputs.py` after a batch.** Antivirus (360) may lock files
  during write → corrupt `.docx`. The verifier lists corrupt/missing; delete and
  re-run (regenerates only the bad/missing).
- Math-font detection MUST use the math *symbol* fonts (CMMI/CMSY/CMEX/STIX/…).
  Do NOT match bare `cm` — LaTeX body text is Computer Modern Roman (CMR) and
  would be falsely flagged as math. `_MATH_FONT` is tuned for this.
- Unicode escapes (`\u22C6`) inside a `r"..."` raw regex string are NOT
  interpreted — always use literal characters in regexes.
- Output is true `.docx`; opens cleanly in WPS/Word. A genuine legacy binary `.doc`
  needs a separate conversion (LibreOffice/Word), out of scope — do NOT name the
  output `.doc`, that only produces a mislabeled docx that Word refuses to open.
- Figures are embedded as images (not OCR'd); only display equations are
  screenshotted, inline math stays as text.
- **Translation needs the local proxy.** `gtranslate` tries Google Translate
  through `TRANSLATE_PROXY` (default http://127.0.0.1:7897). If that proxy is
  down it falls back to **MyMemory**, which is opened via a **direct no-proxy
  opener** (a system-wide `HTTPS_PROXY=127.0.0.1:7897` would otherwise also break
  MyMemory through the dead proxy). MyMemory only handles short segments
  (~500 chars/request) and has a small daily quota — OK for a quick layout
  check, **NOT** for a 33-paper batch. Keep the proxy client (Clash/…) running.
  If a batch dies mid-way, just re-run with `--force`; it skips existing valid
  files and only regenerates the missing/corrupt ones.
- **Venv can be wiped between sessions.** If `import fitz` fails, reinstall in
  the managed venv via a China mirror:
  `pip install -i https://mirrors.aliyun.com/pypi/simple/ pymupdf python-docx`
  (PyPI mirrors `mirrors.aliyun.com` / `pypi.tuna.tsinghua.edu.cn` are reachable
  **directly**, no proxy needed).

## Changelog
- **v5** (this version): fixed two recurring complaints.
  - *Formula screenshots*: tightened display-equation detection (a line with any
    readable prose word is no longer treated as an equation), crop only the
    math-span union (not the whole line), and size each formula to its natural
    width capped at 15 cm (never upscaled) — eliminates oversized/deformed
    formula blocks and the "whole line of text captured into the equation image"
    bug.
  - *Segmentation*: added same-paragraph merge (same page + same column + normal
    line gap) so bilingual/Chinese journals that emit one sentence per text block
    no longer come out one-sentence-per-line.
  - Added MyMemory no-proxy fallback so the pipeline still runs (layout-wise)
    when the Google proxy is offline.
- **v4**: two-column reading order, table→real-Word-table translation, display
  equations as images, header/footer/footnote stripping, font split
  (宋体+Times New Roman), 4-fold chrome removal.
- **v3 and earlier**: initial PyMuPDF + Google-Translate + python-docx pipeline;
  fixed format/segmentation/header-pollution issues.

## References
- `references/environment.md` — environment notes, proxy config, the
  onlinedoctranslator reverse-engineering dead-end write-up.
- `scripts/verify_outputs.py` — post-batch QA: reports corrupt/missing/zero-
  translation files across a directory of `-翻译.docx` outputs.
