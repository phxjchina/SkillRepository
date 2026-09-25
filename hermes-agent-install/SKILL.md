---
name: hermes-agent-install
description: Install NousResearch/hermes-agent locally on Windows (esp. China network) when GitHub git clone is blocked. Covers ZIP-method install, the Python 3.11-3.13 (NOT 3.14) constraint, venv rebuild gotcha, pyproject.toml cwd requirement, and choosing a free model provider (Ollama local / Kimi free tier) instead of the payment prompt.
---

# Hermes Agent 本地安装（国内 Windows 网络）

## When to use
User wants to install `NousResearch/hermes-agent` (open-source autonomous AI agent) locally;
`git clone` fails although the browser reaches GitHub; or hits Python version / venv / provider-payment issues during install.

## Key facts
- Repo: https://github.com/NousResearch/hermes-agent
- Python: requires `>=3.11,<3.14` → use 3.11 / 3.12 / 3.13. **3.14 is rejected.**
- Native Windows support is experimental → prefer WSL2.
- Hermes itself is free/open-source. Any "payment" page comes from the chosen cloud model provider (Nous Portal / OpenRouter / Kimi), NOT Hermes.

## Install (ZIP method — works when git clone is blocked)
1. Browser download ZIP: https://github.com/NousResearch/hermes-agent
   (mirror if slow: https://ghproxy.net/https://github.com/NousResearch/hermes-agent/archive/refs/heads/main.zip)
2. Extract so `pyproject.toml` sits DIRECTLY in the project root (e.g. `D:\hermes-agent\pyproject.toml`).
   Flatten the inner `hermes-agent-main` folder if the ZIP nested it one level deep.
3. Install Python 3.13 from python.org, check "py launcher" + "Add to PATH".
4. Build venv with the RIGHT python and install:
   ```cmd
   cd /d D:\hermes-agent
   py -3.13 -m venv venv
   venv\Scripts\activate
   python -m pip install --upgrade pip
   pip install -e .          REM or: pip install -e ".[all]"
   ```

## Gotchas (the ones that actually bite)
- **venv caches the Python version at creation time.** If `pip install` reports
  `requires a different Python: 3.14.6 not in '<3.14,>=3.11'`, the activated venv is a
  STALE 3.14 one. Fix: `rmdir /s /q venv` then recreate with `py -3.13 -m venv venv`.
  Re-running `pip install` alone does NOT change the version.
- **cwd must contain pyproject.toml.** `pip install -e .` uses the current directory;
  running from the home dir gives "neither 'setup.py' nor 'pyproject.toml' found".
  In cmd use `cd /d D:\hermes-agent` (the `/d` switches drive).
- **`py -3.13` → "No suitable Python runtime found"** means 3.13 is not installed/registered.
  Install it, then OPEN A NEW terminal so the `py` launcher refreshes.
- Mirror for clone if they later want submodules too:
  `git config --global url."https://ghproxy.net/https://github.com/".insteadOf "https://github.com/"`
- **Large AGENTS.md truncation warning:** Hermes auto-loads `AGENTS.md` from its CWD as agent
  context. The hermes-agent repo ships an ~80K-char `AGENTS.md` (dev guide) that triggers
  `Context file AGENTS.md TRUNCATED: ... exceeds limit of 20000`. Harmless but noisy and wastes
  context. Fix for END USERS (not developing Hermes): rename it, e.g.
  `mv D:\hermes-agent\AGENTS.md D:\hermes-agent\AGENTS.md.bak`. The warning disappears next launch.

## Helper scripts (Windows .bat — keep ASCII-only to avoid Chinese mojibake in cmd)
- install_hermes.bat: auto-detects `py -3.13/3.12/3.11`, builds venv, installs.
  Uses `cd /d "%~dp0"` so it runs from its own folder regardless of where double-clicked.
- run_hermes.bat: `cd /d "%~dp0"` → `call venv\Scripts\activate.bat` → `hermes %*`
  (passes args through, e.g. `run_hermes.bat doctor`). Double-click to launch interactive.
- hermes_cmd.bat: same venv bootstrap, but semantically the "run any subcommand" entry.
  `hermes_cmd.bat setup` | `hermes_cmd.bat doctor` | `hermes_cmd.bat --version`.
  No-arg → launches interactive hermes. Use this when you would otherwise type `hermes <subcmd>`.

## Choosing a model (avoid the payment prompt)
The setup wizard (`hermes setup` / `hermes model`) opens a provider signup/checkout page
for cloud models — that is the PROVIDER billing, not Hermes. Close it; nothing is charged
unless card details are entered. Free options:
- **Local Ollama (free, offline):** install Ollama, `ollama pull qwen2.5:7b` (or 3b/8b/14b by RAM),
  then select Local/Ollama in Hermes. Best when no payment wanted and the machine is capable.
- **Kimi free tier (CN-friendly):** register at kimi.moonshot.cn, get a free API key, paste it.
  Stable in China, strong Chinese.
- **Bonsai-27B (1-bit, fits 8G VRAM):** `ollama pull MobiusDevelopment/Bonsai-27B-Q1_0-gguf`
  (~4.4GB, fits fully in 8G VRAM at full GPU speed — 27B-class reasoning at 7B memory cost).
  Best default for a machine with 8G VRAM + 32G RAM. Quality ~90% of full (long-tail facts slightly fuzzier).
  **Hermes 64K context gotcha:** Hermes Agent REFUSES to start if the model's `context_length` < 64K.
  The setup wizard lets you type a small value (e.g. 8192) to save VRAM, but that triggers
  `Model ... has a context window of 8,192 tokens, which is below the minimum 64,000 required`.
  Fix: set `context_length: 65536` under `custom_providers[].models[<name>]` in
  `%LOCALAPPDATA%\hermes\config.yaml` (this is what Hermes checks). For end-to-end length,
  also raise the Ollama model's `num_ctx` to 65536 via a Modelfile
  (`PARAMETER num_ctx 65536` then `ollama create`). Do NOT use 262K — its KV cache (~52GB) overflows
  RAM. 65K KV is ~13GB; 8G VRAM offloads part to RAM (slower but 32G RAM runs it fine).

  **Rebuild WITHOUT re-downloading:** do NOT `ollama rm` the model first. If you `rm` then
  `ollama create` with `FROM <registry-tag>`, Ollama re-pulls the weights (rm dropped the local
  manifest). Correct flow (reuses the local blob, no re-download), keeping the original model name:
  ```
  ollama create bonsai-64k -f Modelfile      REM FROM MobiusDevelopment/Bonsai-27B-Q1_0-gguf (old tag still present → reuses blob)
  ollama rm MobiusDevelopment/Bonsai-27B-Q1_0-gguf
  ollama create MobiusDevelopment/Bonsai-27B-Q1_0-gguf -f Modelfile   REM FROM bonsai-64k (local blob, no download)
  ollama rm bonsai-64k
  ```
  Model name unchanged → Hermes config needs no edit. Same pattern for qwen/etc.

  **CRITICAL — BOTH must be ≥64K, and the OLLAMA RUNTIME one is what Hermes enforces.** Hermes
  queries the model's ACTUAL loaded num_ctx via the Ollama API, not just config.context_length.
  A default 8192 window 400-errors immediately (`request (N tokens) exceeds the available context
  size (8192 tokens)`). Setting config.context_length: 65536 alone is NOT enough — Hermes still
  refuses with `Ollama runtime context is too small for Hermes tool use ... needs at least 64,000`.
  You MUST rebuild the Ollama model with `PARAMETER num_ctx 65536`. Trade-off: at 65K the KV cache
  is ~13GB, which 8G VRAM cannot hold, so Ollama offloads part to RAM — slower than pure-GPU but
  32G RAM runs it fine (short chats stay fast; only long sessions slow down). 262K (~52GB) overflows
  RAM too — avoid. Renaming the repo's large AGENTS.md to .bak shrinks the prompt but does NOT
  remove the need for a 64K num_ctx.

  **Gotcha — same-named rebuild still shows OLD num_ctx to Hermes.** Ollama caches the loaded
  model instance in RAM; renaming + recreating the same tag does NOT reload it, so Hermes probes
  the stale 32K instance and refuses. Fix: `ollama stop <model>` to unload, then restart Hermes so
  it reloads at the new 64K. Belt-and-suspenders: also add `ollama_num_ctx: 65536` under the model
  entry in config.yaml (Hermes enforces this field and names it in the error message).

## Verify
`hermes --version` → should print the installed version (observed: 0.20.0).
