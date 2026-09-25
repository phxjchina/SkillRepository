# 学生档案 Schema（实验室 OS 双端口共享数据载体）

> 角色：导师端口与学生端口**共享同一份本地档案**；是六大专家读写学生状态的唯一事实源。
> 存储：本地 JSON / Markdown，零云端依赖，隐私不出本机（契合护栏第 4 条）。
> 命名：`/workspace/lab-data/students/<学号>.json`（或同名 .md 便于人工审阅）。
> 维护方：路由 Agent 分发后，对应专家**只写自己那块字段**，互不覆盖（避免跨域写脏）。

---

## 一、字段定义（JSON Schema 中文释义）

```json
{
  "student_id": "学号（字符串，唯一主键）",
  "name": "姓名",
  "meta": {
    "grade": "年级：大一 / 大二 / 大三 / 大四",
    "major_direction": "专业方向：软件 / 嵌入式 / 物联网 / 智能",
    "priority_path": "主攻 P 级路径：P1 / P2 / P3 / P4（默认从 P1 起）",
    "entered_lab": "入实验室日期 YYYY-MM-DD",
    "status": "在培 / 考研 / 考公 / 毕业",
    "mentor": "归属教师：彭老师 / QQ老师 / H老师"
  },

  "tech": {
    "current_P": "当前主攻 P 级",
    "completed_modules": ["已完成能力模块（来自技术架构 §1 的 4 域×模块）"],
    "current_task": { "task_id": "任务卡 ID", "title": "任务名", "due": "截止日" },
    "code_reviews": [ { "date": "YYYY-MM-DD", "verdict": "通过/修改/交教师", "note": "评审摘要" } ],
    "blocker": "卡点：无 / P4攻坚 / 环境缺失（供能力专家与导师端口预警）"
  },

  "emotion": {
    "current_state": "学生主动自述状态（来自情绪地图卡/周报滑条）；沉默型可空",
    "inferred_state": "被动行为信号推断状态（置信度见下）；与 current_state 并列、互不覆盖",
    "inferred_confidence": "0.0–1.0；越低越需谨慎，仅供教师参考",
    "signal_source": "推断依据信号层：L1产出 / L2制度 / L3交互 / L4 peer",
    "behavioral_signals": {
      "commit_freq_7d": "近 7 天代码提交次数（长期 0 偏高关注）",
      "task_stuck_days": "当前任务卡壳天数",
      "weekly_report_status": "已交 / 迟交 / 缺交",
      "milestone_delay": "里程碑延期天数（0 为按期）",
      "review_rework_rate": "代码评审返工率 0–1",
      "agent_idle_days": "与 Agent 无交互天数"
    },
    "trajectory": [ { "week": "YYYY-Www", "state": "A–E/推断", "source": "自述/推断", "note": "波动备注" } ],
    "flag": "正常 / 关注 / 异常(已上报教师)",
    "last_signal_date": "最近一次行为信号采集日期",
    "autonomy_note": "自主性备注：同一刺激下响应不可预设；推断非事实、带置信度、可纠偏"
  },

  "belief": {
    "change_anchor": "三个改变之一：改变自己 / 改变环境 / 改变世界",
    "ladder_level": "七层阶梯位置：L0–L6",
    "coordinate_text": "学生自填坐标：'我在 L_ 层，借 ___ 改变 ___'"
  },

  "ability": {
    "stage": "训练四阶段之一：启蒙 / 训练 / 产出 / 闭环",
    "semester": "第几学期（1–8）",
    "next_milestone": { "title": "下一里程碑", "due": "达成日" }
  },

  "governance": {
    "attendance": "考勤状态：正常 / 弹性达标 / 预警",
    "weekly_report": { "last_date": "最近周报日期", "status": "已交 / 未交 / 迟交" },
    "violations": [ { "date": "YYYY-MM-DD", "type": "违规类型", "handled_by": "教师处置结论" } ],
    "warnings": [ "待处理预警条目" ]
  },

  "products": {
    "doing": [ { "product_id": "来自 AIOPC学生项目规划 的编号", "name": "产品名", "P": "主P级" } ],
    "mvp_stage": "雏形 / 内测 / 可演示"
  },

  "log": [
    { "ts": "ISO 时间戳", "port": "导师/学生", "expert": "技术/情绪/制度/信念/能力/实验", "action": "动作摘要" }
  ]
}
```

---

## 二、示例学生档案（试点用）

```json
{
  "student_id": "20230101",
  "name": "张同学",
  "meta": {
    "grade": "大二",
    "major_direction": "智能",
    "priority_path": "P1",
    "entered_lab": "2026-03-01",
    "status": "在培",
    "mentor": "彭老师"
  },
  "tech": {
    "current_P": "P1",
    "completed_modules": ["信息处理系统/基础编程", "信息处理系统/Web 入门"],
    "current_task": { "task_id": "T-20260101-03", "title": "实验室管理智能体(学生版) 前端原型", "due": "2026-09-20" },
    "code_reviews": [ { "date": "2026-09-10", "verdict": "修改", "note": "接口未对齐后端 schema" } ],
    "blocker": "无"
  },
  "emotion": {
    "current_state": "投入",
    "inferred_state": "投入（置信度 0.82，依据 L1 提交稳定 + L2 周报已交）",
    "inferred_confidence": 0.82,
    "signal_source": "L1产出 / L2制度",
    "behavioral_signals": {
      "commit_freq_7d": 9,
      "task_stuck_days": 0,
      "weekly_report_status": "已交",
      "milestone_delay": 0,
      "review_rework_rate": 0.2,
      "agent_idle_days": 1
    },
    "trajectory": [ { "week": "2026-W36", "state": "唤醒", "source": "自述", "note": "任务初接手" }, { "week": "2026-W37", "state": "投入", "source": "推断", "note": "提交稳定+周报已交，L1/L2 信号一致" } ],
    "flag": "正常",
    "last_signal_date": "2026-09-14",
    "autonomy_note": "对 P1 任务自评较高，未强推 P4；推断与自述一致"
  },
  "belief": {
    "change_anchor": "改变自己",
    "ladder_level": "L1",
    "coordinate_text": "我在 L1 层，借实验室管理智能体改变自己的工程能力"
  },
  "ability": {
    "stage": "训练",
    "semester": "4",
    "next_milestone": { "title": "完成 P1 外壳并接入 Bonsai 推理", "due": "2026-09-30" }
  },
  "governance": {
    "attendance": "正常",
    "weekly_report": { "last_date": "2026-09-08", "status": "已交" },
    "violations": [],
    "warnings": []
  },
  "products": {
    "doing": [ { "product_id": "1", "name": "实验室管理智能体(学生版)", "P": "P1外壳+P4内核" } ],
    "mvp_stage": "内测"
  },
  "log": [
    { "ts": "2026-09-11T15:20:00", "port": "学生", "expert": "技术", "action": "派发任务卡 T-20260101-03" },
    { "ts": "2026-09-11T15:25:00", "port": "学生", "expert": "信念", "action": "锚定'改变自己'坐标" }
  ]
}
```

---

## 三、读写约定（写入系统 prompt）

1. **单一事实源**：专家不各自存副本，统一读写本档案对应字段段。
2. **分域写**：技术专家只写 `tech`、情绪专家只写 `emotion`……避免互相覆盖。
3. **日志必记**：任何端口/专家的关键动作都追加一条 `log`，便于导师端口聚合与回滚。
4. **异常上报**：`emotion.flag` 置"异常(已上报教师)"时，立即触发推送（见 `实验室OS自动化配置.md`）。
4.5. **行为信号为只读派生**：`behavioral_signals` 由 cron 从 git/周报/任务卡/评审聚合写入（见自动化配置信号采集说明）；情绪专家据其写 `inferred_state`，**不回写任何私密数据**；`current_state` 与 `inferred_state` 并列、互不覆盖。
5. **本地化**：文件仅存 `/workspace/lab-data/`，不上云、不外传；导师端口聚合视图不得向学生端口泄露 `governance`/`emotion` 的个体评价细节（护栏第 6 条）。

---

*由 WorkBuddy 据《实验室 OS Agent 架构方案》§四/§五 补全 · v1.0 · 待部署*
