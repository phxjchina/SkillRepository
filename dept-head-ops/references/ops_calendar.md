# 系主任运营 · 周期任务矩阵与自动化配置

> 配套 `dept-head-ops` 技能 §十二。本文档给出现役 7 类周期任务的完整参数，以及 WorkBuddy 自动化（automation）创建命令、企业微信配置步骤。目标：**让副主任/委员被系统周期驱动，让主任被系统反向 push。**

---

## 一、周期任务矩阵（运维总表）

| # | 任务     | 频率   | 触发时间       | 系统动作（脚本/产出）                          | 推送通道         | 责任人 / 知会 | 升级路径        |
| - | ------ | ---- | ---------- | ------------------------------------ | ------------ | -------- | ----------- |
| 1 | 排课推进检查 | 每周   | 周一 09:00   | `push_task.py weekly`：扫台账排课任务，未启动则提醒 | 群 @曹 + 知会主任  | 曹敬馨 / 彭  | 未启动→周二再催    |
| 2 | 推进会准备  | 每月   | 25 日 15:00 | `push_task.py monthly`：下月预排 + 材料清单   | 群 + 主任私推     | 各牵头人 / 彭 | 推进会当日收纪要    |
| 3 | 待拍板扫描  | 每工作日 | 08:30      | `push_task.py scan`（待拍板部分）→ 反向推主任    | **主任私推**     | 彭寒       | 积压>3天→升级约谈  |
| 4 | 逾期扫描   | 每日   | 09:00      | `push_task.py scan`（逾期部分）→ 推主任+群@责任人 | 群 + 主任私推     | 责任人 / 彭  | 逾期1天起→约谈+考核 |
| 5 | 党支部月度  | 每月   | 1 日 09:00  | `push_task.py party`：扫 T7 未勾选项       | 群 @书记 + 知会主任 | 书记 / 彭   | 滞后→转 T6 督办  |
| 6 | 学期排课启动 | 每学期  | 期末         | 派 T6 给曹（`add`）                       | 群 @曹         | 曹 / 彭    | —           |
| 7 | 临时派活   | 随时   | 主任触发       | `push_task.py add`：写入台账+推送           | 群 @责任人       | 责任人 / 彭  | 到期前2天软催     |

> 通道说明：群 = `DEPT_WEBHOOK`（系部工作群机器人）；主任私推 = `HEAD_WEBHOOK`（彭老师私人推送机器人）。未配置 webhook 时全部降级为本地 `state/last_push.md`，可先空跑验证。

---

## 二、WorkBuddy 自动化创建参数（automation_update）

> 在 WorkBuddy 自动化面板用以下参数创建；或让本助手执行"把排课周提醒建上"等指令即可。cwds 统一填技能目录：`C:/Users/Administrator/.workbuddy/skills/dept-head-ops`。
>
> **运行时说明（重要）**：本机托管 Python（`C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe`）缺少标准库 `Lib`，无法执行脚本；按"凡需脚本优先用 Node"的约定，以下自动化统一改用 Node 版脚本 `scripts/push_task.js`，由托管 Node 运行：  
> `C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-5/node.exe "C:/Users/Administrator/.workbuddy/skills/dept-head-ops/scripts/push_task.js" <命令>`。  
> 原 `scripts/push_task.py` 仍保留，仅作参考；其语法/逻辑与 `.js` 等价。

### 自动化 1 · 每日逾期扫描（核心反向 push，每日 09:00）

- mode: create
- name: 系部每日逾期扫描（反向push主任+群催责任人）
- scheduleType: recurring
- rrule: `FREQ=DAILY;BYHOUR=9;BYMINUTE=0`
- status: ACTIVE
- prompt（自包含）：
  ```
  用 Bash 执行
  "C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-5/node.exe"
  "C:/Users/Administrator/.workbuddy/skills/dept-head-ops/scripts/push_task.js" scan --only overdue
  读取 state/backlog.csv，把逾期任务反向推彭老师（HEAD_WEBHOOK）+ 在群 @ 责任人（DEPT_WEBHOOK）；未配置 webhook 时落盘 state/last_push.md。
  向彭老师汇报：今日几项逾期、分别是哪些（编号/责任人/任务/原截止/逾期天数）。若提示 [local] 说明未配置 webhook，提示按 §三 配置。
  ```

### 自动化 2 · 每工作日待拍板扫描（反向 push，工作日 08:30）

- name: 系部每工作日待拍板扫描（反向push主任）
- scheduleType: recurring
- rrule: `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=8;BYMINUTE=30`
- status: ACTIVE
- prompt：
  ```
  用 Bash 执行 node push_task.js scan --only waiting（Node 路径同上）。
  把"待拍板"任务反向推彭老师；积压>3天在推送里特别提醒"请今日拍板"。
  向彭老师汇报：几项待拍板、分别是哪些、是否有积压超 3 天需今日拍板。未配置 webhook 提示按 §三 配置。
  ```

### 自动化 3 · 每周排课推进（周一 09:00）

- name: 系部每周排课推进（周一催曹敬馨）
- scheduleType: recurring
- rrule: `FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0`
- status: ACTIVE
- prompt：
  ```
  用 Bash 执行 node push_task.js weekly（Node 路径同上）。
  扫"排课"在途任务，群 @ 曹敬馨催进度，并私推彭老师周报+健康度看板；无在途排课时提示启动 T1 摸底。
  向彭老师汇报检查结果并简述执行结果。未配置 webhook 提示按 §三 配置。
  ```

### 自动化 4 · 每月推进会准备（25 日 15:00）

- name: 系部每月推进会准备（25日15:00）
- scheduleType: recurring
- rrule: `FREQ=MONTHLY;BYMONTHDAY=25;BYHOUR=15;BYMINUTE=0`
- status: ACTIVE
- prompt：
  ```
  用 Bash 执行 node push_task.js monthly（Node 路径同上）。
  生成下月预排+推进会清单，推群并知会彭老师+健康度看板。
  向彭老师汇报清单已生成（含待拍板数）并简述执行结果。未配置 webhook 提示按 §三 配置。
  ```

### 自动化 5 · 党支部月度提醒（每月 1 日 09:00）

- name: 党支部月度工作提醒（每月1日09:00）
- scheduleType: recurring
- rrule: `FREQ=MONTHLY;BYMONTHDAY=1;BYHOUR=9;BYMINUTE=0`
- status: ACTIVE
- prompt：
  ```
  用 Bash 执行 node push_task.js party（Node 路径同上）。
  核对党支部 T7 本月应完成项，群 @ 党支部书记提醒并知会彭老师。
  向彭老师汇报提醒已生成（在途党建任务数/清单，或提示书记核对 T7）并简述执行结果。未配置 webhook 提示按 §三 配置。
  ```

> 矩阵中的「学期排课启动」（任务 6）与「临时派活」（任务 7）为手动/一次性触发，不建定时自动化；由主任一句"启动下学期排课"或"把 XX 派给 XX"触发 `push_task.js add`，再由对应周期扫描自然纳入督办。

---

## 三、企业微信配置步骤（一次性）

### 步骤 A：建群机器人（系部工作群）

1. 打开企业微信系部工作群 → 右上角「···」→「群机器人」→「添加机器人」。
2. 命名如「系部运营助手」，创建后复制 **Webhook 地址**（形如 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx`）。
3. 把该地址填入 `scripts/push_task.js`（自动化实际调用）或 `scripts/push_task.py` 顶部 `CONFIG["DEPT_WEBHOOK"]`。

### 步骤 B：建私人推送机器人（反向 push 主任）

1. 新建一个只有你自己的群（或企业微信「我的推送」类机器人），同样添加群机器人。
2. 复制 Webhook 填入 `CONFIG["HEAD_WEBHOOK"]`。该通道只推"待你拍板/逾期预警/运营看板"给你本人。

### 步骤 C：填成员 userid（用于 @）

- 在企业微信通讯录查看各副主任/委员的 **账号（userid）**，填入 `CONFIG["USER_MAP"]`：


  ```python
  "USER_MAP": {
      "张晓丽": "zhangxiaoli",   # 改成真实 userid
      "曹敬馨": "caojingxin",
      "侯媛媛": "houyuanyuan",
      "范文娜": "fanwenna",
      "宋飞": "songfei",
      "薛杉": "xueshan",
      "金聪": "jincong",
      "贾楠": "jianan",
      "党支部书记": "xxx",
  }
  ```
- 没填 userid 也不会报错：脚本退化为「【姓名】」文本点名（不 @），照常推送。

### 步骤 D：验证

```bash
# 先空跑（不配 webhook 也行，会落盘 last_push.md）。自动化用 Node 版：
NODE="C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-5/node.exe"
"$NODE" "C:/Users/Administrator/.workbuddy/skills/dept-head-ops/scripts/push_task.js" add --owner 曹敬馨 --task "测试推送：回收教师意愿摸底" --due 2026-10-10 --deliver "T1回收表"
"$NODE" "C:/Users/Administrator/.workbuddy/skills/dept-head-ops/scripts/push_task.js" scan
# 或等价用参考版 Python：python push_task.py add ... / scan
```

看到 `state/last_push.md` 生成即链路通；配好 webhook 后手机即收消息。

---

## 四、日常用法速记

| 场景       | 主任说一句                   | 系统做            |
| -------- | ----------------------- | -------------- |
| 学院临时通知某活 | "把学院XX通知派给张晓丽，下周五前交报告"  | `add` 入台账+推张晓丽 |
| 想看全局     | "今天有什么要我拍板的/逾期的"        | `scan` 出看板推你   |
| 每周一自动    | （无需操作）                  | `weekly` 催曹敬馨  |
| 每月25日自动  | （无需操作）                  | `monthly` 备推进会 |
| 每月1日自动   | （无需操作）                  | `party` 催党支部书记 |
| 成果提交待拍板  | 曹回"排课初稿好了" → 主任说"标记待拍板" | 次日 `scan` 推你拍板 |

> **权责边界**：台账里每一条都带 owner + due + supervisor。系统只催不代做；催而不动 → 逾期 → 约谈 → 考核，这条红线自动生效，主任不必亲自盯。
