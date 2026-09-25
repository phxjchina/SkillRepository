"""
dynamics_env.py — 实验室巡检小车（Lab Rover）地面真值动力学环境

这是"真实世界"的一面：一个 2D 连续时间动力学系统，模拟在西安航空学院
「信息物理融合系统创客空间」里的一台地面巡检小车。

状态 s = [x, y, vx, vy]   位置 + 速度（实验室平面直角坐标系）
动作 a = [ax, ay]          加速度指令（受 max_acc 限幅）

世界含：
  - 矩形实验室边界 [0,L]×[0,W]
  - 若干矩形禁区（桌子 / 设备），进入即碰撞
  - 一个目标区（到达即成功）

动力学（clip_vel=False 时为严格线性，便于世界模型学习 + 形式化验证）：
    x'  = x + vx·dt + 0.5·ax·dt²
    vx' = (vx + ax·dt)·(1 − damp·dt)
写成标准线性形式   s' = A·s + B·a + c   即可被 z3 符号化验证。

本文件是"物理世界"本体，与 AI 无关；世界模型将在 world_model.py 中
从它与策略交互产生的数据里"学出"这套动力学。
"""
import numpy as np


class LabRoverEnv:
    def __init__(self, L=10.0, W=6.0, dt=0.1, damp=0.1,
                 max_acc=3.0, max_vel=4.0, clip_vel=False):
        self.L, self.W = L, W
        self.dt, self.damp = dt, damp
        self.max_acc, self.max_vel = max_acc, max_vel
        self.clip_vel = clip_vel  # 真实交互用 True（限幅，非线性）；验证用 False
        # 禁区（桌 / 设备）：(x0, y0, x1, y1)
        self.obstacles = [(2.0, 2.0, 3.5, 3.5),
                          (6.0, 1.0, 7.0, 2.0),
                          (7.5, 3.5, 9.0, 5.0)]
        # 目标区
        self.goal = (0.8, 4.8, 1.8, 5.8)
        self.state = None
        self.state_dim = 4
        self.act_dim = 2

    # ── 标准接口 ──────────────────────────────────────────────
    def reset(self, state=None):
        if state is None:
            state = np.array([0.4, 0.4, 0.0, 0.0], dtype=float)
        self.state = np.array(state, dtype=float)
        return self.state.copy()

    def step(self, a):
        a = np.clip(np.array(a, dtype=float), -self.max_acc, self.max_acc)
        x, y, vx, vy = self.state
        dt, d = self.dt, self.damp
        nx = x + vx * dt + 0.5 * a[0] * dt * dt
        ny = y + vy * dt + 0.5 * a[1] * dt * dt
        nvx = (vx + a[0] * dt) * (1.0 - d * dt)
        nvy = (vy + a[1] * dt) * (1.0 - d * dt)
        if self.clip_vel:
            sp = np.hypot(nvx, nvy)
            if sp > self.max_vel:
                nvx, nvy = nvx / sp * self.max_vel, nvy / sp * self.max_vel
        self.state = np.array([nx, ny, nvx, nvy], dtype=float)
        reward, done, info = self._aux()
        return self.state.copy(), reward, done, info

    def task_reward(self, s):
        """基于状态的连续任务奖励：鼓励接近目标区；进入目标区给大额正奖励。"""
        x, y, _, _ = s
        gx0, gy0, gx1, gy1 = self.goal
        gxc, gyc = (gx0 + gx1) / 2.0, (gy0 + gy1) / 2.0
        if gx0 <= x <= gx1 and gy0 <= y <= gy1:
            return 2.0
        return -0.1 * float(np.hypot(x - gxc, y - gyc))

    def _aux(self):
        """奖励：边界/碰撞重罚并终止；否则用连续任务奖励（鼓励接近目标）。"""
        x, y, vx, vy = self.state
        if not (0.0 <= x <= self.L and 0.0 <= y <= self.W):
            return -5.0, True, {'event': 'boundary'}
        for (x0, y0, x1, y1) in self.obstacles:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return -5.0, True, {'event': 'collision'}
        r = self.task_reward(self.state)
        done = (r >= 2.0)
        info = {'event': 'goal'} if done else {}
        return r, done, info

    # ── 线性参数（供世界模型 / 形式化验证复用，要求 clip_vel=False）──
    def linear_params(self):
        """返回严格线性动力学 s' = A·s + B·a 的 (A, B)。damp 项并入 A。"""
        dt, d = self.dt, self.damp
        k = 1.0 - d * dt  # 阻尼因子，同时作用于速度项与加速度项
        A = np.array([
            [1.0, 0.0, dt, 0.0],
            [0.0, 1.0, 0.0, dt],
            [0.0, 0.0, k,   0.0],
            [0.0, 0.0, 0.0, k],
        ])
        B = np.array([
            [0.5*dt*dt, 0.0],
            [0.0,       0.5*dt*dt],
            [k*dt,      0.0],
            [0.0,       k*dt],
        ])
        return A, B

    # ── 安全不变量（供形式化验证 / 物理 AI 修正使用）──────────
    def in_safe(self, s):
        """状态是否处于安全集（不越界、不超速、不进禁区）。"""
        x, y, vx, vy = s
        if not (0.0 <= x <= self.L and 0.0 <= y <= self.W):
            return False
        if abs(vx) > self.max_vel or abs(vy) > self.max_vel:
            return False
        for (x0, y0, x1, y1) in self.obstacles:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return False
        return True

    def safe_constraints_z3(self, s_vars):
        """把安全不变量翻译成 z3 约束列表（s_vars 为 4 个 z3 实变量）。"""
        from z3 import Or
        x, y, vx, vy = s_vars
        cons = [0.0 <= x, x <= self.L, 0.0 <= y, y <= self.W,
                -self.max_vel <= vx, vx <= self.max_vel,
                -self.max_vel <= vy, vy <= self.max_vel]
        for (x0, y0, x1, y1) in self.obstacles:
            # NOT (x0<=x<=x1 AND y0<=y<=y1)
            cons.append(Or(x < x0, x > x1, y < y0, y > y1))
        return cons

    # ── 数据采集（随机游走，供训练世界模型）─────────────────
    def collect_data(self, n_steps=4000, seed=0):
        rng = np.random.default_rng(seed)
        S, A, S2, R = [], [], [], []
        s = self.reset()
        for _ in range(n_steps):
            a = rng.uniform(-self.max_acc, self.max_acc, size=2)
            s2, r, done, _ = self.step(a)
            S.append(s); A.append(a); S2.append(s2); R.append(r)
            s = s2
            if done:
                s = self.reset()
        return (np.array(S), np.array(A), np.array(S2), np.array(R))


if __name__ == "__main__":
    # 自检：线性参数应精确复现 clip_vel=False 的一步动力学
    env = LabRoverEnv(clip_vel=False)
    A, B = env.linear_params()
    s = np.array([1.0, 2.0, 0.5, -0.3])
    a = np.array([1.2, -0.8])
    s_pred = A @ s + B @ a
    s_true = env.reset(s.copy()); s_true, _, _, _ = env.step(a)
    print("线性预测:", np.round(s_pred, 6))
    print("环境真实:", np.round(s_true, 6))
    print("最大误差:", np.max(np.abs(s_pred - s_true)))
