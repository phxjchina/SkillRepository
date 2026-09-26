# 系主任运营 · 周期任务矩阵与自动化配置

> 配套 `dept-head-ops` 技能 §十二。本文档给出现役 7 类周期任务的完整参数，以及 WorkBuddy 自动化（automation）创建命令、企业微信配置步骤。目标：**让副主任/委员被系统周期驱动，让主任被系统反向 push。**

---

## 一、周期任务矩阵（运维总表）

| # | 任务 | 频率 | 触发时间 | 系统动作（脚本/产出） | 推送通道 | 责任人 / 知会 | 升级路径 |
|---|---|---|---|---|---|---|---|
| 1 | 排课推进检查 | 每周 | 周一 09:00 | `push_task.py weekly`：扫台账排课任务，未启动则提醒 | 群 @曹 + 知会主任 | 曹敬馨 / 彭 | 未启动→周二再催 |
| 2 | 推进会准备 | 每月 | 25 日 15:00 | `push_task.py monthly`：下月预排 + 材料清单 | 群 + 主任私推 | 各牵头人 / 彭 | 推进会当日收纪要 |
| 3 | 待拍板扫描 | 每工作日 | 08:30 | `push_task.py scan`（待拍板部分）→ 反向推主任 | **主任私推** | 彭寒 | 积压>3天→升级约谈 |
| 4 | 逾期扫描 | 每日 | 09:00 | `push_task.py scan`（逾期部分）→ 推主任+群@责任人 | 群 + 主任私推 | 责任人 / 彭 | 逾期1天起→约谈+考核 |
| 5 | 党支部月度 | 每月 | 1 日 09:00 | `push_task.py party`：扫 T7 未勾选项 | 群 @书记 + 知会主任 | 书记 / 彭 | 滞后→转 T6 督办 |
| 6 | 学期排课启动 | 每学期 | 期末 | 派 T6 给曹（`add`） | 群 @曹 | 曹 / 彭 | — |
| 7 | 临时派活 | 随时 | 主任触发 | `push_task.py add`：写入台账+推送 | 群 @责任人 | 责任人 / 彭 | 到期前2天软催 |

> 通道说明：群 = `DEPT_WEBHOOK`（系部工作群机器人）；主任私推 = `HEAD_WEBHOOK`（彭老师私人推送机器人）。未配置 webhook 时全部降级为本地 `state/last_push.md`，可先空跑验证。

---

## 二、WorkBuddy 自动化创建参数（automation_update）

> 在 WorkBuddy 自动化面板用以下参数创建；或让本助手执行"把排课周提醒建上"等指令即可。cwds 统一填技能目录：`C:/Users/Administrator/.workbuddy/skills/dept-head-ops`。

### 自动化 1 · 每日逾期+待拍板扫描（核心反向 push）
- mode: create
- name: 系部每日运营扫描（逾期+待拍板）
- scheduleType: recurring
- rrule: `FREQ=DAILY;BYHOUR=9;BYMINUTE=0`
- status: ACTIVE
- prompt（自包含）：
  ```
  运行系主任运营技能的去重扫描脚本：用 Bash 执行
  "C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe"
  "C:/Users/Administrator/.workbuddy/skills/dept-head-ops/scripts/push_task.py" scan
  该脚本会读取 state/backlog.csv，把逾期和"待拍板"任务通过企业微信推送（已配置 webhook 时）或落盘 state/last_push.md（未配置时）。
  运行后向彭老师汇报：今日有几项待拍板、几项逾期、分别是什么。若 webhook 未配置，提示先配置。
  ```

### 自动化 2 · 每周排课推进
- name: 系部每周排课推进
- scheduleType: recurring
- rrule: `FREQ=WEEKLY;BYDAY=MO;BYHOUR=9;BYMINUTE=0`
- status: ACTIVE
- prompt：
  ```
  运行 "C:/Users/Administrator/.workbuddy/skills/dept-head-ops/scripts/push_task.py" weekly
  （Python 用托管路径 C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe）。
  检查排课相关任务进度，推送提醒给曹敬馨并知会彭老师。汇报执行结果。
  ```

### 自动化 3 · 每月推进会准备
- name: 系部每月推进会准备
- scheduleType: recurring
- rrule: `FREQ=MONTHLY;BYMONTHDAY=25;BYHOUR=15;BYMINUTE=0`
- status: ACTIVE
- prompt：
  ```
  运行 push_task.py monthly，生成下月系部工作预排与推进会材料清单，推送给各牵头人并知会彭老师。
  Python 路径同上。汇报结果。
  ```

### 自动化 4 · 党支部月度提醒
- name: 党支部月度工作提醒
- scheduleType: recurring
- rrule: `FREQ=MONTHLY;BYMONTHDAY=1;BYHOUR=9;BYMINUTE=0`
- status: ACTIVE
- prompt：
  ```
  运行 push_task.py party，核对党支部年度台账（T7）本月应完成项，提醒党支部书记并知会彭老师。
  Python 路径同上。汇报结果。
  ```

> 自动化 6（学期排课启动）为一次性/手动，不建定时；由主任在期末一句"启动下学期排课"触发 `add`。

---

## 三、企业微信配置步骤（一次性）

### 步骤 A：建群机器人（系部工作群）
1. 打开企业微信系部工作群 → 右上角「···」→「群机器人」→「添加机器人」。
2. 命名如「系部运营助手」，创建后复制 **Webhook 地址**（形如 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx`）。
3. 把该地址填入 `scripts/push_task.py` 顶部 `CONFIG["DEPT_WEBHOOK"]`。

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
# 先空跑（不配 webhook 也行，会落盘 last_push.md）
python push_task.py add --owner 曹敬馨 --task "测试推送：回收教师意愿摸底" --due 2026-10-10 --deliver "T1回收表"
python push_task.py scan
```
看到 `state/last_push.md` 生成即链路通；配好 webhook 后手机即收消息。

---

## 四、日常用法速记

| 场景 | 主任说一句 | 系统做 |
|---|---|---|
| 学院临时通知某活 | "把学院XX通知派给张晓丽，下周五前交报告" | `add` 入台账+推张晓丽 |
| 想看全局 | "今天有什么要我拍板的/逾期的" | `scan` 出看板推你 |
| 每周一自动 | （无需操作） | `weekly` 催曹敬馨 |
| 每月25日自动 | （无需操作） | `monthly` 备推进会 |
| 每月1日自动 | （无需操作） | `party` 催党支部书记 |
| 成果提交待拍板 | 曹回"排课初稿好了" → 主任说"标记待拍板" | 次日 `scan` 推你拍板 |

> **权责边界**：台账里每一条都带 owner + due + supervisor。系统只催不代做；催而不动 → 逾期 → 约谈 → 考核，这条红线自动生效，主任不必亲自盯。
