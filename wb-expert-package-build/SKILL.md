---
name: wb-expert-package-build
description: 把已有资料或方法论（文档、SKILL.md、框架知识库、提示词）转化为可上架 WorkBuddy 专家中心的 Expert 包（专家 / 专家团），并完成初始化、校验、注册、打包全流程。当用户要求「把某套东西做成专家」「创建/转化 expert」「生成专家包」「发布专家」「上架专家中心」时使用。内含 Windows 实操踩坑清单。
version: "1.0.0"
agent_created: true
---

# WorkBuddy Expert 包制作

把「一堆资料 / 一套方法论」变成 WorkBuddy 专家中心里可安装、可分享的 Expert 包。

> 本 skill 是 builtin `expert-manager` 的实操补充：**字段规范与脚本以 `expert-manager` 为准**，本 skill 聚焦「流程串联 + 校验硬规则 + Windows 踩坑」。

## 何时使用

- 用户要把某份文档 / 某个 Skill / 一套方法论做成 Expert（如「实验室管理体系架构师」这类角色顾问）
- 用户要创建、转化、修改、打包、上架专家
- 用户问「怎么发布专家 / 专家怎么给别人用 / 怎么变现」

## 硬性前提（不可违反）

1. **专家目录固定**：`$WORKBUDDY_CONFIG_DIR/plugins/marketplaces/my-experts/plugins`
   （本机 `WORKBUDDY_CONFIG_DIR=C:\Users\Administrator\.workbuddy`）
   生成到别处 = **检测不到、市场不可见**。
2. **脚本一律用 builtin expert-manager 的**：
   `D:/WorkBuddy/resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/expert-manager/scripts/`
   （init_expert.py / validate_expert.py / register_expert.py / package_expert.py）
3. **Python 用托管解释器**：`C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe`

## 标准流程（7 步）

1. **读规范**：`expert-manager/references/` 下 `plugin-json-spec.md`、`agent-md-spec.md`、`avatar-spec.md`（Team 型再加 `team-spec.md`）
2. **判类型与分类**：
   - 单角色 → `expertType: "agent"`；多角色协作 → `"team"`（**必须按实际结构判，不可随意指定**）
   - `categoryId` 从 12 类白名单选，按「主要输出物领域 + 服务对象」判定，并向用户说明理由
3. **初始化**：`init_expert.py <name> --type agent|team --path <专家目录>`
   - `<name>` 必须 **kebab-case 且有业务语义**（如 `lab-os-architect`，不可用 `team-lead`）
4. **填内容**：`.codebuddy-plugin/plugin.json`（展示字段）+ `agents/<name>.md`（frontmatter + 正文）+ `README.md`
5. **生成头像**：用 `ImageGen`，读 avatar-spec 从 Agent MD 角色特征构建 prompt，背景色调按 categoryId 映射；**生成后必须缩到 512×512 且 ≤500KB**
6. **校验**：`validate_expert.py <expert-dir>`（必须零 error）
7. **注册**：`register_expert.py <expert-dir>`（写入 marketplace.json）；**再可选打包**：`package_expert.py <expert-dir> [输出目录]`

## 校验硬规则（validate 会卡）

| 规则 | 说明 |
|---|---|
| tags / quickPrompts | **各恰好 3 个** |
| defaultInitPrompt.zh | 须 == quickPrompts[0].zh |
| displayDescription.zh | 40–50 字 |
| categoryId | 必须在 12 类白名单内 |
| Agent MD frontmatter | **禁止 tools 字段** |
| frontmatter `name` | 必须 == MD 文件名 |
| plugin.json 位置 | 在 `.codebuddy-plugin/plugin.json`（**不是** `.workbuddy-plugin`） |
| `plugin` 字段 | 须 == `name` |

## Windows 实操踩坑（重要）

1. **路径必须用原生 Windows 形式**（`C:/...`）。Git Bash 的 `$HOME` 会展开成 `/c/...`，被原生 Python 误拼成 `E:\c\...`，脚手架会建到错位置。
2. **头像体积**：`ImageGen` 默认 `size=1024x1024` 常产出 1MB+ PNG，**超出 500KB 规范**。用 Pillow 缩放压缩：
   ```python
   from PIL import Image
   im = Image.open(p).convert("RGB").resize((512, 512), Image.LANCZOS)
   im.save(p, "PNG", optimize=True)   # 512×512 卡通插画通常 300–400KB
   ```
   若 PNG 仍超 500KB，改存 JPG（`quality=88`）并同步改 plugin.json 的 `avatar` 路径。
3. **头像文件名**：ImageGen 产出是随机文件名，需重命名为 plugin.json 里声明的（通常 `avatars/expert.png`）。
4. **注册后市场才可见**：`marketplace.json` 由 `register_expert.py` 生成，**禁止手写**；校验不通过会拒绝注册。
5. **不可改的标识**（改了专家会丢失）：plugin.json 的 `name` / `agentName`、专家目录名、`agents/*.md` 文件名。要改名只能重建。
6. `rm -rf` 可能被 WorkBuddy safe-delete 机制 fail-closed 拦截；删除请用明确的 `rm -f <具体文件>`。

## 命令模板（本机可直接复用）

```bash
PY="C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe"
SD="D:/WorkBuddy/resources/app.asar.unpacked/resources/plugins/workbuddy-builtin/skills/expert-manager/scripts"
ROOT="C:/Users/Administrator/.workbuddy/plugins/marketplaces/my-experts/plugins"

"$PY" "$SD/init_expert.py"    my-expert --type agent --path "$ROOT"
# … 填充 plugin.json / agents/my-expert.md / README.md / 生成头像 …
"$PY" "$SD/validate_expert.py" "$ROOT/my-expert"
"$PY" "$SD/register_expert.py" "$ROOT/my-expert"
"$PY" "$SD/package_expert.py"  "$ROOT/my-expert" "E:/输出目录"
```

## 交付后提醒用户

- 头像可手动替换（512×512、PNG/JPG、≤500KB）
- 专家需**重启 WorkBuddy 或新开对话**才在 GUI 专家中心可见（会话启动时列表为快照）
- 打包产物 zip 可直接分发；**上架开放平台（open.workbuddy.cn）另走在线上传流程**
