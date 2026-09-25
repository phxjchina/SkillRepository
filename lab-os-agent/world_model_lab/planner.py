"""
planner.py — 模型预测控制（MPC）：在"想象"里规划

核心思想（世界模型的拿手好戏）：智能体**不触碰真实世界**，而是在自己学得的
世界模型内部，沿多条候选动作序列"脑补"未来，比较后果，选出累积奖励最高的
那一条。这就是 Dreamer 系列论文里 "improve behavior by imagining future
scenarios before committing to actions"——先想清楚再动手。

这也正是物理 AI 闭环中"推理"这一半：感知(视频/图像+声音) → 世界模型推理/想象
→ 行动 → 真实反馈回灌。本文件演示"推理"这一环。
"""
import numpy as np


class MPC:
    def __init__(self, wm, env, horizon=12, n_candidates=300, seed=0):
        self.wm = wm
        self.env = env
        self.h = horizon
        self.n = n_candidates
        self.rng = np.random.default_rng(seed)
        self.da = env.act_dim
        self.max_acc = env.max_acc

    def _rollout(self, s0, seq):
        s = np.asarray(s0, float)
        total = 0.0
        traj = [s.copy()]
        for a in seq:
            s2, _ = self.wm.predict(s, a)
            r = self.env.task_reward(s2)   # 在"想象"状态上用任务奖励判定
            total += r
            traj.append(s2.copy())
            s = s2
            if r >= 2.0:                   # 想象中已抵达目标，提前结束
                break
        return total, np.array(traj)

    def plan(self, s0):
        """返回 (best_return, best_traj, best_seq)。完全在世界模型内完成。"""
        best = None
        for _ in range(self.n):
            seq = self.rng.uniform(-self.max_acc, self.max_acc,
                                   size=(self.h, self.da))
            ret, traj = self._rollout(s0, seq)
            if best is None or ret > best[0]:
                best = (ret, traj, seq)
        return best

    def plan_cem(self, s0, iters=14, pop=150, elite=30, alpha=0.5, std0=1.5):
        """交叉熵方法(CEM)规划：在想象里迭代优化动作序列，导向目标区。

        比随机采样专业得多（PETS / POPLIN 等 model-based RL 标准规划器），
        能从'朝目标方向'的初值出发，逐步收敛到高回报动作序列。
        全程在世界模型内部完成——'先想清楚，再动手'。
        """
        H, da = self.h, self.da
        g0, g1, g2, g3 = self.env.goal
        gcx, gcy = (g0 + g2) / 2.0, (g1 + g3) / 2.0
        dx, dy = gcx - s0[0], gcy - s0[1]
        nrm = float(np.hypot(dx, dy)) + 1e-6
        # 初值：朝目标方向的恒定加速度
        ax0 = dx / nrm * self.max_acc * 0.7
        ay0 = dy / nrm * self.max_acc * 0.7
        mu = np.column_stack([np.full(H, ax0), np.full(H, ay0)])
        std = np.ones((H, da)) * std0
        best = None
        for _ in range(iters):
            seqs = mu[None, :, :] + std[None, :, :] * self.rng.normal(size=(pop, H, da))
            seqs = np.clip(seqs, -self.max_acc, self.max_acc)
            scores = np.array([self._rollout(s0, seq)[0] for seq in seqs])
            ei = np.argsort(scores)[-elite:]
            em = seqs[ei]
            mu = alpha * em.mean(0) + (1 - alpha) * mu
            std = alpha * em.std(0) + (1 - alpha) * std
            if best is None or scores[ei[-1]] > best[0]:
                best = (float(scores[ei[-1]]), self._rollout(s0, mu)[1], mu.copy())
        return best
