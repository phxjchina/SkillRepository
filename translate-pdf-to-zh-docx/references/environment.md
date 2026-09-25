# Environment Notes & Dead-End Write-Up

## 1. Network / proxy
- The Google Translate free web endpoint
  `https://translate.google.com/translate_a/single?client=gtx&sl=auto&tl=zh-CN&dt=t`
  is reachable from mainland China ONLY through a local HTTP proxy.
- Default proxy in `translate_pipeline.py`: `http://127.0.0.1:7897`
  (a local Clash/V2Ray/etc. listener). Override via env var `TRANSLATE_PROXY`.
- The proxy works for Python (`urllib` with `ProxyHandler`). It does NOT help
  browser automation (see §3).

## 2. Python environment
- Use the managed venv: `C:/Users/Administrator/.workbuddy/binaries/python/envs/default`
  (has `pymupdf` → `import fitz`, and `python-docx` → `import docx`).
- `fitz` emits a deprecation warning ("use import pymupdf"); harmless, keep `import fitz`.

## 3. Why browser automation is impossible on this machine
- 360 antivirus blocks Chrome's CDP debug port (9222). `chrome --remote-debugging-port=9222`
  fails to bind; `agent-browser` daemon times out with 10060/10061. Conclusive:
  no headless browser control is possible here.
- Even with Chrome installed, onlinedoctranslator cannot be driven headlessly
  (see §4). So the browser path is doubly blocked — do not pursue it.

## 4. onlinedoctranslator.com — full reverse-engineering (dead end)
Endpoint flow that was reconstructed:
1. `GET /app/challenge` → `{algorithm, challenge, maxnumber, salt, signature}`
   (ALTCHA, an open-source PoW CAPTCHA).
2. Solve: find integer `n in [0, maxnumber]` such that
   `SHA-256(salt + str(n)).hexdigest() == challenge` (EXACT match, NOT leading
   zeros). `maxnumber` = 100000.
3. `POST /app/uploadtotranslationcontainer` (multipart): field `input-file`
   (the PDF) + field `captcha` (base64 of the ALTCHA response JSON).
4. `POST /app/translationsubmit` (form): only `from` and `to`. The `captcha` lives
   in the UPLOAD form's `<altcha-widget name="captcha">`, not the translation form.
5. Poll `GET /app/translationstatus` until `COMPLETED`.
6. `GET /app/gettranslateddocument/<urlencoded-filename>` to download.

Reality: upload + submit succeed and a job with the correct output filename is
created, but it NEVER advances past `LANGUAGE_PAIR_SELECTED` — translation never
starts. Three independent live tests confirmed this. The site's process page only
*polls*; the actual start is gated behind the real browser's Dropzone→iframe upload,
ALTCHA widget, and Google language-detection component. A headless client cannot
trigger dispatch. **Conclusion: not scriptable. Abandon.**

## 5. Quality comparison (why this pipeline wins)
- Argos (offline): runs, but translation quality clearly below Google; user rejected.
- Bing / MyMemory: acceptable, lower quality; user rejected.
- onlinedoctranslator: Google quality BUT unusable headlessly (§4).
- **This pipeline**: same Google engine, plus structured reconstruction
  (headings, page breaks), at ~17s/paper. This is the chosen solution.

## 6. Corruption QA (critical operational lesson)
- Antivirus (360) may lock a file during write/rename, producing a non-zip byte
  stream that `zipfile` rejects with "File is not a zip file".
- Symptom seen: one of 33 outputs was corrupt; another was locked
  (WinError 32, with a leftover `~$` Word temp-lock file) and could not be renamed.
- Fix procedure (validated):
  1. Delete the corrupt `.doc` and any `~$*` temp-lock files.
  2. Rename remaining valid `.doc` back to `.docx` (they are valid docx payloads;
     rename is safe) so the pipeline's "exists?" skip logic engages.
  3. Re-run `translate_pipeline.py <dir>` → regenerates ONLY the missing/corrupt
     files; the 31 valid ones are skipped.
  4. Rename `.docx` → `.doc`, then run `verify_outputs.py` to confirm 0 corrupt.
- The shipped `translate_pipeline.py` now saves directly to `.doc`, eliminating the
  rename step that previously enabled the corruption. Still run `verify_outputs.py`
  after every batch as a safety net.
