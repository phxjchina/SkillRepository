#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_skeleton.py — 生成任务书/开题报告/论文 可填空骨架(.docx)
生成 Markdown 骨架（【】占位），并调工作区 md2docx.py 落地为 .docx。
用法:
  python gen_skeleton.py --kind task|opening|thesis --out 骨架.docx \
      [--student "姓名" --title "题目" --advisor "教师" --major "计算机科学2104"]
"""
import argparse, os, subprocess, sys, tempfile

MD2DOCX = os.environ.get("MD2DOCX", r"E:/培训所需软件/练习用材料/.workbuddy/md2docx.py")


def task_sk(a):
    return f"""# 本科毕业设计（论文）任务书（填空骨架）

> 使用学院官方模板（附件3）排版；本骨架只整理内容要点，最终以教师下发的正式任务书为准。

- 题目：{a.title or "【题目：基于<技术>的<对象>系统的设计与实现】"}
- 学生姓名：{a.student or "【姓名】"}　学号：【学号】　专业班级：{a.major or "【如 计算机科学2104，不含「班」字】"}　指导教师：{a.advisor or "【教师】"}
- 设计（论文）起止时间：【2025年12月X日 至 2026年6月X日（连接符全文统一，数字与汉字间不加空格）】

## 1 课题目标及要求
【目标：1-2句说清做出来的系统/方法解决什么问题】
【要求：拆成可验收条目——(1)功能指标… (2)性能指标… (3)技术指标…；不要与第2部分重复堆砌，不要一句话了事】

## 2 主要内容及成果形式
【主要内容：3-5条核心工作，每条一句话】
【成果形式：XX系统一套，毕业设计论文一份（禁用"系统说明书"）】

## 3 进度安排（6阶段，时间连续，终点=答辩日）
1. 【第1阶段 选题与调研 YYYY-MM-DD ~ YYYY-MM-DD】
2. 【第2阶段 开题 YYYY-MM-DD ~ YYYY-MM-DD】
3. 【第3阶段 方案设计与实现(上) YYYY-MM-DD ~ YYYY-MM-DD】
4. 【第4阶段 实现与测试(下) YYYY-MM-DD ~ YYYY-MM-DD】
5. 【第5阶段 论文撰写 YYYY-MM-DD ~ YYYY-MM-DD】
6. 【第6阶段 答辩 YYYY-MM-DD ~ YYYY-MM-DD（=学院通知答辩日）】

## 4 建议参考文献（≥5篇，近3年为主，≥1篇外文，与课题强相关）
[1] 【作者. 题名[J]. 刊名, 年, 卷(期): 起止页.】（作者≤3位全列，>3位列前3位加“,等”）
[2] 【外文示例：Zhang Y, et al. Title[J]. Journal, 2024, 12(3): 100-110.】

---
（三方手写签名：指导教师 → 教研室主任 → 学生，日期依次推后）
"""


def opening_sk(a):
    return f"""# 毕业设计（论文）开题报告（填空骨架 · 附件5）

> 封面"完成时间"必须填阿拉伯数字；题目与任务书一字不差（复制粘贴）。

- 题目：{a.title or "【题目】"}
- 学生姓名：{a.student or "【姓名】"}　专业班级：{a.major or "【专业班级】"}　指导教师：{a.advisor or "【教师】"}
- 完成时间：【2026年X月X日】

## 1 研究目的及意义
### 1.1 研究目的
【1段：本课题要解决的具体问题与要达到的目标】
### 1.2 研究意义
【1段：理论/实用价值，2-3句，别拔高】

## 2 国内外研究现状
### 2.1 国外研究现状
【列3-4项代表性工作：作者(年份)做了什么 → 每小节末必须有评述："然而现有工作在…上不足，本文从…切入"】
### 2.2 国内研究现状
【同上，3-4项+评述】

## 3 本课题要研究或解决的问题和拟采用的研究手段（篇幅必须>第1+2部分之和）
### 3.1 主要研究内容
【3-5条，每条展开2-3句：做什么、做到什么程度】
### 3.2 拟解决的关键问题
【2-3个技术难点，说明为什么难】
### 3.3 拟采用的研究手段（技术路线）
【开发环境/语言/框架/算法/硬件选型 + 技术路线图(图1) + 为什么这么选】
（注意：研究手段必须与任务书"使用工具"一致——铁律④）

## 4 工作进度安排
【与任务书6阶段逐条一致，复制任务书第3部分再核对起止日——铁律②】

## 参考文献（≥10篇，≥2篇外文，80%近3年，含任务书全部文献，去重）
[1] 【…】
[2] 【…】

> 交前自查：无残留模板提示文字、无错别字漏字（通读一遍）、图有图题置于图下方。
"""


def thesis_sk(a):
    return f"""# 毕业设计（论文）（填空骨架）

- 题目：{a.title or "【题目】"}　学生：{a.student or "【姓名】"}　指导教师：{a.advisor or "【教师】"}

## 摘要
【五要素各1-2句：目的→内容→方法→成果→结论；≤500字；不写心得体会】
关键词：【词1】；【词2】；【词3】；【词4】（3-5个，分号分隔）

## Abstract
【与中文摘要对应的英文；另起一页；Times New Roman】
Key words: 【kw1; kw2; kw3】

## 目录
（由Word自动生成，定稿前核对与正文标题逐条一致、章号连续）

## 1 绪论
### 1.1 研究背景与意义
### 1.2 国内外研究现状（有评述）
### 1.3 本文主要工作

## 2 相关技术/需求分析
### 2.1 【技术/需求概述】（勿大段抄概念，控制在全文1/3以内）

## 3 系统设计/方法设计
### 3.1 总体架构（图3-1）
### 3.2 模块设计
### 3.3 数据库/模型设计（三线表）

## 4 系统实现（本人实现≥全文2/3的重头戏）
### 4.1 【模块1实现：关键代码思路+运行截图（图4-1）+说明】
### 4.2 【模块2实现…】

## 5 测试与结果分析
### 5.1 测试环境与用例（表5-1）
### 5.2 结果与分析（数据来自真实测试，严禁编造）

## 6 结论
【精炼总结工作与结果+不足+展望；不写心得】

## 参考文献（≥15篇，≥2篇外文，含开题文献；正文有标注[1]）
[1] 【…】

## 致谢
【谢指导教师{a.advisor or "【教师姓名】"}与帮助者；末尾学生署名】
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["task", "opening", "thesis"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--student", default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--advisor", default=None)
    ap.add_argument("--major", default=None)
    a = ap.parse_args()
    md = {"task": task_sk, "opening": opening_sk, "thesis": thesis_sk}[a.kind](a)
    tmp = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    tmp.write(md)
    tmp.close()
    if os.path.exists(MD2DOCX):
        subprocess.run([sys.executable, MD2DOCX, tmp.name, a.out], check=True)
        print("[docx] %s" % a.out)
    else:
        fallback = os.path.splitext(a.out)[0] + ".md"
        with open(fallback, "w", encoding="utf-8") as f:
            f.write(md)
        print("[md] md2docx 不可用，已输出 %s（可自行粘贴到 Word）" % fallback)
    os.unlink(tmp.name)


if __name__ == "__main__":
    main()
