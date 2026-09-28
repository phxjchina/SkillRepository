---
name: workbuddy-workspace-4011-fix
description: 诊断并修复 WorkBuddy 报错 4011「Conversation workspace does not exist or was removed：<路径>」。当用户粘贴该报错、或反馈某个历史任务打不开/提示工作空间不存在时使用。典型根因是工作空间目录被移动或重命名，而会话中记录的旧路径失效。修复首选在原路径建目录联接（Junction）指回新位置，不移动任何文件且可逆。
version: 1.0.0
author: 小布
agent_created: true
---

# WorkBuddy 报错 4011 工作空间不存在 —— 诊断与修复

## 触发场景

用户粘贴形如下面的报错：

```
Error Code: 4011
Server Detail: {"code":4011,"details":"Conversation workspace does not exist or was removed: <某个绝对路径>"}
```

或用户说「某个历史任务打不开」「提示工作空间不存在」。

## 根因（先记住这条）

WorkBuddy 在**创建会话时把工作空间绝对路径固化**在两处：

| 位置 | 内容 |
| --- | --- |
| `~/.workbuddy/workspace-display-names.json` | `workspaces.<斜杠小写路径>.path` = 原始绝对路径 |
| `~/.workbuddy/projects/<slug>/<会话UUID>.jsonl` | 会话正文；slug 由路径段用 `-` 拼接、盘符小写 |
| `~/.workbuddy/changes-index/<UUID>.json` 等 | 变更索引，同 UUID |

此后只要**移动或重命名该目录**（或它的任一上级目录），旧路径失效，打开会话即报 4011。
**注意：报错里给的路径就是旧路径，磁盘上找不到很正常，不代表数据丢了。**

## 诊断步骤

1. 取报错里的路径，例如 `F:\教学\2026下半年\物联网概论资料\物联网概论`。
2. 确认它是否真的不存在（Git Bash：`ls -la "F:/教学/2026下半年"`）。
3. 读取 `~/.workbuddy/workspace-display-names.json`，核对记录的 `path` 与报错是否一致（会带 displayName，可用于确认是哪一个任务）。
4. 在磁盘上找真实位置：按**目录名逐层搜**，通常只差中间某一层。最省事的办法是看缺失层的同级目录的 mtime —— 被整理过的日期会露出来。
   - 例：`F:\教学` 下只有 `2022年工作`~`2026年工作`、`尤涛2026项目` 等 → 说明 `2026下半年` 被收进了 `2026年工作\`。
5. 核对会话数据仍在：`ls ~/.workbuddy/projects/<slug>/` 应能看到 `<UUID>.jsonl`（体积正常即无丢失）。目标目录下的 `.workbuddy/` 也应完好。
6. 结论写成「会话记录的路径少了中间一层 X」这类一句话。

## 修复（按优先级）

### 方案 A（首选）原路径建目录联接，恢复原会话

不移动、不复制任何文件，只在旧路径处建一个 Junction 指回新位置。

```powershell
$t = "F:\教学\2026年工作\2026下半年"   # 真实位置
$l = "F:\教学\2026下半年"                # 报错里的旧路径
if (-not (Test-Path -LiteralPath $t)) { "ERROR: 目标不存在"; exit 1 }
if (Test-Path -LiteralPath $l) { "已存在，跳过" } else {
  New-Item -ItemType Junction -Path $l -Target $t | Out-Null
}
Get-Item -LiteralPath $l -Force | Select-Object FullName, LinkType, Target | Format-List
```

验证（Git Bash 能直接看到软链指向并穿透读目录）：

```bash
ls -la "F:/教学/2026下半年"
ls -la "F:/教学/2026下半年/物联网概论资料/物联网概论" | head
```

- Junction **不需要管理员权限**（符号链接才需要）。
- 台账里其余部分无需改动：`projects` 的 slug 与 `workspace-display-names.json` 记的都是旧路径，正是我们要让它重新可用的路径。
- 撤销：`Remove-Item -LiteralPath "<旧路径>" -Force`（只删链接，**不加 `-Recurse`**）。
- 提醒用户：联接是"活"的，以后移动**目标**目录仍会断开；另外别用会把 Junction 展开成真实副本的工具去复制该目录。

### 方案 B 新建任务指向正确路径

放弃旧会话记录，新建任务时工作空间选真实路径。文件全在，最干净，但旧对话无法再打开。适用于只有一两次对话、不值当保留的情形。

### 方案 C 把目录移回原位

恢复原路径，但会破坏用户后来的目录组织方式，一般不推荐，除非用户明确要回到旧结构。

## 排查中的常见坑

- **PowerShell 工具可能不回显 stdout**，命令返回 `exit code 0` 却看不到输出。不要据此判定失败，改用 Bash（Git Bash）复验，或把结果写文件再读。
- Git Bash 里 `ls` 对 Junction 显示为 `lrwxrwxrwx ... -> /f/...`，这是正常的（MSYS 把 reparse point 统一当软链）。
- Windows 路径含中文时，优先用 PowerShell 的 `-LiteralPath` 处理，别在 Git Bash 里用 `cmd /c` 拼接中文路径（编码易乱）。
- 不要为了"修好"去移动/重命名用户的原始目录 —— 那正是病因。**加链接，不动数据。**
- 若 `projects/<slug>` 下的 `.jsonl` 也不见了，才是真的会话丢失，此 skill 不适用。

## 预防

- 已作为工作空间使用过的目录，**不要随意移动或重命名上级目录**；确需整理时先关闭相关任务。
- 整理教学/资料盘时，改动后逐个打开常用任务验证一遍。
