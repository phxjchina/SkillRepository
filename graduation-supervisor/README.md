# 毕业设计监督导师（Graduation Design Supervisor）

代替指导教师**全程跟踪**本科毕业设计（论文）推进，并对每个阶段成果做结构化审查与 Word 批注，守住抽检红线。西安航空学院计算机学院模板。

## 类型
Agent 型（单个 AI 专家）

## 核心能力
1. **队列驾驶舱**：扫描本地 .docx 原件，生成整届进度看板（谁到哪步 / 谁卡住 / 谁缺材料）。
2. **单人下钻精审**：任务书 / 开题报告 / 论文逐条审查，注入可编辑 Word 批注。
3. **阶段进度跟踪**：9 阶段状态卡 + 跨会话进度记忆 + 主动预警。
4. **抽检红线守护**：对照《陕西省本科毕业设计（论文）抽检评价要素》。

## 随附技能
`skills/graduation-design-advisor/` —— 含完整审查清单（任务书29/开题30/论文53/外文20/意见3/常见9类/抽检要素）、五条跨文档铁律、三个脚本：
- `supervision_cockpit.py`：队列驾驶舱看板生成
- `review_docx.py` / `review_thesis.py`：单文档结构初筛（已修复表格内正文读取）
- `inject_comments.py`：Word 真批注注入（追加模式，不覆盖原批注）

## 使用示例
- "生成本届毕业设计监督驾驶舱进度看板，列出谁卡在哪个阶段、谁缺材料"
- "审查并给这位同学的开题报告注入 Word 批注"
- "检查一下本周谁还没交阶段成果、需要我催谁"

## 头像
`avatars/graduation-supervisor.png`（由 ImageGen 生成，可手动替换为 512×512 PNG/JPG ≤500KB）

## 安装 / 注册
专家已置于专家目录 `…/my-experts/plugins/graduation-supervisor/`，并已写入 `marketplace.json`，在 WorkBuddy 专家中心「我的专家」可见。
