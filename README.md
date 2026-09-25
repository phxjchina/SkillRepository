# SkillRepository

彭老师在科研与教学中沉淀的**可复用技能（WorkBuddy Skills）与专家包（Expert）**集合。

所有技能均为「复制即用」：把技能目录复制到 `~/.workbuddy/skills/<name>/`，重载 WorkBuddy（或新开一个会话）即可使用；专家包（`*.zip` 或专家目录）则在 WorkBuddy 专家中心「导入 / 安装」。

---

## 一、教学与培养方案

- [`program-director-plan/`](./program-director-plan/) — **专业负责人（培养方案设计）智能体**
  按 **OBE 反向设计**从「能开发的系统」出发，拆出「子系统 → 功能 → 知识点 → 教学大纲」，产出培养方案轮廓：三层课程结构（基座 / 核心 / 特色）、课程清单与学期安排、反向设计大图（SVG）、以及 Word(.docx) 终稿。支持把教材目录、前沿方向反推为课程，处理撤销专业的功能不撤销迁移、微专业融入、AI 专业瘦身。详见该目录内 `SKILL.md`。

- [`dept-head-review/`](./dept-head-review/) — **系主任（培养方案审核）智能体**
  帮系主任 / 教学副院长按六维逐条审查各专业培养方案——**差异化与错位竞争、去冗余不断层、能力培养主线(OBE)、应用型定位、撤销专业功能不撤销、工程认证 2024 版衔接**，产出结构化《审核意见表》（总体结论 + 各维度问题 + 严重程度 + 修改建议），并可下达成修订指令。详见该目录内 `SKILL.md`。

- [`graduation-design-advisor/`](./graduation-design-advisor/) — **毕业设计监督导师（教师端，全流程跟踪 + 阶段成果审核）**
  代指导教师走完「选题 → 任务书 → 开题 → 外文翻译 → 中期 → 论文初稿/定稿 → 评阅/答辩 → 成绩」，含 **9 阶段状态模型 + 队列驾驶舱**（一眼看整届进度、谁缺材料、谁卡住）+ **单人下钻精审** + **主动巡检**；内置任务书 / 开题 / 论文三套审核清单、跨文档五条铁律与抽检红线（对照《陕西省本科毕业设计（论文）抽检评价要素》）。脚本：`supervision_cockpit.py`（队列看板）、`review_docx.py` / `review_thesis.py`（结构初筛，含表格内容）、`inject_comments.py`（Word 真批注注入，保留原图与排版）。详见该目录内 `SKILL.md`。

- [`graduation-design-coach/`](./graduation-design-coach/) — **毕业设计陪跑教练（学生端，v1.2.0）**
  与监督导师配对的**学生端**技能：「只辅导不代写」，陪一名学生走完 **选题 → 任务书 → 开题报告 → 工程实现 → 中期检查 → 论文撰写 → 答辩PPT** 七阶段。含 7 阶段指导手册（附《论文写作规范速查》）、常见坑 50 条、模板/范例库索引、答辩问答库。脚本：`coach_progress.py`、`self_check.py`（支持 `--type translation` 与 `--stage mid/draft`）、`gen_skeleton.py`、`gen_defense_ppt.py`（一键 11 页答辩 PPT）。已用 2021-2026 五届、17+ 人真实材料批量实测演化。详见该目录内 `SKILL.md`。

- [`lesson-plan-from-materials/`](./lesson-plan-from-materials/) — **从 PPT / 文档批量生成 Word 教案**
  以既有教学材料（`.ppt/.pptx` 或其它文档）为内容源，**严格镜像给定教案模板的版式**（表格、合并单元格、字体如宋体 10.5pt）批量生成 Word 教案。详见该目录内 `SKILL.md`。

- [`ppt-generation-skill/`](./ppt-generation-skill/) — **研究报告 / 论文 → PowerPoint 演示文稿**
  根据研究报告 / 论文 / 作业 / 项目方案生成结构清晰、要点精炼的 `.pptx`（含幻灯片大纲、简洁要点、演讲者备注与视觉设计建议），适用于课堂、开题、答辩、业务汇报。**无需外部 API，离线可用**（本机 python-pptx 落地）。详见该目录内 `SKILL.md`。

## 二、科研与文献

- [`ima-kb-rename-table/`](./ima-kb-rename-table/) — **ima 知识库 / 本地 PDF·Word 批量改名对照表**
  为 ima 知识库（无重命名 API）或本地磁盘 PDF/Word 批量提取论文/报告标题，生成「原文件名 → 建议改名」对照表（CSV/XLSX/HTML）；本地文件可进一步落地真实改名（带可回退日志）。覆盖递归列举、内容抽取、打分/版面定位标题、符号清洗、误抓护栏、同名配对、诊断量化全流程。详见该目录内 `README.md` 与 `SKILL.md`。

- [`translate-pdf-to-zh-docx/`](./translate-pdf-to-zh-docx/) — **英文学术 PDF → 中文 Word 翻译管线**
  将英文（或其他语种）学术 PDF 翻译为结构化中文 `.docx`：保留标题层级与段落衔接、图片原位嵌入、表格真实翻译、显示公式干净截图，并剥离页眉页脚噪声。质量接近 Google 翻译，适配中国大陆网络（本地代理 + MyMemory 兜底）。详见该目录内 `README.md` 与 `SKILL.md`。

- [`md-survey-to-docx/`](./md-survey-to-docx/) — **学术 Markdown → Word（引用转 GB/T 7714 上角标）**
  把学术 Markdown 稿件（综述/论文）转成 `.docx`，并把 `[论文标题]` 式内联引用统一换成 **GB/T 7714 顺序编码制的数字上角标**（如 `[6]`），自动校验引用与参考文献编号一一对应。详见该目录内 `SKILL.md`。

## 三、实验室管理与 WorkBuddy 平台工具

- [`lab-os-agent/`](./lab-os-agent/) — **实验室 OS Agent（导师管理驾驶舱 + 学生培养陪跑）**
  面向高校实验室的**本地化学生管理 Agent 操作手册**（自包含：含 15 份框架知识库 `frameworks/` 与可运行教学原型 `world_model_lab/`）。核心为 **双端口**（导师「管理驾驶舱」+ 学生「培训陪跑」）、**多专家编排**（Router + 技术/情绪/制度/信念/能力/实验 6 专家）、**职能委员体系**（9 委员 ↔ Agent 能力映射）、**多模态感知层**、**物理 AI 研究北极星**（P1–P4）与**实验室世界模型**（管理元框架）。已泛化为通用版：路径相对化、身份脱敏、模型后端可插拔（本地 Ollama / deepseek / qwen / zhipu）。详见该目录内 `SKILL.md`。

- [`lab-os-agent-builder/`](./lab-os-agent-builder/) — **实验室 OS Agent 构建方法论**
  沉淀该体系的**构建方法论 / 协作纪律 / 演进时间线**（双端口 → 六专家 → 九委员 → 多模态感知 → 物理 AI → 管理世界模型）、关键纠偏，以及可复用工作流（edge-tts 配音视频、国奖级架构图、双区帧、学生包打包）。当需要扩展、复述或续做该体系及推广物料时加载。详见该目录内 `SKILL.md`。

- [`wb-skill-load-verify/`](./wb-skill-load-verify/) — **WorkBuddy Skill 真机加载验证器**
  发布 / 上架前对 Skill 做真机加载体检：解析 frontmatter、校验目录名与 `name` 一致、按支持中文文件名的规则核对全部相对路径引用、交叉核对 `frameworks` 物理文档与显式引用，并检测 `__pycache__` 再生作为「已被 WorkBuddy 加载器扫描」的动态证据。脚本：`scripts/verify_skill_load.py <skill目录> [--install]`。详见该目录内 `SKILL.md`。

- [`wb-expert-package-build/`](./wb-expert-package-build/) — **WorkBuddy Expert 包制作流程**
  把已有资料 / 方法论（文档、`SKILL.md`、框架知识库、提示词）转化为可上架专家中心的 **Expert 包**，串联 `init → validate → register → package` 全流程，内附字段硬规则与 Windows 实操踩坑清单。是 builtin `expert-manager` 的实操补充。详见该目录内 `SKILL.md`。

- [`workbuddy-workspace-4011-fix/`](./workbuddy-workspace-4011-fix/) — **修复 WorkBuddy 4011 工作空间报错**
  诊断并修复报错 4011「Conversation workspace does not exist or was removed」。典型根因是工作空间目录被移动 / 重命名而会话记录的旧路径失效；修复首选在原路径建**目录联接（Junction）**指回新位置，**不移动任何文件且可逆**。详见该目录内 `SKILL.md`。

- [`github-skill-repo-sync/`](./github-skill-repo-sync/) — **技能同步到本仓库的流程**
  把本机 `~/.workbuddy/skills/` 下的技能同步到 `phxjchina/SkillRepository`（main）：ghproxy 只读镜像 clone、复制、commit、GCM 免 PAT 推送；并含 **github.com 被墙时改走 GitHub Data API 增量推送**的兜底脚本 `scripts/api_push_assets.py`。详见该目录内 `SKILL.md`。

- [`hermes-agent-install/`](./hermes-agent-install/) — **Hermes Agent 本地安装（国内 Windows 网络）**
  在本机安装 `NousResearch/hermes-agent`：ZIP 法绕过 `git clone` 被墙、Python 3.11–3.13（**不支持 3.14**）约束、venv 重建坑、`pyproject.toml` 目录要求，以及改用免费模型提供方（Ollama 本地 / Kimi 免费额度）避开付款页。详见该目录内 `SKILL.md`。

---

## 专家（Expert）

除技能外，本仓库还收录可直接安装到 WorkBuddy 专家中心的**专家包**：

- [`graduation-supervisor/`](./graduation-supervisor/) — **毕业设计监督导师（专家包）**
  把 `graduation-design-advisor` 技能封装为常驻**专家角色**（Agent 型，分类：项目质量）：内嵌该技能副本、专家人设与工作流（`agents/graduation-supervisor.md`）、头像及 `.codebuddy-plugin/plugin.json` 清单，自包含、开箱即用。安装后即可以「毕业设计监督导师」身份对话，代您监督学生并审核每个阶段性成果。详见该目录内 `README.md`。

- `graduation-coach.zip`（发布包）— **毕业设计辅导教练（学生端专家包）**
  把 `graduation-design-coach` 技能封装为面向学生的常驻专家（Agent 型，分类：项目质量）。**学生获取方式**：下载本仓库中的 zip（或老师发的群文件）→ WorkBuddy 专家中心 → 导入/安装 → 对话里 @「毕业设计辅导教练」即可开始七阶段陪跑。源码目录见 [`graduation-design-coach/`](./graduation-design-coach/)。

- `lab-os-architect.zip`（发布包）— **实验室管理体系架构师（专家包）**
  把 `lab-os-agent` 的**方法论**（双端口、六专家、9 委员映射、多模态感知、物理 AI P1–P4、世界模型元框架）提炼为常驻**专家角色**（Agent 型，分类：运营人力 09-OperationsHR）：面向高校实验室导师，提供体系诊断、架构设计与分阶段落地路线。**使用方式**：下载 zip → WorkBuddy 专家中心 → 导入 / 安装 → 对话里 @「实验室管理体系架构师」即可。源码技能见 [`lab-os-agent/`](./lab-os-agent/)。

## 安装方法

把本仓库克隆到本地，再将需要的技能目录复制到：

- **用户级**（跨项目可用）：`~/.workbuddy/skills/<skill-name>/`
- **项目级**（随仓库共享）：`<项目>/.workbuddy/skills/<skill-name>/`

复制完成后，**重载 WorkBuddy（或新开一个会话）**，技能即出现在可用技能列表。
专家包则是：下载 `*.zip` → WorkBuddy 专家中心「导入 / 安装」。

## 贡献 / 完善

欢迎 **Fork** 本仓库 → 修改对应技能的 `SKILL.md`（或补充 `scripts/`、`references/` 资源）→ 提交 **Pull Request**，改进会回流到本仓库，惠及所有人。
