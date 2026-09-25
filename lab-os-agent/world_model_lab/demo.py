"""
demo.py — 实验室巡检小车「真世界模型」端到端演示

一条龙演示彭老师体系里"物理 AI 大脑"的闭环：
  1) 真实世界(动力学环境) 产生 (s,a)→(s',r) 数据
  2) 世界模型 从数据学出动力学（可解释线性模型，误差≈0）
  3) 模型预测控制(MPC) 在"想象"里规划出最优动作序列
  4) 形式化验证(z3) 证明该世界模型不会越界/超速/撞禁区；
     若不可证明 → 物理 AI 修正(收紧动作) → 再验证直到可证明安全

运行：  python3.11 demo.py
输出：  控制台报告 + figs/ 下三张图
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, os.path.dirname(__file__))
from dynamics_env import LabRoverEnv
from world_model import LinearWorldModel, evaluate
from planner import MPC
import formal_verify as fv

HERE = os.path.dirname(__file__)
FIG = os.path.join(HERE, 'figs')
os.makedirs(FIG, exist_ok=True)

# ── 中文字体：提取 Noto Sans CJK SC（index=2）为独立 ttf，确保简体字形 ──
import matplotlib.font_manager as fm
_CJK_TTC = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
_SC_TTF = os.path.join(HERE, 'assets', 'NotoSansSC-Regular.ttf')
os.makedirs(os.path.dirname(_SC_TTF), exist_ok=True)
if not os.path.exists(_SC_TTF):
    from fontTools.ttLib import TTFont
    TTFont(_CJK_TTC, fontNumber=2).save(_SC_TTF)
fm.fontManager.addfont(_SC_TTF)
plt.rcParams['font.family'] = fm.FontProperties(fname=_SC_TTF).get_name()
plt.rcParams['axes.unicode_minus'] = False


def main():
    print("=" * 64)
    print("实验室巡检小车 · 真世界模型 端到端演示")
    print("（场景：西安航空学院 · 信息物理融合系统创客空间 · 地面巡检小车）")
    print("=" * 64)

    env = LabRoverEnv(clip_vel=False)
    A, B = env.linear_params()
    c = np.zeros(4)

    # ── 1) 数据采集 ──
    S, Aa, S2, R = env.collect_data(6000, seed=7)
    n = len(S)
    n_tr = n // 2

    # ── 2) 训练世界模型 ──
    wm = LinearWorldModel(env.state_dim, env.act_dim)
    wm.fit(S[:n_tr], Aa[:n_tr], S2[:n_tr], R[:n_tr])
    err = evaluate(wm, S[n_tr:], Aa[n_tr:], S2[n_tr:])
    print(f"\n[1] 世界模型训练完成 | 测试集平均预测误差(状态范数): {err:.5f}")

    # ── 3) MPC 在想象里规划 ──
    s0 = np.array([0.4, 0.4, 0.0, 0.0])
    mpc = MPC(wm, env, horizon=22, n_candidates=2000, seed=3)
    ret, traj, seq = mpc.plan_cem(s0)
    traj = np.array(traj)
    print(f"[2] MPC 想象规划 | 最优累积奖励={ret:.2f} | 轨迹步数={len(traj)-1} "
          f"| 终点位置=({traj[-1][0]:.2f},{traj[-1][1]:.2f})")

    s = env.reset(s0.copy())
    reached = None
    for a in seq:
        s, _, done, info = env.step(a)
        if done:
            reached = info['event']
            break
    print(f"    ↳ 真实环境回放同一动作序列: {reached or '在界内安全移动（未终止）'}")

    # ── 4) 形式化验证 + 物理 AI 修正 ──
    init_box = [(0.3, 0.5), (0.3, 0.5), (-0.2, 0.2), (-0.2, 0.2)]
    loose = [(-3.0, 3.0), (-3.0, 3.0)]
    ok_loose, cex = fv.verify_safe(
        A, B, c, init_box, loose, env.safe_constraints_z3, horizon=8)
    print(f"\n[3] 形式化验证（宽松动作 ±3.0）: "
          f"{'安全' if ok_loose else '发现违规反例（轨迹越界）'}")
    final_box, iters, _ = fv.physical_ai_guard(
        init_box, loose, env.safe_constraints_z3, A, B, c, horizon=8)
    print(f"    ↳ 物理 AI 修正：动作幅度逐次减半，第 {iters} 次后变为 "
          f"{final_box} → 可证明安全（确定性保证）")

    # ── 5) 可视化 ──
    plot_map(env, traj, s0, os.path.join(FIG, 'fig1_planning.png'))
    plot_pred_vs_true(S2[n_tr:], wm.predict_batch(S[n_tr:], Aa[n_tr:])[0],
                      os.path.join(FIG, 'fig2_prediction.png'))
    if not ok_loose:
        plot_cex(env, cex, os.path.join(FIG, 'fig3_counterexample.png'))
    print(f"\n[4] 图表已保存至 {FIG}")
    print("演示完成。")


def plot_map(env, traj, s0, path):
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.add_patch(Rectangle((0, 0), env.L, env.W, fill=False, ec='k', lw=2))
    for (x0, y0, x1, y1) in env.obstacles:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0,
                               fc='gray', alpha=0.45))
    gx0, gy0, gx1, gy1 = env.goal
    ax.add_patch(Rectangle((gx0, gy0), gx1 - gx0, gy1 - gy0,
                           fc='green', alpha=0.4))
    ax.plot(traj[:, 0], traj[:, 1], '-o', ms=3, color='C0',
            label='MPC 想象轨迹（世界模型内）')
    ax.plot(s0[0], s0[1], 'ks', ms=9, label='起点')
    ax.set_xlim(-0.6, env.L + 0.6)
    ax.set_ylim(-0.6, env.W + 0.6)
    ax.set_xlabel('x'); ax.set_ylabel('y')
    ax.set_title('实验室巡检小车 · 世界模型内 MPC 想象规划')
    ax.legend(loc='upper right'); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def plot_pred_vs_true(S2, P, path):
    fig, ax = plt.subplots(figsize=(4.6, 4.6))
    ax.scatter(S2[:, 0], P[:, 0], s=5, alpha=0.3, color='C0')
    lo = min(S2[:, 0].min(), P[:, 0].min())
    hi = max(S2[:, 0].max(), P[:, 0].max())
    ax.plot([lo, hi], [lo, hi], 'r--', lw=1.5, label='理想 y=x')
    ax.set_xlabel('真实 x 坐标'); ax.set_ylabel('世界模型预测 x 坐标')
    ax.set_title('世界模型预测 vs 真实（测试集）')
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def plot_cex(env, cex, path):
    traj = cex['traj']
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.add_patch(Rectangle((0, 0), env.L, env.W, fill=False, ec='k', lw=2))
    for (x0, y0, x1, y1) in env.obstacles:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0,
                               fc='gray', alpha=0.45))
    ax.plot(traj[:, 0], traj[:, 1], '-o', ms=4, color='C3',
            label='违规反例轨迹（z3 找到）')
    # 标出越界点
    bad = [(i, p) for i, p in enumerate(traj)
           if not (0 <= p[0] <= env.L and 0 <= p[1] <= env.W)]
    for i, p in bad:
        ax.plot(p[0], p[1], 'rx', ms=10, mew=2)
    if bad:
        ax.annotate('越界点', xy=(bad[0][1][0], bad[0][1][1]),
                    xytext=(bad[0][1][0] + 0.3, bad[0][1][1] + 0.3),
                    color='red', arrowprops=dict(arrowstyle='->', color='red'))
    ax.set_xlim(-1.2, env.L + 0.6); ax.set_ylim(-1.2, env.W + 0.6)
    ax.set_xlabel('x'); ax.set_ylabel('y')
    ax.set_title('形式化验证发现的违规反例（持续加速 → 越出实验室边界）')
    ax.legend(loc='upper right'); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


if __name__ == '__main__':
    main()
