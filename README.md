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

- [`graduation-design-advisor/`](./graduation-design-advisor/) — **毕业设计监督导师（全流程跟踪 + 阶段成果审核）**
  代替指导教师在「选题 → 任务书 → 开题 → 中期 → 论文初稿/定稿 → 评阅/答辩 → 成绩」全流程中监督学生、逐阶段审核成果。含 **9 阶段状态模型 + 队列驾驶舱**（一眼看整届进度、谁缺材料、谁卡住）+ **单人下钻精审** + **主动巡检**（"本周谁卡住了"）；内置任务书 / 开题 / 论文三套审核清单、跨文档五条铁律与抽检红线。脚本：`supervision_cockpit.py`（队列看板，扫本地 .docx 目录一键出整届进度）、`review_docx.py` / `review_thesis.py`（结构初筛，**含表格内容**）、`inject_comments.py`（Word 真批注注入，保留原图与排版、不覆盖已有批注）。详见该目录内 `SKILL.md`。

- [`program-director-plan/`](./program-director-plan/) — **专业负责人·培养方案设计（OBE 反向设计）**
  帮专业负责人/教研室按 OBE 反向设计产出培养方案：先定"能开发的系统" → 拆子系统 → 功能 → 知识点 → 教学大纲；给出三层课程结构（基座/核心/特色）、跨专业去冗余与衔接策略、撤销专业课程迁移与微专业融入方案；并生成分层依赖大图（SVG）与 Word 终稿。脚本：`reverse_design_render.py`（"系统→子系统→功能→知识点→课程"五列泳道反向设计大图，内附三专业示例数据）、`md_to_docx.py`（md → Word，精确保留表格与图片）。详见该目录内 `SKILL.md`。

- [`dept-head-review/`](./dept-head-review/) — **系主任·培养方案审核（六维审查 + 修订指令）**
  帮系主任/教学副院长审核各专业培养方案：按"差异化与错位竞争、去冗余不断层、能力培养主线(OBE)、应用型定位、撤销专业功能不撤销、工程认证 2024 衔接"六维逐条审查，产出结构化《审核意见表》（总体结论 + 各维度问题 + 严重程度 + 修改建议），并可下达成修订指令交由 `program-director-plan` 执行。脚本：`review_plan.py`（自动初筛：抽课程名、查缺失章节、跨专业重名课检测）。详见该目录内 `SKILL.md`。

## 专家（Expert）

除技能外，本仓库还收录可直接安装到 WorkBuddy 专家中心的**专家包**：

- [`graduation-supervisor/`](./graduation-supervisor/) — **毕业设计监督导师（专家包）**
  把上面的 `graduation-design-advisor` 技能封装为常驻**专家角色**（Agent 型，分类：项目质量）：内嵌该技能副本、专家人设与工作流（`agents/graduation-supervisor.md`）、头像及 `.codebuddy-plugin/plugin.json` 清单，自包含、开箱即用。安装后即可以「毕业设计监督导师」身份对话，代您监督学生并审核每个阶段性成果。详见该目录内 `README.md`。

## 安装方法

把本仓库克隆到本地，再将需要的技能目录复制到：

- **用户级**（跨项目可用）：`~/.workbuddy/skills/<skill-name>/`
- **项目级**（随仓库共享）：`<项目>/.workbuddy/skills/<skill-name>/`

复制完成后，**重载 WorkBuddy（或新开一个会话）**，技能即出现在可用技能列表。

## 贡献 / 完善

欢迎 **Fork** 本仓库 → 修改对应技能的 `SKILL.md`（或补充 `scripts/`、`references/` 资源）→ 提交 **Pull Request**，改进会回流到本仓库，惠及所有人。
