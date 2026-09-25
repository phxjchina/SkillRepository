# 实验室 OS 自动化配置（触发器 + 推送模板）

> 角色：把《实验室 OS Agent 架构方案》§四"主动自动化机制"从**表格描述**落成**可部署配置 + 现成文案模板**。
> 依赖宿主：定时/事件触发需 WorkBuddy 自动化 task manager 或本地 cron/系统日历。本文件给出两种形态的配置，按宿主二选一接入。
> 推送对象：彭老师（导师端口）；部分动作同时抄送相关学生。

---

## 一、定时任务配置

### 1.1 本地 cron 形态（Linux / macOS，直接可用）

```cron
# 实验室 OS Agent —— 导师端口主动推送（彭老师时区 GMT+8）
# 每周一 09:00 周报催收 + 上周未交名单聚合
0 9 * * 1  cd /workspace && python3 lab-os/cron_push.py --job weekly_report --to mentor >> lab-data/logs/cron.log 2>&1

# 每里程碑日 08:30 进度检查 + 风险标红（由 lab-os 读学生档案 next_milestone 计算到期）
30 8 * * * cd /workspace && python3 lab-os/cron_push.py --job milestone_check --to mentor >> lab-data/logs/cron.log 2>&1

# 每周日 20:00 情绪周度复盘（聚合本周学生对话 → 态势）
0 20 * * 0 cd /workspace && python3 lab-os/cron_push.py --job emotion_review --to mentor >> lab-data/logs/cron.log 2>&1

# 每月 1 日 09:00 能力雷达更新（P1–P4 进度分布）
0 9 1 * * cd /workspace && python3 lab-os/cron_push.py --job ability_radar --to mentor >> lab-data/logs/cron.log 2>&1
```

> `cron_push.py` 为推送执行脚本占位：读取 `lab-data/students/*.json` → 按 job 聚合并调用推送通道（WorkBuddy 设备推送 / 邮件 / 微信）。部署阶段按您现有通道接入。

### 1.2 WorkBuddy 自动化 task 形态（JSON 配置，挂自动化-task-manager）

```json
{
  "lab_os_automation": {
    "timezone": "Asia/Shanghai",
    "tasks": [
      {
        "id": "weekly_report",
        "schedule": "0 9 * * 1",
        "port": "mentor",
        "action": "聚合 lab-data 中所有 weekly_report.status!=已交 的学生，生成未交名单",
        "push_template": "TPL_WEEKLY_REPORT",
        "to": "彭老师"
      },
      {
        "id": "milestone_check",
        "schedule": "30 8 * * *",
        "port": "mentor",
        "action": "遍历 next_milestone.due<=今日+3天 的学生，标红延期/卡壳",
        "push_template": "TPL_MILESTONE",
        "to": "彭老师"
      },
      {
        "id": "emotion_review",
        "schedule": "0 20 * * 0",
        "port": "mentor",
        "action": "聚合本周行为信号（提交/任务卡/周报/产出 L1–L4）+ 对话，推断情绪态势（关注/异常单独置顶）",
        "push_template": "TPL_EMOTION",
        "to": "彭老师"
      },
      {
        "id": "ability_radar",
        "schedule": "0 9 1 * *",
        "port": "mentor",
        "action": "统计 P1–P4 各阶段人数分布，生成能力雷达摘要",
        "push_template": "TPL_ABILITY",
        "to": "彭老师"
      }
    ],
    "event_hooks": [
      {
        "event": "student_submit_weekly",
        "action": "批阅合规 + 触发信念专家成就锚定（TPL_ACHIEVE 学生侧）"
      },
      {
        "event": "emotion_flag_anomaly",
        "action": "立即推送 TPL_EMOTION_ALERT 给彭老师，不自行处理（护栏第2条）"
      },
      {
        "event": "governance_violation",
        "action": "制度专家记录 + 推送 TPL_GOV_WARN 给彭老师，不处罚（护栏第3条）"
      },
      {
        "event": "student_pick_product",
        "action": "实验专家按 P1–P4 派任务卡（见 AIOPC学生项目规划 §四）"
      }
    ]
  }
}
```

> **信号采集说明（被动情绪感知 · 见情绪体系 §3.5）**：`emotion_review` 与 `emotion_flag_anomaly` 的数据来源为**公开可观察的行为痕迹**，由 `cron_push.py` 从以下位置聚合——git/代码仓库提交记录（L1 产出）、任务卡与里程碑系统（L1/L2）、周报提交状态（L2）、代码评审返工率（L1）、与 Agent 的交互日志（L3）。**不读取私聊、私人文件、生理数据**。推断结论写入档案 `emotion.inferred_state` 并带 `inferred_confidence` 置信度，供导师端口参考而非定性。

---

## 二、推送 Prompt 模板（可直接套用）

> 约定：`{{ }}` 为变量占位，由聚合脚本从学生档案注入。语气学术、克制、不制造焦虑。

### TPL_WEEKLY_REPORT（周报催收 · 周一）
```
彭老师，本周实验室周报催收提醒：

✅ 已交（{{count_submitted}} 人）：{{names_submitted}}
⚠️ 未交（{{count_missing}} 人）：{{names_missing}}

建议：对连续 2 周未交者，由制度专家标记预警并转您处置。
—— 实验室 OS · 导师端口
```

### TPL_MILESTONE（里程碑预警）
```
彭老师，里程碑进度检查（{{date}}）：

🔴 延期/卡壳（{{count_risk}} 人）：
{% for s in risk %}- {{s.name}}：{{s.ability.next_milestone.title}} 原定 {{s.ability.next_milestone.due}}，卡点 {{s.tech.blocker}}
{% endfor %}
🟢 正常推进（{{count_ok}} 人）

提示：卡在 P4 攻坚者，建议技术专家降一档给外部刺激，避免动力缺失（见情绪体系"动力缺失/无动机"）。
—— 实验室 OS · 导师端口
```

### TPL_EMOTION（情绪周度复盘 · 周末）
```
彭老师，本周学生情绪态势复盘（{{week}}）：

（数据来源：被动行为信号推断 L1–L4 + 主动自述，详见学生档案 emotion 字段；置信度偏低者仅作参考）

总览：心流 {{n_flow}} · 投入 {{n_in}} · 唤醒 {{n_awake}} · 散乱 {{n_scatter}} · 共同体 {{n_comm}}
⚠️ 关注（{{n_watch}} 人）：{{names_watch}} —— 行为信号显示动力/投入走低，建议信念/情绪专家轻量介入（先关怀、不直报）
🔴 异常（{{n_anom}} 人）：{{names_anom}} —— 已按护栏上报，请您介入

说明：① 推断非事实、带置信度、学生可纠偏；② 情绪波动为自主性闭环正常现象，无需抹平；③ 仅"关注/异常"层级提示，沉默型学生由行为信号兜底覆盖。
—— 实验室 OS · 导师端口
```

### TPL_EMOTION_ALERT（情绪异常即时上报 · 事件）
```
🔴 彭老师，紧急：学生 {{name}} 对话出现情绪异常信号（{{signal}}）。
按护栏第2条，已停止自行处理并上报于您。
最近状态：{{emotion.current_state}} / 轨迹 {{emotion.trajectory}}
建议：请您直接介入或转介心理支持。
—— 实验室 OS · 情绪专家
```

### TPL_ABILITY（能力雷达 · 月初）
```
彭老师，本月能力雷达（{{month}}）：

P1 软件 {{n_p1}} 人 · P2 嵌入式 {{n_p2}} · P3 物联网 {{n_p3}} · P4 智能 {{n_p4}}
阶段分布：启蒙 {{n0}} · 训练 {{n1}} · 产出 {{n2}} · 闭环 {{n3}}

观察：{{insight}}（如"P1 转 P4 断层明显，建议补 P2/P3 过渡产品"）
—— 实验室 OS · 能力专家
```

### TPL_ACHIEVE（学生侧成就锚定 · 事件：交周报）
```
{{name}}，你这周的周报我读到了——

你推进的 {{tech.current_task.title}}，正是"改变自己"这一步的真实证据：
你在 L{{belief.ladder_level}} 层，借 {{products.doing[0].name|默认'实验室工作'}} 改变着自己的工程能力。
继续往前，下个里程碑是 {{ability.next_milestone.title}}。

记住那句话：在实验室，你改变自己；你做的每件事，正在改变环境；而你们这一代人，终将改变世界。
—— 实验室 OS · 信念专家
```

### TPL_GOV_WARN（制度预警 · 事件：违规/懈怠）
```
彭老师，制度预警：学生 {{name}} 于 {{date}} 出现 {{type}}（{{detail}}）。
已按制度专家记录，未自行处置。处置权在您。
历史：{{governance.violations}}
—— 实验室 OS · 制度专家
```

---

## 三、部署接线说明

1. **通道**：推送目标 `彭老师` 映射到您现有通道（WorkBuddy 设备推送 / 邮件 / 企业微信），部署时填 `cron_push.py` 的 `to` 实现。
2. **数据**：脚本读 `/workspace/lab-data/students/*.json`（见 `学生档案schema.md`）。
3. **护栏硬编码**：`emotion_flag_anomaly` / `governance_violation` 两个 hook 的"上报不处置"逻辑必须保留，不得被模板改写绕过。
4. **回滚**：所有定时动作先写 `lab-data/logs/cron.log` 再推送；误推送可据日志回溯，不复制整树。
5. **试点起步**：先挂 `weekly_report` + `milestone_check` 两条验证两周，再审阅调频（契合架构方案 §七 节奏）。

---

*由 WorkBuddy 据《实验室 OS Agent 架构方案》§四 补全 · v1.0 · 待部署*
