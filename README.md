# SkillRepository

彭老师在日常科研与教学中总结出的一些**可复用技能（WorkBuddy Skills）**集合。

## 技能目录

- [`ima-kb-rename-table/`](./ima-kb-rename-table/) — **ima 知识库 PDF 批量改名对照表**
  递归列举 ima 知识库某大类下的 PDF，从全文提取论文/报告标题，生成「原文件名 → 建议改名」对照表（CSV/XLSX/HTML）。
  适用场景：知识库无重命名 API、需批量把文件名规范化为论文标题时。详见该目录内 `README.md` 与 `SKILL.md`。

## 安装方法

把本仓库克隆到本地，再将需要的技能目录复制到：

- **用户级**（跨项目可用）：`~/.workbuddy/skills/<skill-name>/`
- **项目级**（随仓库共享）：`<项目>/.workbuddy/skills/<skill-name>/`

复制完成后，**重载 WorkBuddy（或新开一个会话）**，技能即出现在可用技能列表。

## 贡献 / 完善

欢迎 **Fork** 本仓库 → 修改对应技能的 `SKILL.md`（或补充 `scripts/`、`references/` 资源）→ 提交 **Pull Request**，改进会回流到本仓库，惠及所有人。
