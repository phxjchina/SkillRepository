# SkillRepository

彭老师在日常科研与教学中总结出的一些**可复用技能（WorkBuddy Skills）**集合。

## 技能目录

- [`ima-kb-rename-table/`](./ima-kb-rename-table/) — **ima 知识库 PDF 批量改名对照表**
  递归列举 ima 知识库某大类下的 PDF，从全文提取论文/报告标题，生成「原文件名 → 建议改名」对照表（CSV/XLSX/HTML）。
  适用场景：知识库无重命名 API、需批量把文件名规范化为论文标题时。详见该目录内 `README.md` 与 `SKILL.md`。

- [`translate-pdf-to-zh-docx/`](./translate-pdf-to-zh-docx/) — **英文学术 PDF → 中文 Word 翻译管线**
  将英文（或其他语种）学术 PDF 翻译为结构化中文 `.docx`：保留标题层级与段落衔接、图片原位嵌入、表格真实翻译、显示公式干净截图，并剥离页眉页脚噪声。质量接近 Google 翻译，适配中国大陆网络（本地代理 + MyMemory 兜底）。详见该目录内 `README.md` 与 `SKILL.md`。

- [`survey-from-local-pdfs/`](./survey-from-local-pdfs/) — **本地 PDF 语料 → 系统文献综述（SLR）**
  把一批本地下载的论文 PDF 当作唯一参考文献库，产出引用零幻觉的中文系统文献综述（SLR 范式）：研究问题、方法论、纳入/排除、数据表、效度威胁一应俱全，内置引用校验（零悬空、零未引）。详见该目录内 `README.md` 与 `SKILL.md`。

## 安装方法

把本仓库克隆到本地，再将需要的技能目录复制到：

- **用户级**（跨项目可用）：`~/.workbuddy/skills/<skill-name>/`
- **项目级**（随仓库共享）：`<项目>/.workbuddy/skills/<skill-name>/`

复制完成后，**重载 WorkBuddy（或新开一个会话）**，技能即出现在可用技能列表。

## 贡献 / 完善

欢迎 **Fork** 本仓库 → 修改对应技能的 `SKILL.md`（或补充 `scripts/`、`references/` 资源）→ 提交 **Pull Request**，改进会回流到本仓库，惠及所有人。
