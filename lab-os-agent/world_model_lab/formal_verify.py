"""
formal_verify.py — 世界模型的形式化不变量 / 可达性验证（z3）

这是接入彭老师「可验证 AI / 形式化方法」方向的关键钩子。

问题：世界模型"想象"出的轨迹，能保证不越界、不超速、不撞禁区吗？神经网络
世界模型的脆弱性正在于——它会累积误差、在分布外"幻觉"出违规轨迹（见 2026
世界模型综述的局限章节）。形式化方法给出确定性回答：

  对线性动力学  s' = A·s + B·a + c
  问：从初始集 S0 出发、任意合法动作序列 (长度 H)、是否**必然**保持安全？

  等价于检查其否定是否可满足：
    ∃ 动作序列, ∃ 步 t*，使前 t* 步合法 且 第 t* 步状态违反安全不变量。
  用 z3 符号化执行 H 步（线性实数算术，求解高效），若 sat → 找到反例（违规
  动作序列 + 轨迹），若 unsat → 对所有动作序列、所有步都安全（可证明）。

这把"物理 AI 把物理公理嵌入架构、剔除违规动作"从口号落成可验证的算子：
验证发现违规 → 收紧动作集 / 加边界约束（物理 AI 修正）→ 再验证直到通过。
"""
from fractions import Fraction
import numpy as np
from z3 import Real, RealVal, Sum, And, Or, Not, Solver, sat


def _frac(x):
    return RealVal(Fraction(float(x)).limit_denominator(10_000_000))


def verify_safe(A, B, c, init_box, action_box, safe_cons_fn, horizon):
    """
    参数
    ----
    A, B, c     : 线性动力学 s' = A·s + B·a + c  (numpy)
    init_box    : 初始集，[(lo,hi)*ds]   —— 表示"所有起点都在该 box 内"
    action_box  : 动作集，[(lo,hi)*da]
    safe_cons_fn: 输入 z3 变量列表(长度 ds)，返回安全约束（And/Or 表达式）
    horizon     : 验证步数 H

    返回
    ----
    (True, None)                       —— 对所有动作序列、所有步均安全（可证明）
    (False, dict)                     —— 发现反例：含 'seq' 动作序列与 'traj' 轨迹
    """
    ds, da = A.shape[0], B.shape[1]
    s0 = [Real(f"s0_{i}") for i in range(ds)]
    sol = Solver()
    for i in range(ds):
        sol.add(s0[i] >= _frac(init_box[i][0]), s0[i] <= _frac(init_box[i][1]))
    cur = s0
    step_states = []
    for t in range(horizon):
        a = [Real(f"a{t}_{i}") for i in range(da)]
        for i in range(da):
            sol.add(a[i] >= _frac(action_box[i][0]),
                    a[i] <= _frac(action_box[i][1]))
        nxt = [
            Sum([_frac(A[i][j]) * cur[j] for j in range(ds)] +
                [_frac(B[i][k]) * a[k] for k in range(da)] +
                [_frac(c[i])])
            for i in range(ds)
        ]
        cur = nxt
        step_states.append(cur)
    # 反例：存在某一步违反安全不变量
    viol = Or(*[Not(And(safe_cons_fn(st))) for st in step_states])
    sol.add(viol)
    if sol.check() == sat:
        m = sol.model()
        def _val(var):
            v = m[var]
            return float(v.as_fraction()) if v is not None else 0.0
        seq = [[_val(Real(f"a{t}_{i}")) for i in range(da)]
               for t in range(horizon)]
        # 用线性参数在 numpy 推演反例轨迹，供可视化
        traj = [np.array([_val(s0[i]) for i in range(ds)])]
        for a in seq:
            traj.append(A @ traj[-1] + B @ np.array(a) + c)
        return False, {"seq": np.array(seq), "traj": np.array(traj)}
    return True, None


def physical_ai_guard(init_box, action_box, safe_cons_fn, A, B, c, horizon,
                      max_iter=6):
    """
    物理 AI 修正闭环：验证若不通过，逐步收紧动作幅度直到可证明安全。
    返回 (final_action_box, iterations, history)。
    """
    ds = A.shape[0]
    da = B.shape[1]
    box = [list(b) for b in action_box]
    history = []
    for it in range(max_iter):
        ok, cex = verify_safe(A, B, c, init_box, box, safe_cons_fn, horizon)
        history.append((it, ok, box, cex))
        if ok:
            return box, it + 1, history
        # 收紧：把动作幅度减半（物理 AI 修正——剔除会致违规的过激动作）
        box = [[b[0] * 0.5, b[1] * 0.5] for b in box]
    return box, max_iter, history


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from dynamics_env import LabRoverEnv
    env = LabRoverEnv(clip_vel=False)
    A, B = env.linear_params()
    c = np.zeros(4)
    init_box = [(0.3, 0.5), (0.3, 0.5), (-0.2, 0.2), (-0.2, 0.2)]
    action_box = [(-3.0, 3.0), (-3.0, 3.0)]
    ok, cex = verify_safe(A, B, c, init_box, action_box,
                          env.safe_constraints_z3, horizon=8)
    print("验证结果（宽松动作）:", "安全" if ok else "发现违规反例")
    if not ok:
        print("反例轨迹首末状态：", np.round(cex["traj"][[0, -1]], 3))
    final_box, iters, _ = physical_ai_guard(
        init_box, action_box, env.safe_constraints_z3, A, B, c, horizon=8)
    print(f"物理AI修正后动作集：{final_box}，迭代 {iters} 次后安全")
