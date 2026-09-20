# -*- coding: utf-8 -*-
"""反向设计（OBE）大图渲染器：系统→子系统→功能→知识点→课程大纲 分层依赖 SVG。
输出：每个专业一张 SVG + 一张跨专业依赖总图 + 一个 HTML 预览页。"""
import os, html, datetime

OUT = r"F:\教学\2025年工作\智能科学与技术专业"
FONT = "Microsoft YaHei, PingFang SC, SimHei, sans-serif"

# ---------- 三专业反向设计数据（同构） ----------
PROFS = [
 {
  "key":"AI","name":"人工智能专业","sub":"构造智能体程序 · 生成式AI应用开发（实用导向·已瘦身）",
  "color":"#2563eb","light":"#dbeafe","dark":"#1e40af",
  "systems":[
   {"id":"S1","name":"企业智能知识库问答系统(RAG)","job":"RAG知识库工程师",
    "subs":[
      {"name":"文档接入与预处理","funcs":[
        {"f":"多格式文档解析(PDF/Word/网页)","kp":"文档解析 / 格式清洗","c":"RAG技术与知识库构建 §483"},
        {"f":"文本清洗与元数据抽取","kp":"文本清洗 / 元数据","c":"RAG §483；智能数据挖掘 §24"}]},
      {"name":"切片·向量化·检索","funcs":[
        {"f":"语义切片与Embedding","kp":"向量空间 / 相似度","c":"RAG §487；AI数学基础(向量)"},
        {"f":"向量库检索与重排Rerank","kp":"向量库 / 混合检索","c":"RAG §491 / §495"}]}]},
   {"id":"S2","name":"多智能体自动化工作流系统","job":"智能体开发工程师",
    "subs":[
      {"name":"单体智能体","funcs":[
        {"f":"ReAct推理与Function Call","kp":"Agent架构 / 记忆","c":"多智能体系统开发 §128"},
        {"f":"私有RAG知识库接入","kp":"RAG接入 / 检索","c":"多智能体 §129；RAG §499"}]},
      {"name":"多Agent协作","funcs":[
        {"f":"角色设定与任务分解","kp":"任务规划 / 通信","c":"多智能体系统开发 §129"},
        {"f":"AutoGen/LangGraph编排","kp":"工作流编排","c":"多智能体系统开发 §129"}]}]},
   {"id":"S3","name":"智能视觉检测系统","job":"计算机视觉工程师",
    "subs":[
      {"name":"图像预处理","funcs":[
        {"f":"图像增强/边缘检测","kp":"图像增强 / 特征","c":"计算机视觉 §23；模式识别"},
        {"f":"CNN/RNN模型构建","kp":"卷积神经网络","c":"深度学习A §162"}]},
      {"name":"目标检测与边缘部署","funcs":[
        {"f":"YOLO目标检测/语义分割","kp":"目标检测 / 分割","c":"计算机视觉 §23"},
        {"f":"模型量化部署Jetson","kp":"量化 / 边缘部署","c":"本地大模型部署与微调 §155；智科航空嵌入式综合实验"}]}]},
   {"id":"S4","name":"智能文本处理与对话系统","job":"NLP工程师",
    "subs":[
      {"name":"文本理解","funcs":[
        {"f":"文本分类/情感/摘要","kp":"分类 / 序列建模","c":"NLP及应用；机器学习"},
        {"f":"Transformer与预训练","kp":"自注意力 / 预训练","c":"生成式AI与AI大模型 §245；NLP"}]},
      {"name":"对话生成与接口","funcs":[
        {"f":"对话机器人/Seq2Seq","kp":"对话状态 / 生成","c":"NLP及应用；生成式AI §245"},
        {"f":"意图识别与API对接","kp":"API调用 / 上下文","c":"生成式AI导论 §261；AI辅助编程"}]}]},
   {"id":"S5","name":"本地大模型私有化部署与微调平台","job":"模型部署工程师",
    "subs":[
      {"name":"选型与本地推理","funcs":[
        {"f":"开源模型谱系与算力评估","kp":"模型谱系 / 算力","c":"本地大模型部署与微调 §159"},
        {"f":"GGUF量化与API服务封装","kp":"量化格式 / 推理","c":"本地大模型部署与微调 §155"}]},
      {"name":"轻量微调与集成","funcs":[
        {"f":"LoRA/QLoRA微调","kp":"参数高效微调","c":"本地大模型部署与微调 §155"},
        {"f":"嵌入RAG/行业系统","kp":"模型集成","c":"本地部署 §155；RAG / 多智能体"}]}]},
   {"id":"S6","name":"AI辅助软件开发平台","job":"AI辅助开发工程师",
    "subs":[
      {"name":"需求与原型","funcs":[
        {"f":"需求分析与用户故事","kp":"需求工程","c":"AI辅助编程与软件工程 §371"},
        {"f":"低保真原型设计","kp":"原型设计","c":"AI辅助编程 §392；软件工程基础"}]},
      {"name":"代码与交付","funcs":[
        {"f":"函数/模块代码生成审查","kp":"代码生成 / 审查","c":"AI辅助编程 §375"},
        {"f":"Git/CI与文档自动化","kp":"版本协同 / 质量","c":"AI辅助编程 §383/§395"}]}]},
   {"id":"S7","name":"智能数据分析与挖掘系统","job":"数据分析师",
    "subs":[
      {"name":"数据工程","funcs":[
        {"f":"数据清洗与数据仓库","kp":"预处理 / 仓库","c":"智能数据挖掘 §24；数据分析与实践"},
        {"f":"分类/聚类/关联挖掘","kp":"挖掘算法 / 预测","c":"智能数据挖掘 §24；机器学习"}]},
      {"name":"可视化与决策","funcs":[
        {"f":"报表与数据可视化","kp":"数据可视化","c":"数据分析与实践"},
        {"f":"决策支持输出","kp":"决策建模","c":"AI短剧(展示包装) §186"}]}]},
   {"id":"S8","name":"AI数字内容创作系统","job":"AI数字文创",
    "subs":[
      {"name":"策划与视觉","funcs":[
        {"f":"选题/剧本/分镜","kp":"叙事结构 / 分镜","c":"AI短剧与数字内容创作 §190"},
        {"f":"文生图/图生图一致性","kp":"多模态生成","c":"AI短剧 §186；生成式AI导论 §257"}]},
      {"name":"视频音频与合规","funcs":[
        {"f":"文生视频/AI配音","kp":"视频 / 音频合成","c":"AI短剧 §186"},
        {"f":"版权自查与合规发布","kp":"版权合规 / 风控","c":"AI短剧 §191；生成式AI导论 §269"}]}]},
  ]},
 {
  "key":"ZK","name":"智能科学与技术专业","sub":"构造智能系统(感知-传输-处理-计算-存储-控制) · 航空智能+ · 软硬协同",
  "color":"#16a34a","light":"#dcfce7","dark":"#14532d",
  "systems":[
   {"id":"Z1","name":"智能物联网系统(全反馈闭环)","job":"物联网/智能系统集成工程师",
    "subs":[
      {"name":"感知接入","funcs":[
        {"f":"多源传感数据采集","kp":"传感原理 / 信号调理","c":"智能感知技术及应用 S6；智能信息感知技术 S6"},
        {"f":"嵌入式节点采集","kp":"嵌入式 / 低功耗","c":"航空嵌入式系统 S6；物联网(迁移)"}]},
      {"name":"传输·处理·控制","funcs":[
        {"f":"无线组网与边缘处理","kp":"WSN / 边缘计算","c":"物联网技术应用综合实验 S6；边缘计算"},
        {"f":"闭环控制与系统集成","kp":"系统集成 / 控制","c":"智能系统创新设计 S6；系统分析与设计(迁移)"}]}]},
   {"id":"Z2","name":"无人机导航与控制系统","job":"无人机系统工程师",
    "subs":[
      {"name":"导航定位","funcs":[
        {"f":"多源融合导航定位","kp":"SLAM / 滤波","c":"智能信息感知技术 S6；无人机编程与开发 S6"},
        {"f":"航迹规划与自组网","kp":"路径规划 / 自组网","c":"无人机反制系统设计与仿真 S7(导航)"}]},
      {"name":"飞行控制","funcs":[
        {"f":"飞控算法与姿态控制","kp":"控制理论 / 姿态","c":"航空嵌入式系统 S6"},
        {"f":"集群协同控制","kp":"集群算法 / 任务规划","c":"无人机反制系统 S7(集群)；智能系统创新设计 S6"}]}]},
   {"id":"Z3","name":"低空安全防护与无人机反制系统","job":"低空安全工程师",
    "subs":[
      {"name":"目标探测","funcs":[
        {"f":"雷达/频谱探测","kp":"信号处理 / FPGA","c":"计科FPGA J4(协作)；智能信息感知 S6"},
        {"f":"视觉目标识别","kp":"目标检测","c":"计算机视觉(共享)；智科深度学习A S6"}]},
      {"name":"反制决策","funcs":[
        {"f":"反制策略仿真","kp":"系统仿真 / 决策","c":"无人机反制系统设计与仿真 S7"},
        {"f":"安全合规与风控","kp":"低空安全合规","c":"人工智能前沿技术 S7；生成式AI导论 §269"}]}]},
   {"id":"Z4","name":"航空嵌入式智能系统","job":"航空嵌入式工程师",
    "subs":[
      {"name":"航空嵌入式开发","funcs":[
        {"f":"ARM/Linux飞控开发","kp":"嵌入式Linux / 驱动","c":"航空嵌入式系统 S6"},
        {"f":"适航软件规范","kp":"适航 / 可靠","c":"系统分析与设计(迁移)；体系结构设计(迁移)"}]},
      {"name":"综合实验(Jetson)","funcs":[
        {"f":"边缘AI部署综合实验","kp":"边缘部署 / 集成","c":"航空智能嵌入式系统综合实验 S6"},
        {"f":"航电仿真联调","kp":"航电仿真","c":"学院航电仿真平台(综合实验)"}]}]},
   {"id":"Z5","name":"智能系统集成与综合实验平台","job":"系统集成工程师",
    "subs":[
      {"name":"系统分析与建模","funcs":[
        {"f":"需求与体系结构建模","kp":"系统工程 / 建模","c":"系统分析与设计(迁移)；体系结构设计(迁移)"},
        {"f":"智能系统集成设计","kp":"集成方法 / 接口","c":"智能系统创新设计 S6"}]},
      {"name":"综合实验台","funcs":[
        {"f":"智能物联网综合实验台","kp":"实验台集成","c":"学院智能物联网综合实验台"},
        {"f":"低空安全防护实验平台","kp":"平台集成","c":"学院低空安全防护实验平台"}]}]},
   {"id":"Z6","name":"工业机器视觉系统","job":"机器视觉/工业检测工程师",
    "subs":[
      {"name":"视觉成像系统搭建","funcs":[
        {"f":"相机/镜头/光源选型与成像","kp":"成像原理 / 曝光 / 景深","c":"工业机器视觉与应用 Ch2（相机·镜头·光源）"},
        {"f":"图像采集与预处理(滤波/增强/特征)","kp":"图像处理基础","c":"工业机器视觉与应用 Ch2 §2.2"}]},
      {"name":"工业视觉四大应用","funcs":[
        {"f":"尺寸测量与定位(手眼标定)","kp":"标定 / 坐标变换","c":"工业机器视觉与应用 Ch3 §3.2/§3.3"},
        {"f":"缺陷检测与识别(条码/OCR/分拣)","kp":"模板匹配 / 分类","c":"工业机器视觉与应用 Ch3 §3.4/§3.5"}]},
      {"name":"AI视觉与具身视觉","funcs":[
        {"f":"深度学习目标检测(YOLO)与机械臂抓取","kp":"目标检测 / 抓取","c":"工业机器视觉与应用 Ch4 §4.1"},
        {"f":"模仿学习(ACT)/大模型具身视觉(Grounded-SAM2)","kp":"模仿学习 / VLA","c":"工业机器视觉与应用 Ch4 §4.2/§4.3"}]}]},
   {"id":"Z7","name":"自主智能系统","job":"自主系统/自动驾驶工程师",
    "subs":[
      {"name":"系统建模与架构","funcs":[
        {"f":"自主智能系统概念与体系结构","kp":"系统视角 / 架构","c":"自主智能系统基础（101计划·系统视角）"},
        {"f":"任务与环境建模","kp":"问题建模","c":"自主智能系统基础（感知-决策-执行框架）"}]},
      {"name":"感知-决策-执行闭环","funcs":[
        {"f":"环境感知与状态估计","kp":"感知 / 估计","c":"自主智能系统基础（感知环节）"},
        {"f":"决策规划与执行控制","kp":"决策 / 控制","c":"自主智能系统基础（决策-执行环节）"}]},
      {"name":"反馈自适应与实训","funcs":[
        {"f":"反馈闭环与自适应学习","kp":"反馈 / 自适应","c":"自主智能系统基础（反馈机制·全书）"},
        {"f":"实训(自动驾驶/服务机器人/智能制造)","kp":"系统集成","c":"自主智能系统基础（配套实训项目）"}]}]},
   {"id":"Z8","name":"智能机器人系统","job":"机器人算法/控制工程师",
    "subs":[
      {"name":"机器人学基础","funcs":[
        {"f":"构型与运动学(正逆/D-H/旋量)","kp":"齐次变换 / 运动学","c":"智能机器人与具身智能 Ch1-2"},
        {"f":"动力学与系统建模(拉氏/状态空间)","kp":"动力学 / 建模","c":"智能机器人与具身智能 Ch2 §2.3"}]},
      {"name":"感知与传感","funcs":[
        {"f":"视觉感知/标定/三维视觉/目标检测","kp":"机器视觉 / 三维视觉","c":"智能机器人与具身智能 Ch3；工业机器视觉(共享)"},
        {"f":"多传感器融合","kp":"融合 / SLAM","c":"智能机器人与具身智能 Ch3 §3.7"}]},
      {"name":"控制·导航·规划","funcs":[
        {"f":"运动控制(PID/MPC/强化学习)","kp":"控制理论 / RL","c":"智能机器人与具身智能 Ch4"},
        {"f":"导航与路径规划(SLAM)/任务规划(MDP)","kp":"SLAM / 规划","c":"智能机器人与具身智能 Ch5-6"}]}]},
   {"id":"Z9","name":"具身智能与世界模型系统","job":"具身智能/大模型工程师",
    "subs":[
      {"name":"具身多模态大模型","funcs":[
        {"f":"语言-动作对齐/RT-1,RT-2/VLA端到端","kp":"VLA / 多模态","c":"智能机器人与具身智能 Ch8"},
        {"f":"细粒度语言控制动作生成","kp":"动作生成","c":"智能机器人与具身智能 Ch8 §8.4"}]},
      {"name":"世界模型与交互学习","funcs":[
        {"f":"具身世界模型(预测/生成)与跨平台预训练","kp":"世界模型 / 预测","c":"智能机器人与具身智能 Ch9；世界模型与具身大模型(新课)"},
        {"f":"视觉引导动作优化/关键点约束","kp":"模仿 / 迁移","c":"智能机器人与具身智能 Ch9 §9.3"}]},
      {"name":"规划控制与多智能体","funcs":[
        {"f":"运动/操作联合规划与智能控制","kp":"规划控制闭环","c":"智能机器人与具身智能 Ch11"},
        {"f":"多智能体协作(博弈/共识/联邦)","kp":"多智能体 / MARL","c":"智能机器人与具身智能 Ch12"}]}]},
   {"id":"Z10","name":"物理AI与数字孪生系统","job":"物理AI/仿真工程师",
    "subs":[
      {"name":"数字孪生构建","funcs":[
        {"f":"OpenUSD/Omniverse场景组装","kp":"数字孪生 / USD","c":"物理AI与数字孪生(新课)·NVIDIA DLI"},
        {"f":"物理特性与仿真环境搭建","kp":"物理仿真","c":"物理AI与数字孪生(新课)"}]},
      {"name":"合成数据与Sim2Real","funcs":[
        {"f":"合成数据生成(Cosmos/生成式)","kp":"合成数据 / 增强","c":"物理AI与数字孪生(新课)·Cosmos"},
        {"f":"仿真到现实迁移(Sim2Real)","kp":"域适应 / 迁移","c":"物理AI与数字孪生(新课)；智能机器人系统(共享)"}]},
      {"name":"机器人仿真部署","funcs":[
        {"f":"Isaac Sim/Lab仿真与软件在环","kp":"仿真 / 在环测试","c":"物理AI与数字孪生(新课)·Isaac"},
        {"f":"数字孪生训练物理AI策略","kp":"策略训练 / 优化","c":"物理AI与数字孪生(新课)；世界模型(共享)"}]}]},
  ]},
 {
  "key":"JK","name":"计算机科学与技术专业","sub":"构造计算机系统五大部件(输入/输出/计算/控制/存储) · 硬件为基·嵌入式为矛·带上位机",
  "color":"#d97706","light":"#fef3c7","dark":"#92400e",
  "systems":[
   {"id":"J1","name":"嵌入式测控系统","job":"嵌入式开发工程师",
    "subs":[
      {"name":"单片机/ARM开发","funcs":[
        {"f":"MCU/ARM外设编程","kp":"寄存器 / 中断","c":"嵌入式系统(核心)；计算机组成与结构"},
        {"f":"Linux驱动开发","kp":"内核 / 驱动","c":"嵌入式Linux(核心)；操作系统"}]},
      {"name":"测控接口与调试","funcs":[
        {"f":"传感器/执行器接口","kp":"接口 / 总线","c":"嵌入式系统；智能感知(共享)"},
        {"f":"逻辑/示波器调试","kp":"调试 / 时序","c":"FPGA数字系统(接口) J4"}]}]},
   {"id":"J2","name":"上位机监控软件","job":"桌面/工业软件工程师",
    "subs":[
      {"name":"通信与界面","funcs":[
        {"f":"串口/网络通信","kp":"通信协议 / Socket","c":"计算机网络；嵌入式通信"},
        {"f":"GUI与数据可视化","kp":"GUI框架 / 可视化","c":"软件工程基础；AI辅助编程(共享)"}]},
      {"name":"数据持久化","funcs":[
        {"f":"本地/数据库存储","kp":"数据库 / 文件","c":"数据库原理及应用"},
        {"f":"与下位机联调交付","kp":"联调 / 交付","c":"软件工程基础；AI辅助编程 §395"}]}]},
   {"id":"J3","name":"计算机硬件系统(五大部件)","job":"硬件/体系结构工程师",
    "subs":[
      {"name":"运算与控制","funcs":[
        {"f":"CPU/运算器设计","kp":"数据通路 / 控制器","c":"计算机组成与结构(核心)"},
        {"f":"指令系统与微程序","kp":"指令集 / 微架构","c":"计算机组成与结构；体系结构设计(迁移)"}]},
      {"name":"存储与I/O","funcs":[
        {"f":"存储器层次设计","kp":"Cache / 内存","c":"计算机组成与结构"},
        {"f":"I/O与总线接口","kp":"总线 / 中断","c":"计算机组成与结构；嵌入式接口"}]}]},
   {"id":"J4","name":"FPGA数字逻辑与接口系统","job":"数字逻辑/ASIC工程师",
    "subs":[
      {"name":"数字逻辑设计","funcs":[
        {"f":"Verilog组合/时序逻辑","kp":"HDL / 状态机","c":"FPGA数字系统与逻辑设计(核心)"},
        {"f":"IP核与接口设计","kp":"IP复用 / 接口","c":"FPGA数字系统；嵌入式接口"}]},
      {"name":"硬加速与信号处理","funcs":[
        {"f":"信号处理硬件加速","kp":"并行 / 流水线","c":"FPGA数字系统；智科Z3雷达协作"},
        {"f":"逻辑分析仪调试","kp":"时序分析","c":"FPGA数字系统(实验)"}]}]},
   {"id":"J5","name":"操作系统内核与驱动","job":"系统软件工程师",
    "subs":[
      {"name":"OS原理","funcs":[
        {"f":"进程/内存管理","kp":"调度 / 虚拟内存","c":"操作系统(核心)"},
        {"f":"文件系统","kp":"FS / I/O","c":"操作系统；计算机组成与结构"}]},
      {"name":"驱动与实验","funcs":[
        {"f":"设备驱动开发","kp":"驱动框架","c":"操作系统；嵌入式Linux"},
        {"f":"内核实验与裁剪","kp":"裁剪 / 移植","c":"嵌入式Linux；航空嵌入式(共享)"}]}]},
  ]},
]

# 跨专业依赖边： (来源系统id, 目标系统id, 说明)
CROSS = [
 ("S5","Z4","AI本地大模型部署依赖智科航空嵌入式(Jetson)综合实验"),
 ("S5","J1","AI边缘部署依赖计科嵌入式测控硬件"),
 ("S1","J3","AI知识库依赖计科数据库/服务器底座"),
 ("S3","Z3","AI视觉检测复用于智科反制系统目标探测"),
 ("Z2","J1","智科无人机飞控依赖计科嵌入式硬件"),
 ("Z2","J3","智科导航依赖计科计算机硬件系统"),
 ("Z1","J2","智科物联网监控调用计科上位机软件"),
 ("Z1","J1","智科物联网节点依赖计科嵌入式"),
 ("Z3","J4","智科反制雷达信号处理依赖计科FPGA硬加速"),
 ("J2","Z1","计科上位机被智科物联网/无人机监控调用"),
 # 新增系统依赖
 ("Z6","S3","智科工业机器视觉系统为AI视觉检测提供工业场景/硬件/标定能力"),
 ("Z7","Z8","自主智能系统(闭环框架)是智能机器人系统的上层方法论"),
 ("Z7","Z9","自主智能系统反馈闭环贯通具身智能世界模型"),
 ("Z8","Z6","智能机器人系统调用工业机器视觉做感知"),
 ("Z8","Z10","智能机器人在物理AI数字孪生中仿真训练(Sim2Real)"),
 ("Z9","Z10","世界模型为物理AI提供预测/生成式仿真环境"),
 ("Z10","Z2","物理AI数字孪生用于无人机飞控仿真"),
 ("Z8","Z4","智能机器人控制依赖智科航空嵌入式硬件"),
 ("Z9","S2","具身多智能体为AI多智能体工作流提供物理底座"),
 ("Z10","J3","物理AI仿真依赖计科计算机硬件/并行计算"),
 ("Z8","J1","机器人嵌入式控制依赖计科嵌入式测控"),
 ("Z6","J1","工业视觉采集节点依赖计科嵌入式硬件"),
]

# ---------- 渲染 ----------
COLW, ROWH, PADX, PADY, BANDPAD = 215, 42, 16, 8, 22
COLX = [PADX + i*COLW for i in range(5)]
COLHEAD = ["待开发系统","子系统","功能","知识点","课程·教学大纲"]
HEADY = 70

def esc(s): return html.escape(str(s), quote=True)

def box(x,y,w,h,text,fill,stroke,fs=12,tc="#1f2937",bold=False):
    fw = 'font-weight="bold"' if bold else ""
    # 简单中文折行：每行约 maxn 个字符（CJK 计1，ASCII 计0.5），避免长名溢出框
    maxn = max(4, int((w-14)/(fs*0.60)))
    lines=[]; cur=""; cnt=0.0
    for ch in str(text):
        cur+=ch
        cnt += 1.0 if ord(ch) > 0x2e80 else 0.5
        if cnt >= maxn:
            lines.append(cur); cur=""; cnt=0.0
    if cur: lines.append(cur)
    if not lines: lines=[""]
    lh = fs + 3
    start_y = y + h/2 - (len(lines)-1)*lh/2 + fs*0.32
    tsp = "".join(f'<tspan x="{x+w/2}" y="{start_y+i*lh:.1f}">{esc(ln)}</tspan>' for i,ln in enumerate(lines))
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.2"/>'
            f'<text font-size="{fs}" font-family="{FONT}" fill="{tc}" text-anchor="middle" {fw}>{tsp}</text>')

def txt(x,y,text,fs=11,tc="#374151",anchor="middle"):
    return (f'<text x="{x}" y="{y}" font-size="{fs}" font-family="{FONT}" '
            f'fill="{tc}" text-anchor="{anchor}">{esc(text)}</text>')

def edge(x1,y1,x2,y2,color="#94a3b8",dash="",w=1.4):
    d = f'stroke-dasharray="{dash}"' if dash else ""
    # 贝塞尔水平连线
    mx = (x1+x2)/2
    return (f'<path d="M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}" '
            f'fill="none" stroke="{color}" stroke-width="{w}" {d}/>')

def render_prof(prof):
    # 统计每个系统行数
    rows = []  # (sys_i, sub_name, func)
    sys_meta = []
    for si,sysd in enumerate(prof["systems"]):
        cnt=0
        for sub in sysd["subs"]:
            for f in sub["funcs"]:
                rows.append((si, sub["name"], f))
                cnt+=1
        sys_meta.append((sysd, cnt))
    total = len(rows)
    head_h = HEADY + 30
    height = head_h + total*ROWH + (len(prof["systems"]))*BANDPAD + PADY
    width = COLX[4] + COLW + PADX
    c = prof["color"]; lc = prof["light"]; dc = prof["dark"]
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}" font-family="{FONT}">']
    s.append(f'<rect width="{width}" height="{height}" fill="#ffffff"/>')
    # 标题
    s.append(f'<rect x="0" y="0" width="{width}" height="54" fill="{dc}"/>')
    s.append(txt(width/2, 24, f'{prof["name"]} · 反向设计大图（系统→子系统→功能→知识点→课程）',
                16, "#ffffff", "middle").replace('fill="#374151"','fill="#ffffff"'))
    s.append(txt(width/2, 44, prof["sub"], 11, "#e0e7ff", "middle").replace('fill="#374151"','fill="#e0e7ff"'))
    # 列头
    for i,h in enumerate(COLHEAD):
        s.append(txt(COLX[i]+COLW/2, HEADY+16, h, 12.5, dc, "middle").replace('fill="#374151"',f'fill="{dc}"'))
        s.append(f'<line x1="{COLX[i]}" y1="{HEADY+24}" x2="{COLX[i]+COLW}" y2="{HEADY+24}" stroke="{lc}" stroke-width="1"/>')
    s.append(f'<line x1="{PADX}" y1="{HEADY+24}" x2="{width-PADX}" y2="{HEADY+24}" stroke="{lc}" stroke-width="1.5"/>')
    # 布局
    y = head_h
    sys_cursor=[0]*len(prof["systems"])
    # 预计算每个系统起始y和高度
    sys_y={}; sys_h={}
    yy=head_h
    for si,(sysd,cnt) in enumerate(sys_meta):
        sys_y[si]=yy
        sys_h[si]=cnt*ROWH + BANDPAD
        yy += cnt*ROWH + BANDPAD
    # 逐行
    row_idx=0
    for ri,(si,sub_name,f) in enumerate(rows):
        ry = sys_y[si] + BANDPAD/2 + sys_cursor[si]*ROWH
        sys_cursor[si]+=1
    # 第二遍：画框与连线
    sys_cursor=[0]*len(prof["systems"])
    # 系统框（跨整个band）
    for si,(sysd,cnt) in enumerate(sys_meta):
        bx=COLX[0]; by=sys_y[si]; bh=cnt*ROWH+BANDPAD
        s.append(box(bx,by,COLW-8,bh, f'{sysd["id"]} {sysd["name"]}', lc, dc, 12, dc, True))
        # 岗位标注（小字）
        s.append(txt(bx+ (COLW-8)/2, by+bh-8, f'岗位：{sysd["job"]}', 9.5, dc, "middle"))
    # 子系统：记录各子系统首行y与高度
    sub_y={}; sub_h={}
    for si,(sysd,cnt) in enumerate(sys_meta):
        pass
    # 先统计每个(si,sub_name)占几行
    sub_count={}
    for (si,sn,f) in rows:
        sub_count[(si,sn)]=sub_count.get((si,sn),0)+1
    # 计算子系统y
    sub_y={}; sub_started={}
    for (si,sn,f) in rows:
        key=(si,sn)
        if key not in sub_y:
            ry=sys_y[si]+BANDPAD/2+sys_cursor[si]*ROWH
            sub_y[key]=ry
        sub_started[key]=sub_started.get(key,0)+1
    # 重排sys_cursor用于子系统高度
    # 画子系统框（按出现顺序，每个画一次）
    drawn=set()
    sys_cursor=[0]*len(prof["systems"])
    # 重新遍历定位子系统band
    sub_band={}
    tmp={}
    for (si,sn,f) in rows:
        key=(si,sn)
        if key not in tmp:
            base=sys_y[si]+BANDPAD/2
            # 计算该行之前同系统的行数
            n_before=0
            for (si2,sn2,f2) in rows:
                if si2==si and (si2,sn2) in sub_y and (si2,sn2,sn2)<(si,sn,sn):
                    pass
            # 直接用累计
            pass
    # 简化：按行遍历同时维护 subsystems 当前 band
    sys_cursor=[0]*len(prof["systems"])
    sub_cur={}
    cur_sub_first={}
    for ri,(si,sn,f) in enumerate(rows):
        ry = sys_y[si] + BANDPAD/2 + sys_cursor[si]*ROWH
        # 功能框
        fy=ry+4; fh=ROWH-10
        s.append(box(COLX[2], fy, COLW-10, fh, f["f"], "#fff7ed", "#fb923c", 11, "#7c2d12"))
        s.append(box(COLX[3], fy, COLW-10, fh, f["kp"], "#f0fdf4", "#22c55e", 10.5, "#14532d"))
        s.append(box(COLX[4], fy, COLW-10, fh, f["c"], "#eff6ff", "#3b82f6", 10, "#1e3a8a"))
        # 子系统框（首次出现画一个跨其后行的框）
        key=(si,sn)
        if key not in cur_sub_first:
            cur_sub_first[key]=ry
            # 计算该子系统后续行数
            n=sub_count[key]
            subh=n*ROWH
            s.append(box(COLX[1], ry, COLW-8, subh, sn, lc, c, 11, dc, True))
            # 连线 系统->子系统（系统框中心 -> 子系统框中心）
            s.append(edge(COLX[0]+COLW-8, sys_y[si]+ sys_h[si]/2, COLX[1], ry+subh/2, c))
        # 子系统->功能 连线
        s.append(edge(COLX[1]+COLW-8, ry+ROWH/2, COLX[2], ry+ROWH/2, c))
        # 功能->知识点->课程 连线
        s.append(edge(COLX[2]+COLW-10, ry+ROWH/2, COLX[3], ry+ROWH/2, "#fb923c"))
        s.append(edge(COLX[3]+COLW-10, ry+ROWH/2, COLX[4], ry+ROWH/2, "#22c55e"))
        sys_cursor[si]+=1
    # 图例
    ly=height-46
    s.append(f'<rect x="{PADX}" y="{ly-2}" width="{width-2*PADX}" height="34" rx="6" fill="#f8fafc" stroke="#e2e8f0"/>')
    leg=[("系统",lc,dc),("子系统",lc,c),("功能","#fff7ed","#fb923c"),("知识点","#f0fdf4","#22c55e"),("课程","#eff6ff","#3b82f6")]
    lx=PADX+14
    for name,fill,stroke in leg:
        s.append(f'<rect x="{lx}" y="{ly+6}" width="16" height="12" rx="3" fill="{fill}" stroke="{stroke}"/>')
        s.append(txt(lx+22, ly+16, name, 10.5, "#475569","start"))
        lx+=86
    s.append(f'<text x="{width-PADX-10}" y="{ly+16}" font-size="9.5" font-family="{FONT}" fill="#94a3b8" text-anchor="end">生成：{datetime.date.today()} · OBE反向设计 · 连线表示「分解/映射」依赖</text>')
    s.append('</svg>')
    return "\n".join(s), width, height

def render_cross():
    width=1180; rowh=46; top=90
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{top+14*rowh+60}" viewBox="0 0 {width} {top+14*rowh+60}" font-family="{FONT}">']
    s.append(f'<rect width="{width}" height="{top+14*rowh+60}" fill="#ffffff"/>')
    s.append(f'<rect x="0" y="0" width="{width}" height="54" fill="#0f172a"/>')
    s.append(txt(width/2,24,"跨专业能力依赖总图：三专业主干系统相互支撑",16,"#ffffff","middle").replace('fill="#374151"','fill="#ffffff"'))
    s.append(txt(width/2,44,"箭头 = 「依赖/被调用」关系（上游系统依赖下游系统提供的能力）",11,"#cbd5e1","middle").replace('fill="#374151"','fill="#cbd5e1"'))
    # 三列
    cols=[("AI","人工智能专业","#2563eb",[p for p in PROFS[0]["systems"]]),
          ("ZK","智能科学与技术专业","#16a34a",[p for p in PROFS[1]["systems"]]),
          ("JK","计算机科学与技术专业","#d97706",[p for p in PROFS[2]["systems"]])]
    colx=[60,460,860]; colw=320
    node_y={}  # sysid -> y
    for ci,(ck,name,color,syslist) in enumerate(cols):
        x=colx[ci]
        s.append(f'<rect x="{x}" y="{top-26}" width="{colw}" height="26" rx="6" fill="{color}"/>')
        s.append(txt(x+colw/2, top-8, name, 13, "#ffffff","middle").replace('fill="#374151"','fill="#ffffff"'))
        for i,sysd in enumerate(syslist):
            y=top+i*rowh
            node_y[sysd["id"]]=y
            s.append(box(x, y, colw-20, rowh-10, f'{sysd["id"]} {sysd["name"]}', "#f8fafc", color, 11, "#0f172a", True))
    # 依赖边
    cmap={p["id"]:p for p in PROFS[0]["systems"]+PROFS[1]["systems"]+PROFS[2]["systems"]}
    for (a,b,desc) in CROSS:
        ya=node_y.get(a); yb=node_y.get(b)
        if ya is None or yb is None: continue
        xa=colx[[k for k,_,_,_ in cols].index(a[:2] if False else [c[0] for c in cols if a in [s["id"] for s in c[3]]][0])]
        # 找到a、b所属列
        def findcol(sid):
            for ci,(ck,name,color,sl) in enumerate(cols):
                if any(x["id"]==sid for x in sl): return ci
            return 0
        ca=findcol(a); cb=findcol(b)
        x_ar=colx[ca]+colw-20; x_al=colx[ca]
        x_br=colx[cb]+colw-20; x_bl=colx[cb]
        color = cols[cb][2]
        # 从a右出，到b左或右入
        if cb>ca:
            x1=x_ar; x2=x_bl
        elif cb<ca:
            x1=x_al; x2=x_br
        else:
            x1=x_ar; x2=x_bl
        mx=(x1+x2)/2
        s.append(f'<path d="M{x1},{ya+rowh/2-5} C{mx},{ya+rowh/2-5} {mx},{yb+rowh/2-5} {x2},{yb+rowh/2-5}" fill="none" stroke="{color}" stroke-width="1.8" marker-end="url(#arrow)"/>')
    # 箭头定义
    s.insert(2, '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L8,3 L0,6 Z" fill="#475569"/></marker></defs>')
    s.append(f'<text x="{width/2}" y="{top+14*rowh+40}" font-size="10" font-family="{FONT}" fill="#94a3b8" text-anchor="middle">例：AI(S5)本地部署←智科(Z4)航空嵌入式综合实验、计科(J1)嵌入式测控；智科(Z3)反制←计科(J4)FPGA硬加速</text>')
    s.append('</svg>')
    return "\n".join(s)

# ---------- 主流程 ----------
os.makedirs(OUT, exist_ok=True)
svgs=[]
for prof in PROFS:
    svg,w,h=render_prof(prof)
    fn=os.path.join(OUT, f'reverse_{prof["key"]}.svg')
    with open(fn,'w',encoding='utf-8') as fp: fp.write(svg)
    svgs.append((prof,fn,w,h))
    print("written", fn, w, h)
cross_svg=render_cross()
cross_fn=os.path.join(OUT,'reverse_cross.svg')
with open(cross_fn,'w',encoding='utf-8') as fp: fp.write(cross_svg)
print("written", cross_fn)

# HTML 预览整合
parts=[]
parts.append(f'<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>三专业反向设计大图</title>'
             f'<style>body{{font-family:{FONT};margin:0;background:#f1f5f9;color:#0f172a}}'
             f'.wrap{{max-width:1200px;margin:0 auto;padding:24px}}'
             f'h1{{font-size:22px}}.sec{{margin:28px 0 10px;font-size:18px;font-weight:bold;border-left:6px solid #2563eb;padding-left:10px}}'
             f'.cap{{color:#475569;font-size:13px;margin:6px 0 14px;line-height:1.6}}'
             f'.card{{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:10px;overflow:auto}}'
             f'img{{width:100%;height:auto;display:block}}</style></head><body><div class="wrap">')
parts.append('<h1>智能科学与工程系 · 三专业反向设计（OBE）大图</h1>')
parts.append('<p class="cap">设计方法：先定「能开发的系统」→ 拆子系统 → 功能 → 知识点 → 教学大纲（课程·章节）。'
              '每专业一张分层依赖图（连线表示「分解/映射」依赖）；末图为跨专业能力依赖总图（箭头表示相互支撑）。'
              'AI 专业已按彭老师意见瘦身（去掉最优化等偏难课，换实用课）。</p>')
for prof,fn,w,h in svgs:
    rel=os.path.basename(fn)
    parts.append(f'<div class="sec" style="border-color:{prof["color"]}">{prof["name"]}</div>')
    parts.append(f'<p class="cap">{prof["sub"]}</p>')
    parts.append(f'<div class="card"><img src="{rel}" alt="{prof["name"]}"></div>')
parts.append('<div class="sec" style="border-color:#0f172a">跨专业能力依赖总图</div>')
parts.append('<p class="cap">三专业主干系统并非孤立：计科提供硬件/嵌入式/上位机底座，智科提供系统级集成与航空特色，'
             'AI 提供算法模型与生成式应用；三者通过边缘部署、视觉检测、雷达信号处理等形成能力闭环。</p>')
parts.append(f'<div class="card"><img src="reverse_cross.svg" alt="cross"></div>')
parts.append('</div></body></html>')
html_fn=os.path.join(OUT,'reverse_design_preview.html')
with open(html_fn,'w',encoding='utf-8') as fp: fp.write("\n".join(parts))
print("written", html_fn)
