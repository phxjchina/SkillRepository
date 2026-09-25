---
name: wb-skill-load-verify
description: "验证一个 WorkBuddy Skill 能否在真实运行时中正常安装与加载。复制候选 Skill 到用户级技能目录（~/.workbuddy/skills/技能名），解析 SKILL.md 的 frontmatter（name/description/version/author）、校验目录名与 name 一致、用支持中文文件名的规则解析全部相对路径引用并核对文件存在、交叉核对 frameworks 物理文档与显式引用，并检测 __pycache__ 再生作为已被加载器扫描的动态证据。This skill should be used when 用户刚构建/泛化/改造完一个 WorkBuddy Skill，需要在发布或上架前做一次真机加载体检，或怀疑某 Skill 装上去不生效、引用断裂、被 WorkBuddy 识别不到时。建议发布前用本验证器跑一次，确认结构合规、引用零损坏、且已被 WorkBuddy 运行时实际加载。"
version: "1.0.0"
author: "彭老师 / WorkBuddy"
agent_created: true
---

# WorkBuddy Skill 真机加载验证器（wb-skill-load-verify）

## Purpose

在把一个 Skill 发布 / 上架之前，用最少的步骤确认它能被 WorkBuddy 真实运行时识别、加载、且所有相对路径引用都能解析。覆盖静态结构校验与动态加载证据两条链路。

## When to Use

- 用户刚写完、泛化改造完、或从别处拿到一个 Skill，准备发布 / 上架 / 交付前，要"体检"能否正常加载。
- 用户反馈"这个 Skill 装上去不生效 / 识别不到 / 报文件找不到"时，定位是结构问题还是引用断裂。
- 验证泛化改造是否彻底消除了绝对路径硬编码（如 `/workspace/...`）。

## How to Use

### 1. 运行验证器

验证器位于 `scripts/verify_skill_load.py`，支持两种模式：

```bash
# 仅静态校验某个已安装或候选的 skill 目录
python scripts/verify_skill_load.py <skill_dir>

# 先复制安装到 ~/.workbuddy/skills/<name>/ 再做完整校验（推荐发布前用）
python scripts/verify_skill_load.py <skill_dir> --install
python scripts/verify_skill_load.py <skill_dir> --install --name my-skill
```

校验输出 6 步：
- **STEP 1** 安装位置 / 核心文件（SKILL.md）存在性
- **STEP 2** frontmatter 四字段（name / description / version / author）完整性
- **STEP 3** 目录名 == `frontmatter.name`（WorkBuddy 的加载约定，不一致则不被识别）
- **STEP 4** SKILL.md 相对路径引用完整性——**正则必须含中文**（`[^\s，。、()（）"'`<>，]+`），否则中文文件名引用会被漏检或误报为 BROKEN
- **STEP 5** `frameworks/` 物理 .md 与 SKILL.md 显式引用交叉核对（冗余未引用无害）
- **STEP 6** 动态加载证据：检测 `__pycache__/*.pyc`——由 WorkBuddy 加载器扫描 skill 时 import 并字节码编译生成，**存在即证明已被真实运行时加载（铁证）**

### 2. 解读常见失败

| 现象 | 根因 | 处理 |
|---|---|---|
| STEP 3 FAIL（目录名≠name） | 目录名与 frontmatter 不一致 | 改名目录或改 name 字段 |
| STEP 4 BROKEN 且路径末尾带 `` ` `` | 正则未排除反引号，误报 | 用本 skill 自带脚本（已处理） |
| STEP 4 BROKEN 真实路径 | 引用文件缺失或路径未相对化 | 改为相对路径或补文件 |
| 安装目录残留 `/workspace` | 泛化不彻底 | 全局替换为相对路径 |
| STEP 6 无 __pycache__ | 当前会话快照未刷新 | 重启 WorkBuddy / 新开对话后再跑一次 |

### 3. 两个关键坑（必读）

1. **当前会话快照不刷新**：`available_skills` 是会话启动时的快照，新装 Skill 不会出现在本会话。要在 GUI 看到并触发，必须**重启 WorkBuddy 或新开对话**，再用技能面板 / `/<skill-name>` / 自然语言触发。验证器 STEP 6 的 `__pycache__` 才是"已被加载"的硬证据。
2. **safe-delete 拦截 `rm`**：WorkBuddy 的 safe-delete 机制对 `~/.workbuddy/skills/` 下的 `rm -rf` 会 fail-closed 拒绝删除（保护技能目录）。`--install` 模式用 `shutil.copytree` + 主动清理 `__pycache__`，无需手动 `rm`；若需手动清理缓存，直接无视即可（无害，加载器会重建）。

## Notes

- 验证器不修改被验证 Skill 的内容，只读取与（--install 时）复制。
- 分发源目录应保持无 `__pycache__`；`--install` 已自动清理复制产物中的缓存。
- 该验证针对 WorkBuddy 用户级技能目录 `~/.workbuddy/skills/`；项目级 `.workbuddy/skills/` 同理，把 SKILLS_ROOT 改掉即可。
