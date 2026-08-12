# ima-kb-rename-table

为 **ima 知识库（无重命名 API）** 下某一大类的 PDF 批量提取论文/报告标题，生成「原文件名 → 建议改名」对照表（CSV / XLSX / HTML）。

覆盖完整工作流：递归列举 → 候选标题 → 全文缓存 → 打分提取标题 → 符号清洗 → 落盘 → 校验修复 → 重生成交付物。

## 为什么需要它

ima 知识库没有重命名 API，无法批量改文件名。本技能把"该改成什么名字"这件事做成一张**建议改名对照表**，由人工在 ima 里按列对照手动改名。核心价值在于：从一堆乱七八糟的 PDF 原文件名（如 `1-s2.0-S0164121222000553-main.pdf`、`FULLTEXT01.pdf`）中，自动提取出语义完整的论文/报告标题。

## 安装

**方式 A：用户级（跨所有项目）**
把本目录（重命名为 `ima-kb-rename-table`）放到：
```
~/.workbuddy/skills/ima-kb-rename-table/
```
重启 / 新开 WorkBuddy 会话即自动加载。

**方式 B：项目级（随仓库共享给协作者）**
放到项目仓库内：
```
<你的项目>/.workbuddy/skills/ima-kb-rename-table/
```
协作者 clone 后自动获得。

## 使用

对会话说类似：「用 ima-kb-rename-table 技能，处理我 ima 知识库里 XX 大类的 PDF，生成改名对照表」。技能会自动跑完 8 个阶段并产出四件交付物（xlsx / html / csv / 两列 csv）。

## 如何完善这个技能（欢迎 PR）

本技能是为「另一实例的 CodeBuddy / WorkBuddy」写的，重点沉淀**非显而易见的过程性知识**。改进方向：

1. **Fork / Clone 本仓库**
2. 编辑 `SKILL.md`（或补充 `scripts/`、`references/` 资源文件）
3. 提交 Pull Request

常见可改进点：
- 不同语言 PDF（法文 HAL、德文、中文）的标题提取规则
- 更多"作者尾注粘连 / 出版商页脚垃圾 / 截断误判"的识别模式
- 置信度打分模型的权重调优
- 新版 ima 连接器接口变化时的适配

## 目录结构

```
ima-kb-rename-table/
├── SKILL.md      # 技能本体（核心）
├── README.md     # 本文件
└── .gitignore
```

## License

MIT —— 可自由使用、修改、再分发。
