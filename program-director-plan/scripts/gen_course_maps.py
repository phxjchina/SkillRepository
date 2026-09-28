# -*- coding: utf-8 -*-
"""三专业培养方案大图（课程地图）生成器。
样式对齐教务原版：8 学期纵向虚线分列 + 课程框与先修箭头 + 左侧能力条 + 底部跨学期公共课程条。
数据驱动：每专业一份 dict（能力条 / 课程[学期序] / 先修依赖 / 底部通识条）。
输出：培养方案大图_{AI|ZK|JK}.svg 至 OUT 目录。
"""
import os
OUT = r"F:\教学\2025年工作\智能科学与技术专业"
FONT = "Microsoft YaHei, PingFang SC, SimHei, sans-serif"

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def wrap(s, n):
    return [s[i:i+n] for i in range(0, len(s), n)]

# ---------- 三专业数据 ----------
# 课程: (学期, 课程名)  顺序即列内自上而下; deps: (先修课程名, 后续课程名)
PROFS = [
 dict(key="AI", color="#1d4ed8",
  title="人工智能专业 · 培养方案大图（2027 版 · 大模型应用方向）",
  sub="构造智能体程序 · 经典算法链 + 大模型应用链双轨 · 错位竞争：不往硬件系统走",
  abilities=["扎实的数学与程序设计基础","智能算法与模型开发能力","大模型应用与智能体开发能力","系统集成与边缘部署能力","综合运用AI知识解决复杂工程问题的能力"],
  courses=[(1,"高等数学A1"),(1,"Python程序设计"),(1,"人工智能专业导论"),(1,"大学物理1"),(1,"物理实验1"),
           (2,"高等数学A2"),(2,"大学物理2"),(2,"物理实验2"),(2,"离散数学"),(2,"数据结构与算法"),
           (3,"线性代数"),(3,"人工智能导论"),(3,"计算机组成与结构"),
           (4,"概率论与数理统计"),(4,"人工智能数学基础"),(4,"操作系统"),(4,"计算机网络"),(4,"数据库原理及应用"),(4,"算法分析与设计"),
           (5,"软件工程基础"),(5,"模式识别"),(5,"机器学习及其应用"),(5,"模式识别与机器学习综合实验"),(5,"AI辅助编程与软件工程"),
           (6,"深度学习A"),(6,"计算机视觉"),(6,"自然语言处理及应用"),(6,"智能数据挖掘"),(6,"图神经网络"),(6,"RAG技术与知识库构建"),(6,"多智能体系统开发"),(6,"本地大模型部署与微调"),(6,"智能系统创新设计"),
           (7,"强化学习"),(7,"生成式AI与AI大模型"),(7,"AI短剧与数字内容创作"),(7,"生产实习"),
           (8,"毕业实习"),(8,"毕业设计(论文)")],
  deps=[("高等数学A1","高等数学A2"),("高等数学A2","线性代数"),("高等数学A2","概率论与数理统计"),
        ("Python程序设计","数据结构与算法"),("数据结构与算法","算法分析与设计"),
        ("人工智能专业导论","人工智能导论"),("离散数学","数据结构与算法"),
        ("人工智能数学基础","机器学习及其应用"),("机器学习及其应用","深度学习A"),("模式识别","深度学习A"),
        ("深度学习A","计算机视觉"),("深度学习A","自然语言处理及应用"),("深度学习A","图神经网络"),
        ("自然语言处理及应用","生成式AI与AI大模型"),("生成式AI与AI大模型","RAG技术与知识库构建"),("生成式AI与AI大模型","多智能体系统开发"),("生成式AI与AI大模型","本地大模型部署与微调"),
        ("算法分析与设计","强化学习"),("AI辅助编程与软件工程","多智能体系统开发"),
        ("计算机视觉","智能系统创新设计"),("本地大模型部署与微调","智能系统创新设计"),("智能系统创新设计","毕业设计(论文)")],
  base=["思想政治理论课","大学英语","体育","公共选修课、讲座、科技竞赛、社会实践等"]),
 dict(key="ZK", color="#14532d",
  title="智能科学与技术专业 · 培养方案大图（2027 版 · 工程能力平台导向）",
  sub="构造智能系统(感知-传输-处理-计算-存储-控制) · B1-B4四子能力 × SYS1-4四类目标系统 · 软硬协同",
  abilities=["扎实的自然科学与社会科学基础知识","B1 信息系统开发能力","B2 嵌入式系统开发能力","B3 信息物理融合能力","B4 AI算法及模型开发能力","综合解决复杂工程问题·开发各类智能系统"],
  courses=[(1,"高等数学A1"),(1,"Python程序设计"),(1,"智能科学与技术专业导论"),(1,"大学物理1"),
           (2,"高等数学A2"),(2,"大学物理2"),(2,"离散数学"),(2,"数据结构与算法"),
           (3,"线性代数"),(3,"物联网概论"),(3,"人工智能导论"),(3,"计算机组成与结构"),
           (4,"概率论与数理统计"),(4,"人工智能数学基础"),(4,"操作系统"),(4,"计算机网络"),(4,"数据库原理及应用"),(4,"软件工程基础"),
           (5,"系统分析与设计"),(5,"模式识别"),(5,"机器学习及其应用"),(5,"模式识别与机器学习综合实验"),(5,"自动控制原理与智能控制(新增)"),
           (6,"深度学习A"),(6,"智能信息感知技术"),(6,"行业嵌入式系统"),(6,"系统集成与体系结构设计"),(6,"智能感知技术及应用"),(6,"物联网技术应用综合实验"),(6,"行业智能嵌入式系统综合实验"),(6,"智能系统创新设计"),
           (7,"无人机反制系统设计与仿真"),(7,"无人机编程与开发"),(7,"无人机自组网技术"),(7,"人工智能前沿技术"),(7,"智能控制系统综合实践(新增)"),(7,"生产实习"),
           (8,"毕业实习"),(8,"毕业设计(论文)")],
  deps=[("高等数学A1","高等数学A2"),("高等数学A2","线性代数"),("高等数学A2","概率论与数理统计"),
        ("Python程序设计","数据结构与算法"),("物联网概论","智能感知技术及应用"),
        ("人工智能数学基础","自动控制原理与智能控制"),("人工智能数学基础","机器学习及其应用"),
        ("机器学习及其应用","深度学习A"),("计算机组成与结构","行业嵌入式系统"),("操作系统","行业嵌入式系统"),
        ("行业嵌入式系统","行业智能嵌入式系统综合实验"),("智能信息感知技术","行业智能嵌入式系统综合实验"),
        ("系统分析与设计","系统集成与体系结构设计"),("自动控制原理与智能控制","智能控制系统综合实践"),
        ("系统集成与体系结构设计","无人机反制系统设计与仿真"),("智能感知技术及应用","无人机自组网技术"),
        ("智能系统创新设计","智能控制系统综合实践"),("生产实习","毕业设计(论文)"),("深度学习A","智能系统创新设计")],
  base=["思想政治理论课","大学英语","体育","公共选修课、讲座、科技竞赛、社会实践等"]),
 dict(key="JK", color="#9a3412",
  title="计算机科学与技术专业 · 培养方案大图（2027 版 · 五大部件+嵌入式）",
  sub="构造计算机系统五大部件(输入/输出/计算/控制/存储) · 硬件为基·嵌入式为矛·带上位机",
  abilities=["扎实的数学与电子硬件基础","计算机五大部件精通能力","嵌入式与接口开发能力","上位机与系统软件开发能力","综合软硬件协同解决复杂工程问题的能力"],
  courses=[(1,"高等数学A1"),(1,"Python程序设计"),(1,"计算机科学与技术专业导论"),(1,"大学物理1"),(1,"物理实验1"),
           (2,"高等数学A2"),(2,"大学物理2"),(2,"物理实验2"),(2,"离散数学"),(2,"数据结构与算法"),
           (3,"线性代数"),(3,"电路与数字逻辑设计"),(3,"计算机组成原理(深入)"),
           (4,"概率论与数理统计"),(4,"微机原理与接口技术"),(4,"操作系统(深入)"),(4,"计算机网络(深入)"),(4,"数据库系统原理(深入)"),
           (5,"编译原理"),(5,"软件工程(深入)"),(5,"嵌入式系统原理(ARM/Linux)"),(5,"单片机与接口技术"),
           (6,"FPGA原理与应用"),(6,"计算机体系结构"),(6,"上位机软件开发"),(6,"行业计算机组成与结构"),
           (7,"边缘计算(Jetson)"),(7,"智能物联网系统"),(7,"生产实习"),
           (8,"毕业实习"),(8,"毕业设计(论文)")],
  deps=[("高等数学A1","高等数学A2"),("高等数学A2","线性代数"),("高等数学A2","概率论与数理统计"),
        ("Python程序设计","数据结构与算法"),("电路与数字逻辑设计","计算机组成原理(深入)"),
        ("计算机组成原理(深入)","微机原理与接口技术"),("计算机组成原理(深入)","计算机体系结构"),
        ("微机原理与接口技术","单片机与接口技术"),("操作系统(深入)","嵌入式系统原理(ARM/Linux)"),
        ("嵌入式系统原理(ARM/Linux)","FPGA原理与应用"),("单片机与接口技术","上位机软件开发"),
        ("计算机体系结构","边缘计算(Jetson)"),("计算机网络(深入)","智能物联网系统"),
        ("上位机软件开发","智能物联网系统"),("生产实习","毕业设计(论文)")],
  base=["思想政治理论课","大学英语","体育","公共选修课、讲座、科技竞赛、社会实践等"]),
]

# ---------- 布局常量 ----------
L = 100          # 左侧能力条区宽
COLW = 126       # 学期列宽
TOP = 84         # 列头下内容起始 y
ROWH = 42        # 行高
BOXH = 32        # 课程框高
BW = 10          # 外边距

def col_x(s):    # 学期 s(1..8) 左边界
    return L + (s-1)*COLW

def render(prof):
    key, color = prof["key"], prof["color"]
    courses = prof["courses"]
    maxrows = max(sum(1 for c in courses if c[0]==s) for s in range(1,9))
    body_h = maxrows*ROWH
    base_top = TOP + body_h + 18
    H = base_top + len(prof["base"])*38 + 16
    W = L + COLW*8 + 14
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">')
    o.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    o.append(f'<marker id="arw" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 Z" fill="#64748b"/></marker>')
    # 标题
    o.append(f'<text x="{W/2}" y="24" font-size="15" font-weight="bold" fill="#0f172a" text-anchor="middle">{esc(prof["title"])}</text>')
    o.append(f'<text x="{W/2}" y="44" font-size="10.5" fill="{color}" text-anchor="middle">{esc(prof["sub"])}</text>')
    # 学期列头 + 虚线分隔
    for s in range(1,9):
        x = col_x(s)
        o.append(f'<text x="{x+COLW/2}" y="{TOP-12}" font-size="12" font-weight="bold" fill="#0f172a" text-anchor="middle">第{["一","二","三","四","五","六","七","八"][s-1]}学期</text>')
        if s > 1:
            o.append(f'<line x1="{x-3}" y1="{TOP-6}" x2="{x-3}" y2="{base_top+6}" stroke="#94a3b8" stroke-width="1" stroke-dasharray="5,4"/>')
    # 课程框
    pos = {}
    for sem,name in courses:
        row = sum(1 for c in courses if c[0]==sem and courses.index(c) < [i for i,c in enumerate(courses) if c==(sem,name)][0])
        x = col_x(sem)+7
        y = TOP + row*ROWH
        w = COLW-18
        pos[name] = (x,y,w)
        fill = "#fef9c3" if "新增" in name else ("#f8fafc" if sem>=7 else "#ffffff")
        stroke = "#0f172a"
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{BOXH}" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
        lines = wrap(name.replace("(新增)",""), 7)
        if len(lines)==1:
            o.append(f'<text x="{x+w/2}" y="{y+BOXH/2+3.5}" font-size="9.5" fill="#0f172a" text-anchor="middle">{esc(name)}</text>')
        else:
            o.append(f'<text x="{x+w/2}" y="{y+13}" font-size="9" fill="#0f172a" text-anchor="middle">{esc(lines[0])}</text>')
            o.append(f'<text x="{x+w/2}" y="{y+25}" font-size="9" fill="#0f172a" text-anchor="middle">{esc(lines[1])}</text>')
    # 先修箭头
    for a,b in prof["deps"]:
        if a not in pos or b not in pos: continue
        ax,ay,aw = pos[a]; bx,by,bw = pos[b]
        acy, bcy = ay+BOXH/2, by+BOXH/2
        if abs(acy-bcy)<6 and bx>ax:  # 同水平
            d = f'M{ax+aw},{acy} L{bx},{bcy}'
        elif bx>ax:
            d = f'M{ax+aw},{acy} C{bx-14},{acy} {ax+aw+14},{bcy} {bx},{bcy}'
        else:  # 同列或回边：底部出→顶部入
            d = f'M{ax+aw/2},{ay+BOXH} L{bx+bw/2},{by-2}'
        o.append(f'<path d="{d}" fill="none" stroke="#64748b" stroke-width="1.1" marker-end="url(#arw)"/>')
    # 左侧能力条
    n = len(prof["abilities"])
    ah = (H-56-BW)/n
    for i,ab in enumerate(prof["abilities"]):
        y = 56 + i*ah
        o.append(f'<rect x="{BW}" y="{y:.0f}" width="{L-BW-8}" height="{ah-4:.0f}" rx="4" fill="{color}0d" stroke="{color}" stroke-width="1"/>')
        for j,ln in enumerate(wrap(ab, 6)):
            o.append(f'<text x="{BW+(L-BW-8)/2}" y="{y+ah/2-((len(wrap(ab,6))-1)*6.5)+13*j+3:.0f}" font-size="9.5" fill="{color}" text-anchor="middle">{esc(ln)}</text>')
    # 底部通识条
    by = base_top
    for i,txt in enumerate(prof["base"]):
        y = by + i*38
        o.append(f'<rect x="{L}" y="{y}" width="{COLW*8-6}" height="30" rx="3" fill="#f1f5f9" stroke="#94a3b8" stroke-width="0.8"/>')
        o.append(f'<text x="{L+(COLW*8-6)/2}" y="{y+19}" font-size="10.5" fill="#334155" text-anchor="middle">{esc(txt)}</text>')
    o.append('</svg>')
    return "\n".join(o), W, H

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for p in PROFS:
        svg, w, h = render(p)
        fn = os.path.join(OUT, f'培养方案大图_{p["key"]}.svg')
        open(fn, 'w', encoding='utf-8').write(svg)
        print("written", fn, w, h)
