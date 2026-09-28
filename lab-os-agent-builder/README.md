# lab-os-agent-builder 技能安装包

本压缩包是一个 WorkBuddy / CodeBuddy 技能（skill），可直接安装到本地客户端使用。

## 包含文件

- `SKILL.md` —— 技能主文件（YAML frontmatter + 构建方法论正文）
- `README.md` —— 本说明

## 安装方式（任选其一）

### 方式 A：导入 skill 包（若客户端支持）
部分 WorkBuddy / CodeBuddy 客户端提供「导入技能 / Import Skill」入口，
直接选择本 `lab-os-agent-builder.zip` 即可自动安装，无需手动解压。

### 方式 B：解压到技能目录（通用）
1. 解压本 zip，得到 `lab-os-agent-builder/` 文件夹。
2. 将其整体复制到本机技能目录：

   - **Windows**：`C:\Users\<您的用户名>\.codebuddy\skills\lab-os-agent-builder\`
   - **macOS / Linux**：`~/.codebuddy/skills/lab-os-agent-builder/`

   最终路径结构应为：
   ```
   <技能目录>/lab-os-agent-builder/
   ├── SKILL.md
   └── README.md
   ```

3. 重启（或刷新）WorkBuddy / CodeBuddy 客户端，技能即生效。

## 验证安装

在客户端对话中输入「实验室 OS Agent 构建方法论」相关要求，
若 agent 自动加载本技能（读取 `SKILL.md` 中的上下文、演进时间线、协作纪律与可复用工作流），即说明安装成功。

## 备注

- 本技能为**纯文档型**，无任何外部脚本或资源文件依赖，迁移与安装均只需这一个文件夹。
- `SKILL.md` 内引用的 `/workspace/...` 路径为原构建环境（沙箱）的工作区路径，
  属参考性描述；在您本机使用时，请按实际工作区目录理解，不影响方法论本身。
  如需改为相对/可配置路径，可手动编辑 `SKILL.md`。
- 版本：v1.0.0
