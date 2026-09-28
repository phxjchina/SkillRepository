---
name: github-skill-repo-sync
description: 把本机 ~/.workbuddy/skills/ 下的技能同步（clone→复制→commit→push）到彭老师的 GitHub 技能仓库 phxjchina/SkillRepository。当用户说"同步到 github 技能仓库""推送技能""把技能上传到 SkillRepository""同步技能仓库""上传到 github"时使用。覆盖：ghproxy 只读镜像读取、直连 github.com 强制 IPv4、GCM 免 PAT 推送、临时副本损坏时的重建、PAT 权限排查，以及 github.com 被墙时改走 GitHub Data API 的增量推送兜底。
version: 1.2.0
author: 小布
agent_created: true
---

# GitHub 技能仓库同步（SkillRepository）

把本机新建/更新的技能目录同步到 `https://github.com/phxjchina/SkillRepository`（main 分支）。
本机环境：Windows + Git Bash；`~/.workbuddy/skills/` 是 WorkBuddy 安装目录，**不是**该仓库的 git checkout，**绝不能**直接在 skills 目录 `git push`。

## 适用信号
- "同步到 github 技能仓库" / "推送到 github" / "上传技能到 SkillRepository"
- 新增或更新了 `~/.workbuddy/skills/<skill>/` 想纳入版本管理

## 核心事实（本机实测；2026-09-27 主机重装后复测更新）

1. **ghproxy 只读**：`https://ghproxy.net/https://github.com/...` 只能读（clone/fetch），**不能 push**（报只读 / Invalid username or token）。
2. **本机有可用 HTTP 代理（首选）**：`127.0.0.1:7897`（Clash 系）。github.com 直连 443 在 2026-09-27 实测超时，但走代理 clone 仅 16 秒。**推荐 clone/push 全走代理**：`git -c http.proxy=http://127.0.0.1:7897 clone/push ...`，或对仓库 `git config http.proxy http://127.0.0.1:7897`。注意代理端口可能随软件变动，先用 `(echo > /dev/tcp/127.0.0.1/7897) 2>/dev/null && echo OPEN` 探测，失效再依次试 7890/10809/ghproxy 镜像/Data API。
   ⚠️ **「代理优先」≠「必须代理」**：代理探测为失效（端口不通，curl=`000`）时，**先探直连**再决定兜底——`curl -m5 https://api.github.com`，返回 `200` 即说明 github.com 直连可达。2026-09-28 实测：代理 7897 宕机（curl=`000`），但 github.com 直连可用（api=200、`git ls-remote origin` 直连成功、store 里 PAT 有效），此时直接 `GIT_HTTP_PROXY= HTTPS_PROXY= git -c http.proxy= -c credential.helper=store push origin main` 即可推送成功，**无需走 Data API 兜底**。即：代理首选 → 代理宕则探直连 → 直连也不通才走 Data API。
3. **GCM 免 PAT 已失效（2026-09-22 主机重装）**：PortableGit 的 `credential.helper=helper-selector` 指向不存在的组件，Windows 凭据管理器无 github 条目，`git credential fill` 不再返回 token；push 会在终端静默挂起等待输入（后台任务表现为无限 hang）。**现用 PAT + `credential.helper=store`**（存 `~/.git-credentials`，明文，已向用户交底）。写入：`printf "protocol=https\nhost=github.com\nusername=phxjchina\npassword=<PAT>\n" | git credential-store store`；推送：`git -c credential.helper=store push origin main`。⚠️ **只配全局 `credential.helper=store` 不够**：系统级 helper-selector 仍在助手链里报错导致 `git credential fill`/push 失败，须先加空重置——`git config --global --replace-all credential.helper "" && git config --global --add credential.helper store`（2026-09-27 实测，空条目会清掉此前所有 helper，之后 fill 即通）。
4. **正确配置态 = 不存在 ghproxy 的 insteadof 规则**。若存在全局 `url.https://ghproxy.net/https://github.com/.insteadof=https://github.com/`，会把 push 改写成 ghproxy 只读地址导致必失败 → 先 `git config --global --unset "url.https://ghproxy.net/https://github.com/.insteadof"`。
5. **不要用 `timeout` 包装 push**：Git Bash 会命中 Windows `timeout.exe` 报「默认选项不允许超过1次」语法错。另：**非交互会话里 push 若无凭据会静默挂起**（等待终端输入），务必带 `GIT_TERMINAL_PROMPT=0` 做探错，或直接配置凭据。
6. **路径**：MSYS 路径 `/c/tmp/x` 传给 git 偶报 `cannot change to ...: No such file or directory`，改用 Windows 形式 `C:/tmp/x`。若某临时副本 `.git` 损坏（git 报 `not a git repository` 但 `ls`/`cat` 正常），**直接重建新 clone**，别纠缠。
7. **PAT 权限**：Fine-grained 选本仓库 `Contents: Read and write` 即可；无写权限的 PAT 会 403。
8. **sparse-checkout**：旧本地副本可能是 sparse（`/*` + `!/*/`，只检根文件）；**全新 clone 是 full checkout，无此限制**，直接 `git add <子目录>` 即可。
9. **仓库局部配置要重做**（重装/新 clone 后）：`user.name=phxjchina`、`user.email=user@example.com`、`http(s).proxy=127.0.0.1:7897`。

## 判定哪些技能该同步（自建 vs 第三方）

本机 `~/.workbuddy/skills/` 里混合了**自建技能**与**市场 / 官方安装的技能**。只同步自建的，避免把第三方内容推到自己的仓库。

| 判据 | 结论 |
|---|---|
| frontmatter 有 `agent_created: true` | **自建** → 同步 |
| author 含「彭老师 / 小布 / WorkBuddy」 | **自建** → 同步 |
| frontmatter 含 `license:` / `allowed-tools:` / `tags:` | **第三方**（社区 skill 常带 MIT 声明）→ 跳过 |
| author 是第三方名（Sahil Lavingia、TPD、RedFoxHub、Tencent Zhuque Lab 等） | **第三方** → 跳过 |
| 正文含本地特征（彭老师 / 某高校校名 / `C:/Users/Administrator`） | 自建佐证 |

扫描要点：读每个 `SKILL.md` 的 frontmatter，正则提取 `name/version/author/agent_created`，再对全文 grep 本地特征词。

⚠️ **坑**：本机大部分 `SKILL.md` 是 **CRLF 行尾**，正则匹配前务必先 `txt.replace('\r\n','\n')`，否则 frontmatter 会整体匹配失败（表现为所有字段都读成空，本次踩过）。

## 标准流程

```bash
SKILLS="C:/Users/Administrator/.workbuddy/skills"
SRC_REPO="https://ghproxy.net/https://github.com/phxjchina/SkillRepository.git"   # 读走镜像
DST_REPO_DIR="C:/Users/Administrator/SkillRepository"                              # 用 Windows 路径
DIRECT="https://github.com/phxjchina/SkillRepository.git"
PY="C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe"

# 0) 确保没有 ghproxy 改写规则（有就 unset）
git config --global --unset "url.https://ghproxy.net/https://github.com/.insteadof" 2>/dev/null || true

# 0.5) 网络探测（决定走代理还是直连，见核心事实 2）
PROXY="http://127.0.0.1:7897"
PROXY_OK=$( (echo > /dev/tcp/127.0.0.1/7897) 2>/dev/null && echo 1 || echo 0 )
DIRECT_OK=$( curl -m5 -s -o /dev/null -w "%{http_code}" https://api.github.com 2>/dev/null )
echo "proxy=$PROXY_OK  direct_api=$DIRECT_OK"
# 优先级：代理可达用代理；代理不可达但直连 200 则直连；都不可达走 Data API（见兜底节）

# 1) clone（读，代理可达首选代理；代理不可达但直连可用则直连；否则 ghproxy 镜像作备选）
rm -rf "$DST_REPO_DIR"
if [ "$PROXY_OK" = "1" ]; then
  git -c http.proxy=$PROXY clone "$DIRECT" "$DST_REPO_DIR"
elif [ "$DIRECT_OK" = "200" ]; then
  GIT_HTTP_PROXY= HTTPS_PROXY= git -c http.proxy= clone "$DIRECT" "$DST_REPO_DIR"
else
  git clone "https://ghproxy.net/$DIRECT" "$DST_REPO_DIR"
fi

# 2) 复制技能目录（多个技能就重复这行），清理 Python 缓存
cp -r "$SKILLS/<skill-a>" "$DST_REPO_DIR/"
cp -r "$SKILLS/<skill-b>" "$DST_REPO_DIR/"
rm -rf "$DST_REPO_DIR"/*/scripts/__pycache__

# 3) 提交（重装后首次需配身份）
cd "$DST_REPO_DIR"
git config user.name "phxjchina" && git config user.email "user@example.com"
git config http.proxy $PROXY && git config https.proxy $PROXY
git add <skill-a> <skill-b>
git commit -m "feat(skills): 新增 <skill-a> 与 <skill-b>"

# 4) push（走代理 + store 凭据；GCM 已失效见核心事实 3）
#    代理不可达但直连可用时，临时绕过代理直连推：
if [ "$PROXY_OK" = "1" ]; then
  git -c credential.helper=store push origin main
else
  GIT_TERMINAL_PROMPT=0 GIT_HTTP_PROXY= HTTPS_PROXY= git -c http.proxy= -c credential.helper=store push origin main
fi
# 成功输出形如： a03f073..1d7cabe  main -> main
```

## 兜底：github.com 被墙时走 GitHub Data API 增量推送

> 前提澄清：本节是**最后兜底**。若代理宕机但 `curl https://api.github.com` 返回 `200`，应优先用核心事实 2 的「直连 `git push`」路径（2026-09-28 实测可行），**不必**走 Data API——Data API 仅用于直连也不达时的极坏网络。

当 `git push` 直连 github.com 持续超时（`Could not connect to server`，实测约 21s 超时），而 `curl https://api.github.com` 秒通（HTTP 200）时，**改走 Data API** 完成推送——api.github.com 与 github.com 路由不同，前者常可达（实测 2026-09-25）。

脚本模板见本 skill 自带 `scripts/api_push_assets.js`（**Node 版，本机受管 Python 缺标准库 `Lib` 无法跑 `.py`，故 Node 版为首选可直接运行**）；同目录 `api_push_assets.py` 为其等价 Python 版，仅在完整 Python 环境下使用。**关键要点（务必遵守）**：

- **必须用 `base_tree` 增量模式**：`POST /git/trees` 传 `{"base_tree": <父提交的 tree sha>, "tree": [...]}`，未列出的既有文件会被保留。**切勿用 `base_tree: null`**——那会重建整棵树、把仓库里没列出的文件全部删掉（历史上就踩过这个坑）。
- 取父 tree：`GET /git/commits/<main 的 sha>` → `.tree.sha`。
- token 从 GCM 取：`printf "protocol=https\nhost=github.com\n" | git credential fill` → 取 `password=` 一行。
- 流程：逐文件建 blob（base64）→ 建 tree（带 base_tree）→ 建 commit（`parents`=父 sha）→ `PATCH /git/refs/heads/main`（`force: false`）。
- **推送后必须用 API 核实**：`GET /contents/?ref=main` 确认新项在、旧项没丢。
- API 直传字节、不经过 git 的 CRLF 规范化，故远程文件为 LF；日后网络恢复用 git push 可能出现 diff，属正常现象，不用惊慌。

一行调用（**推荐用环境变量传入，无需改脚本内常量**；ROOT 已在脚本内固定为 `C:/Users/Administrator/.workbuddy/SkillRepository`）：

```bash
# Node 版（本机首选，无需 Python）
NEW_DIRS="github-skill-repo-sync" \
MSG="docs(github-skill-repo-sync): Node 版 Data API 兜底脚本 + 直连探测说明" \
"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-3/node.exe" \
  "C:/Users/Administrator/.workbuddy/SkillRepository/github-skill-repo-sync/scripts/api_push_assets.js"

# Python 版（完整 Python 环境；本机受管 Python 缺 Lib 不可运行，仅作参考）
"C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe" \
  "C:/Users/Administrator/.workbuddy/SkillRepository/github-skill-repo-sync/scripts/api_push_assets.py"
```

## 核验（必做）
```bash
git ls-remote --heads "https://ghproxy.net/https://github.com/phxjchina/SkillRepository.git"
# 远程 main 哈希应等于本地刚提交的哈希
git -C "$DST_REPO_DIR" ls-tree -r --name-only <提交哈希> | grep -E "<skill-a>/|<skill-b>/"
```

## 故障排查
| 现象 | 根因 | 处理 |
|---|---|---|
| `Permission ... denied to <账号>` 403 | PAT 属别的账号或该账号无写权限 | 用 GCM 免 PAT（确保 `credential.helperselector.selected=manager`） |
| `denied to phxjchina` 403，但账号对 | PAT 的 `X-OAuth-Scopes` 为空（无 repo 权限） | 换 GCM，或改用勾了 `repo` 的 classic PAT |
| `CONNECT tunnel failed, response 502` / schannel `missing close_notify` | 走了 IPv6 | 加 `-c "http.curloptResolve=github.com:443:$IP"`（$IP 用托管 python 取 IPv4） |
| push 被改写到 ghproxy 报只读 | 存在全局 ghproxy insteadof 规则 | `git config --global --unset ...insteadof` |
| `Could not connect to server` 持续超时（强制 IPv4 也无效），但 `curl api.github.com` 通 | github.com 443 路由被墙 | 优先走本机代理 `127.0.0.1:7897`；**代理探测为失效（端口不通）时先 `curl -m5 https://api.github.com` 探直连**——返回 `200` 即直接 `GIT_HTTP_PROXY= HTTPS_PROXY= git -c http.proxy= -c credential.helper=store push`（2026-09-28 实测成功，无需 Data API）；直连也不通才走 **GitHub Data API 增量推送**（见上节 `scripts/api_push_assets.py`） |
| push 静默挂起无任何输出（后台任务 hang 数分钟） | 无缓存凭据，git 在终端等输入（GCM 已失效） | 杀掉任务；配 PAT 到 `credential.helper=store` 后再推，或带 `GIT_TERMINAL_PROMPT=0` 先探错 |
| `fatal: not a git repository`（.git 存在） | 临时副本损坏 | 重建新 clone |
| `cannot change to '/c/tmp/...'` | MSYS 路径 | 用 `C:/tmp/...` Windows 形式 |
| `Updates were rejected ... fetch first` | 远程领先本地 | 重新 clone（或 fetch 真实远端后 rebase）再推 |

## 边界
- 本技能只做同步；技能内容本身的设计/校验另见 `program-director-plan`、`dept-head-review` 等。
- 推送成功后可建议用户撤销对话中暴露过的无权限/不需要的 PAT。
