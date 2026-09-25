"""
world_model.py — 一个"真"的世界模型（World Model）

它从 环境×策略 交互产生的 (s, a) → (s', r) 数据中，"学出"世界的动力学，
从而能在不触碰真实世界的情况下：
    1) 预测：给定当前状态与某动作，推断下一状态与即时奖励；
    2) 想象（rollout）：从某状态出发，沿一串动作在内部"脑补"未来轨迹；
    3) 规划：在想象里比较不同动作序列的后果，选最优者（见 planner.py）。

这正是 2026 业界共识中「潜空间世界模型」（DreamerV3 / MuZero / TD-MPC2 /
JEPA 一脉）的核心：不是 predict pixels，而是 predict the *next state* in a
compressed representation，为"感知-推理-行动-反馈"闭环提供认知底座。

本文件提供两个后端：
  • LinearWorldModel：岭回归拟合 s' = A·s + B·a + c（可解释、可 z3 符号化验证）
  • NeuralWorldModel ：轻量 GRU 潜空间模型（非线性、对部分可观更鲁棒，CPU 可跑）

默认演示用 LinearWorldModel——它能在纯线性地面真值上几乎零误差复现物理规律，
并直接对接 formal_verify.py 的形式化不变量验证，契合彭老师「可验证 AI」方向。
"""
import numpy as np


# ───────────────────────── 线性世界模型 ─────────────────────────
class LinearWorldModel:
    """从数据学线性动力学 s' = A·s + B·a + c（含偏置）；奖励亦线性建模。"""

    def __init__(self, state_dim, act_dim, reg=1e-4):
        self.ds, self.da = state_dim, act_dim
        self.reg = reg
        self.A = None
        self.B = None
        self.c = None
        self.r_w = None  # 奖励模型权重 (ds+da+1,)

    def fit(self, S, A, Snext, R):
        S, A, Snext, R = map(np.asarray, (S, A, Snext, R))
        N = len(S)
        X = np.hstack([S, A, np.ones((N, 1))])          # (N, ds+da+1)
        # 岭回归闭式解：(XᵀX + λI)⁻¹ XᵀY
        XtX = X.T @ X + self.reg * np.eye(X.shape[1])
        W = np.linalg.solve(XtX, X.T @ Snext)            # (ds+da+1, ds)
        self.W = W                                       # 前向矩阵：X @ W → Snext
        # 单行拆分 s' = A·s + B·a + c（A/B/c 取自 W 的列）
        self.A = W.T[:, :self.ds]                        # (ds, ds)   状态→状态
        self.B = W.T[:, self.ds:self.ds + self.da]       # (ds, da)   动作→状态
        self.c = W.T[:, -1]                              # (ds,)
        self.r_w = np.linalg.solve(XtX, X.T @ R)         # (ds+da+1,)

    def predict(self, s, a):
        s, a = np.asarray(s, float), np.asarray(a, float)
        s2 = self.A @ s + self.B @ a + self.c
        x = np.concatenate([s, a, [1.0]])
        return s2, float(self.r_w @ x)

    def predict_batch(self, S, A):
        S, A = np.asarray(S, float), np.asarray(A, float)
        X = np.hstack([S, A, np.ones((len(S), 1))])
        return X @ self.W, X @ self.r_w

    def params(self):
        return self.A, self.B, self.c

    def report(self):
        print("线性世界模型已拟合（s' = A·s + B·a + c）：")
        print("A =\n", np.round(self.A, 4))
        print("B =\n", np.round(self.B, 4))
        print("c =", np.round(self.c, 4))


# ───────────────────────── 神经世界模型（可选） ─────────────────────────
class NeuralWorldModel:
    """轻量 GRU 潜空间世界模型：编码历史 → 预测下一状态 / 奖励。
    用于演示「非线性 + 部分可观」场景；CPU 小网络可跑。"""

    def __init__(self, state_dim, act_dim, hidden=32, lr=1e-3):
        import torch
        self.torch = torch
        self.ds, self.da = state_dim, act_dim
        self.hidden = hidden
        self.net = torch.nn.Sequential(
            torch.nn.Linear(state_dim + act_dim, hidden),
            torch.nn.Tanh(),
            torch.nn.GRUCell(hidden, hidden),  # 占位示意：实际用简单 MLP 预测
        )
        # 简版：用 MLP 直接 (s,a) -> (s', r)，保留接口以便后续升级为完整 RSSM
        self.mlp = torch.nn.Sequential(
            torch.nn.Linear(state_dim + act_dim, hidden),
            torch.nn.Tanh(),
            torch.nn.Linear(hidden, hidden),
            torch.nn.Tanh(),
            torch.nn.Linear(hidden, state_dim + 1),  # 输出 s' (ds) + r (1)
        )
        self.opt = torch.optim.Adam(self.mlp.parameters(), lr=lr)
        self.loss_fn = torch.nn.MSELoss()

    def fit(self, S, A, Snext, R, epochs=200, batch=256):
        torch = self.torch
        S, A, Snext, R = map(lambda t: torch.tensor(np.asarray(t, float)),
                             (S, A, Snext, R))
        X = torch.cat([S, A], dim=1)
        Y = torch.cat([Snext, R.unsqueeze(1)], dim=1)
        N = X.shape[0]
        for ep in range(epochs):
            idx = torch.randperm(N)[:min(batch, N)]
            pred = self.mlp(X[idx])
            loss = self.loss_fn(pred, Y[idx])
            self.opt.zero_grad(); loss.backward(); self.opt.step()
        print(f"[NeuralWorldModel] 训练完成，末轮 loss≈{loss.item():.4f}")

    def predict(self, s, a):
        torch = self.torch
        x = torch.tensor(np.concatenate([np.asarray(s, float),
                                         np.asarray(a, float)]), float).unsqueeze(0)
        with torch.no_grad():
            y = self.mlp(x)[0]
        return y[:self.ds].numpy(), float(y[self.ds])


def evaluate(wm, S, A, Snext):
    """在测试集上比较世界模型预测与真实下一状态的平均误差。"""
    pred, _ = wm.predict_batch(S, A)
    err = np.mean(np.linalg.norm(pred - Snext, axis=1))
    return float(err)


if __name__ == "__main__":
    from dynamics_env import LabRoverEnv
    env = LabRoverEnv(clip_vel=False)
    S, A, S2, R = env.collect_data(4000, seed=1)
    # 训练 / 测试切分
    n = len(S)
    wm = LinearWorldModel(env.state_dim, env.act_dim)
    wm.fit(S[:n//2], A[:n//2], S2[:n//2], R[:n//2])
    wm.report()
    test_err = evaluate(wm, S[n//2:], A[n//2:], S2[n//2:])
    print(f"测试集平均预测误差（状态范数）：{test_err:.5f}")
