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

- [`graduation-design-coach/`](./graduation-design-coach/) — **毕业设计陪跑教练（面向学生，v1.2.0）**
  与监督导师配对的**学生端**技能：「只辅导不代写」，陪一名学生走完 **选题 → 任务书 → 开题报告 → 工程实现 → 中期检查 → 论文撰写 → 答辩PPT** 七阶段。含 7 阶段指导手册（附教师批改提炼的《论文写作规范速查》）、常见坑 50 条、模板/范例库索引、答辩问答库（通用 + 本实验室真实课题 9 类 + 查重/AIGC 规范）。脚本：`coach_progress.py`（个人进度卡）、`self_check.py`（阶段自检，支持 `--type translation` 与 `--stage mid/draft` 阶段感知）、`gen_skeleton.py`（任务书/开题/论文可填空骨架）、`gen_defense_ppt.py`（一键 11 页答辩 PPT）。已用 2021-2026 五届、17+ 人真实材料批量实测演化。详见该目录内 `SKILL.md`。

- [`lab-os-agent/`](./lab-os-agent/) — **实验室 OS Agent（导师管理驾驶舱 + 学生培养陪跑）**
  面向高校实验室的**本地化学生管理 Agent 操作手册**（自包含：含 15 份框架知识库 `frameworks/` 与可运行教学原型 `world_model_lab/`）。核心为 **双端口**（导师「管理驾驶舱」+ 学生「培训陪跑」）、**多专家编排**（Router + 技术/情绪/制度/信念/能力/实验 6 专家）、**职能委员体系**（9 委员 ↔ Agent 能力映射）、**多模态感知层**（视频 / 图像+声音 本地被动信号）、**物理 AI 研究北极星**（P1–P4）与**实验室世界模型**（把整套体系作为对实验室世界的内部模型 / 管理元框架）。已泛化为通用版：路径相对化、身份脱敏、模型后端可插拔（本地 Ollama / deepseek / qwen / zhipu）。详见该目录内 `SKILL.md`。

- [`wb-skill-load-verify/`](./wb-skill-load-verify/) — **WorkBuddy Skill 真机加载验证器**
  发布 / 上架前对 Skill 做一次真机加载体检：解析 frontmatter、校验目录名与 `name` 一致、按支持中文文件名的规则核对全部相对路径引用、交叉核对 `frameworks` 物理文档与显式引用，并检测 `__pycache__` 再生作为「已被 WorkBuddy 加载器扫描」的动态证据。脚本：`scripts/verify_skill_load.py <skill目录> [--install]`。详见该目录内 `SKILL.md`。

- [`wb-expert-package-build/`](./wb-expert-package-build/) — **WorkBuddy Expert 包制作流程**
  把已有资料 / 方法论（文档、`SKILL.md`、框架知识库、提示词）转化为可上架专家中心的 **Expert 包**，串联 `init → validate → register → package` 全流程，内附字段硬规则与 Windows 实操踩坑清单。是 builtin `expert-manager` 的实操补充。详见该目录内 `SKILL.md`。

## 专家（Expert）

除技能外，本仓库还收录可直接安装到 WorkBuddy 专家中心的**专家包**：

- [`graduation-supervisor/`](./graduation-supervisor/) — **毕业设计监督导师（专家包）**
  把上面的 `graduation-design-advisor` 技能封装为常驻**专家角色**（Agent 型，分类：项目质量）：内嵌该技能副本、专家人设与工作流（`agents/graduation-supervisor.md`）、头像及 `.codebuddy-plugin/plugin.json` 清单，自包含、开箱即用。安装后即可以「毕业设计监督导师」身份对话，代您监督学生并审核每个阶段性成果。详见该目录内 `README.md`。

- `graduation-coach.zip`（发布包）— **毕业设计辅导教练（学生端专家包）**
  把 `graduation-design-coach` 技能封装为面向学生的常驻专家（Agent 型，分类：项目质量）。**学生获取方式**：下载本仓库中的 zip（或老师发的群文件）→ WorkBuddy 专家中心 → 导入/安装 → 对话里 @「毕业设计辅导教练」即可开始七阶段陪跑。源码目录见 [`skills` 同名技能](./graduation-design-coach/)。

- `lab-os-architect.zip`（发布包）— **实验室管理体系架构师（专家包）**
  把 `lab-os-agent` 的**方法论**（双端口、六专家、9 委员映射、多模态感知、物理 AI P1–P4、世界模型元框架）提炼为常驻**专家角色**（Agent 型，分类：运营人力 09-OperationsHR）：面向高校实验室导师，提供体系诊断、架构设计与分阶段落地路线。**使用方式**：下载 zip → WorkBuddy 专家中心 → 导入 / 安装 → 对话里 @「实验室管理体系架构师」即可。源码技能见 [`lab-os-agent/`](./lab-os-agent/)。

## 安装方法

把本仓库克隆到本地，再将需要的技能目录复制到：

- **用户级**（跨项目可用）：`~/.workbuddy/skills/<skill-name>/`
- **项目级**（随仓库共享）：`<项目>/.workbuddy/skills/<skill-name>/`

复制完成后，**重载 WorkBuddy（或新开一个会话）**，技能即出现在可用技能列表。

## 贡献 / 完善

欢迎 **Fork** 本仓库 → 修改对应技能的 `SKILL.md`（或补充 `scripts/`、`references/` 资源）→ 提交 **Pull Request**，改进会回流到本仓库，惠及所有人。
