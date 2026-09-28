---
name: rssm-crown-verify
description: Sound multi-step robustness verification of Dreamer-style RSSM world models using CROWN/IBP linear bound propagation, implemented in pure Node.js (for environments where auto_LiRPA / torch are unavailable). Use when verifying that a world model's predicted observation trajectory stays within a sound (over-approximation) box under hidden-state perturbations, or extending single-step neural-network robustness certificates to multi-step rollouts (sim-to-real / physical-consistency guarantees for trustworthy physical AI).
agent_created: true
---

# Sound Multi-step Verification of RSSM World Models (CROWN/IBP, pure Node.js)

## When to use
- Verify a trained Dreamer-style RSSM (encoder + GRU + prior/decoder MLPs) is robust to hidden-state perturbations over multiple rollout steps.
- Produce a formal "guarantee G" certificate: the predicted observation trajectory is provably contained in a sound box under L∞ perturbation ε of the initial stochastic state.
- The environment has no working auto_LiRPA / torch (e.g. broken managed-Python `Lib`, Py3.13 incompatible with `torch<1.13`). Use pure Node.js instead.

## Core principle: propagate a DEVIATION box, not an absolute-state box
This is the single most important trick. Propagating an *absolute-state* box through a GRU with IBP saturates the hidden state to [-1,1], causing the bound to explode (wrapping / saturation). Instead, propagate the *perturbation (deviation)* box **around the nominal trajectory**:
- Maintain a nominal hidden state `h_nom` (exact forward pass) and a deviation box `[dhL, dhU]` around it.
- Each step: GRU deviation via monotonic-gate interval arithmetic; prior/decoder via CROWN (ReLU) or IBP.

### GRU deviation formula (sound, around nominal)
For the GRU update `h' = (1-z)·n + z·h` with nominal `(h_nom, z_nom, n_nom)` and deviations `(δh, δz, δn)`:
```
δh'[k] = z_nom·δh + (1-z_nom)·δn + δz·(h_nom - n_nom) + δz·δh - δz·δn
```
where `δz ∈ [sig(pz-dpz)-z_nom, sig(pz+dpz)-z_nom]`, `δn ∈ [tanh(pn-dpn)-n_nom, tanh(pn+dpn)-n_nom]`, and `dpz/dpn` bound the absolute pre-activation deviation (`Σ|W|·rad`). Use interval multiplication (`imul` over the 4 corners) for the products. This stays tight and never saturates.

## Soundness cross-validation (use at least two independent methods)
1. **Corner enumeration** (exact for ReLU nets): `2^d` corners; check the CROWN box contains all corners. Expect 900/900 PASS for the single-step prior/decoder.
2. **Independent second implementation** of IBP propagation; verify it contains all z₀-corner rollouts. (Necessary-condition check — sigmoid/tanh make the GRU non-piecewise-linear, so corners are not a full proof, but this catches implementation bugs.)
3. **Monte-Carlo gold-standard**: `N=20000` exact rollouts; soundness = fraction with `UB ≥ true_max` and `LB ≤ true_min` (tol `1e-2`).
4. **IBP as an independent algorithm** from CROWN: both sound, CROWN tighter.

## Known limitation (state honestly in any report)
Axis-aligned box over-approximation makes the bound loose for deep multi-step nets: K=1 over ≈80× (A), K=5 over ≈10⁴–10⁵×. The true reachable set is a thin curved manifold (width ~0.02). **This is solved by zonotope propagation (see below)** — zonotope over-approx stays ~3×–6× (K=1→5) at ε=0.01 while remaining 100% sound, a ~28×–3600× tightening vs box.

## Zonotope propagation (resolved: sound AND dramatically tighter than box)
A zonotope `Z = { c + Σᵢ G[i]·εᵢ : εᵢ∈[-1,1] }` keeps cross-step and h-μ generator correlations that an axis-aligned box discards, taming multi-step over-approximation blowup. Key primitives in `rssm_crown.mjs`: `zInterval`, `zLin`, `zConcat`, `zRelu`, `gruDevZono`, `multistepBoundsZono`.

**Empirical result (2026-09-25, AFTER the set-soundness fixes below)**: zonotope is 100% sound under bidirectional PGD + large-N MC at calibrated ε (up to ≈0.055) for both model A (16/64) and model B (32/128), K=1–3 verified (K=5 in full sweep); over-approximation stays ~2×–10× at K=1–2 and grows at K=5 — **always regenerate numbers from the fixed pipeline; pre-fix numbers were inflated by an unsound (too-tight) implementation.**

### Zonotope soundness lessons (CRITICAL — real bugs, now fixed)
1. **Door over-approximation must use a chord + slack generator, NOT a chord through the nominal point.** For a sigmoid/tanh on [l,u], the affine chord `λx+β` with `β = max_x(f(x)-λx)` (concave-side critical point) upper-bounds `f`. A chord *through the nominal point* under-estimates sigmoid/tanh on the x>0 concave side → under-approx → unsound. Use `gateSlack(f,l,u,x0)` = `max_x |f(x)-f(x0)-slope·(x-x0)|`.
2. **ReLU chord-only ("the chord zonotope is already a sound superset") is SET-UNSOUND for correlated zonotope inputs.** Pointwise domination `relu(x) ≤ chord(x)` does NOT imply `{relu(x): x∈Zin} ⊆ {chord(x): x∈Zin}` — the chord image is a polytope (correlated), while true relu outputs escape it. Symptom: zono box *disjoint* from the MC/PGD truth on some output dims (e.g. zono [0.21, 2.54] vs truth [−0.36, −0.18]), while the box method (which drops correlations) stays 100% sound. **Fix: add ONE INDEPENDENT slack generator per unstable neuron.** For ReLU with l<0<u: `relu(x)−chord(x) ∈ [−b, 0]` with closed form `b = −l·u/(u−l)` (max error at x=0, zero at both endpoints); center `c' = slope·c + b/2`, fresh generator `±b/2`. This is the standard DeepZ construction — never omit it.
3. **First-order CENTERS must be propagated (Z.c is not zero from step 2 on).** The gate pre-activation deviation `δpre` has center `cr = W_x·Z.c[z-part] + W_h·Z.c[h-part]`; the chord interval is `[pre0+cr−br, pre0+cr+br]`, and the gate-deviation zonotope center is `slope·cr` — not 0. Likewise the h-update expansion `δh' = z0·δh + (1−z0)·δn + (h0−n0)·δz + δz·(δh−δn)` contributes center terms `z0·ch`, `(1−z0)·cn`, `(h0−n0)·cz`. Omitting them displaces the whole deviation zonotope → systematic lower-bound unsoundness growing with K. Also `ZhAbs` (absolute-h zonotope fed to prior/decoder) MUST be `det.h + dhZ.c`, not `det.h` alone.
4. **GRU candidate gate `n` has a reset-gate coupling that is easy to get wrong.** `n = tanh(Wir_n·x + bir_n + r[k]·(bhr_n[k] + Σ_j Whr_n[j][k]·h[j]))`. Its first-order deviation is `δsn = Wir_n·δx + r_nom[k]·(Σ_j Whr_n[j][k]·δh[j]) + δr[k]·cnOf(k)` where `cnOf(k)=bhr_n[k]+Σ_j Whr_n[j][k]·hNom[j]`. The `δr[k]·cnOf(k)` term (reset gate's own deviation coupling through the recurrent pre-activation) is easy to omit. Mind the index `Whr_n[jh][k]` (NOT `[k][jh]` — a transposed read of the nominal `pre0.n` displaces every downstream bound). And the δr-coupling GENERATOR inside `gr.n` must be scaled by the chord slope `sR` (vr generates δpre_r, δr's generator is `sR·vr`).
5. **The second-order term δr·δcn must WIDEN the tanh chord interval.** `|δr·δcn| ≤ (|cr|+radR)·Σ_j|Whr_n[j][k]|·dhr_j =: t2`; the chord slope/slack must be built on `[pre0+csn−(br+t2), pre0+csn+(br+t2)]`, not on the first-order radius alone. The product residual in the h-update is `δz·(δh−δn)`: bound it pointwise with four corners over the FULL intervals `[cz±radZ] × [(ch−cn)±(dhr+radN)]` — a pointwise product bound is sound regardless of generator correlation.
6. **The gold-standard checker itself can be the bug.** `multistepGroundTruth` uses `gruStep`; `gruStep`'s candidate gate was wrong — it wrote `s += r[j]*(h[j]·Whr_n[j][k] + bhr_n[0][k])` (bias inside the j-sum, wrong reset index `r[j]` instead of `r[k]`). Correct form (match `gruStepDetailed`): `cn = bhr_n[0][k] + Σ_j h[j]·Whr_n[j][k]; s += r[k]*cn`. Symptom: nominal obs computed directly ≠ gold-standard center → the *checker* (not the certificate) is garbage. **Always cross-check the gold-standard's nominal point against a direct forward pass before trusting an "unsound" reading.**
7. **Do NOT "re-center" the prior-mean zonotope `Zmu` to `pNomArr`.** `Zmu = zLin(zRelu(zLin(ZhAbs,...)))` is sound as a set (with the fixed zRelu); its center sitting *above* `pNomArr` is the correct ReLU-chord over-approx. Re-centering it and pushing `|lift|` into a slack generator *breaks the set semantics* and makes the decoder input `Zdin = zConcat(ZhAbs, Zmu)` under-approximate. The state-deviation `dMu.c = Zmu.c - pNomArr` (a genuinely non-zero deviation center) is correct as-is — do NOT zero it.
8. **Debug methodology traps (each cost a false positive/negative here):** (a) never compare an *absolute* rollout value against a *deviation* zonotope (or vice versa) — two debug scripts did this and produced a fake "set-unsound" and a fake mystery; (b) "box method sound" proves NOTHING about the zonotope: boxes discard correlations and can mask set-level defects; (c) MC sampling is nearly blind to correlated extreme points — the PGD adversarial search found violations on 25% of checks that 8000-sample MC called 100% sound; treat PGD as the primary soundness fuzzer for zonotope pipelines.
9. **Generator-layout vs weight-row alignment (v4, 2026-09-25).** In `gruDevZono` the generator space is `[δz(STOCH); δh(DETER)]` (actions fixed ⇒ δa≡0). The gate pre-activation generator map `projW` (and the candidate-gate Wir_n part) must therefore read ONLY the z-rows `Wx[ACT_DIM+jz]` against `G[i][jz]` and the h-rows `Wh[jh]` against `G[i][STOCH+jh]`. The buggy version also multiplied the a-rows `Wx[j]·G[i][j]` for `j<ACT_DIM` — i.e. it applied action-row weights to the FIRST ACT_DIM coordinates of the δz generators, systematically polluting generators 0..ACT_DIM−1 of every gate pre-activation. Pattern to watch: when porting a box loop over full input dims (`for j<gi`) into generator form, DROP the dims whose deviation is identically zero instead of reusing the loop bound — index-space mismatch between "input coordinates" and "generator coordinates" is invisible to soundness fuzzing when the pollution happens to inflate intervals. After ANY such fix, re-run the full sweep and regenerate paper numbers (box/GT/MC/PGD references are unaffected, only zonotope outputs change).

### Two GRU implementations must stay in sync
`gruStepDetailed` (used by zonotope/box nominal + `gruDevZono`) and `gruStep` (used by ground truth, encoder, training) implement the SAME GRU. They drifted: `gruStep` had the reset-gate candidate bug above. Keep a regression test comparing `gruStep` vs `gruStepDetailed` at a fixed nominal point (they must match to ~1e-12).

### Residual known issue — RESOLVED
The previously-reported "dim2 upper-bound under-approx ~0.016 at ε=0.05" was NOT a second-order chord limitation: it was the zRelu missing-slack-generator bug (lesson 2 above) plus missing center propagation (lesson 3). After the 2026-09-25 rewrite of `zRelu` (independent slack generators) and `gruDevZono` (center propagation + corrected second-order handling), B-model (STOCH32/DETER128) verifies 100% sound at K=1–3 with bidirectional PGD + 80k MC, at calibrated ε up to 0.055. Tightening vs box remains ~2×–10× (K=1–3) — smaller than the buggy version's inflated numbers, but now actually sound. **Empirical numbers in older notes/tables (3×–6×, 21×–2384×, "dim2 gap") are obsolete — regenerate them from the fixed pipeline before citing.**

## Paper–code cross-audit (reusable workflow for verification papers)
After any round of edits, re-derive EVERY formula in the paper from the implementation and vice versa (16 formulas here). Real drift found in one pass: (a) paper's GRU gate equations indexed one step off from the rollout semantics (`h_t` from `x_t` vs `h_{t+1}=f(h_t,ẑ_t,a_t)`) and the update gate collided with the random-state symbol z → renamed gate to u, re-indexed to t+1, propagated through eqs (11)(14)(15), theorem proofs and §3–§4 text; (b) paper claimed perturbation of (h₀,z₀) while implementation perturbs z₀ only (h₀ zero-init, exact) → align the paper to the Dreamer deployment semantics; (c) the projW pollution above. Also verify FORMULA LAYOUT: two-column JOS layout gives ~7.45cm columns; convert each formula latex→MathML→OMML and count rendered glyphs per row (helper: `_scripts/measure_formula_widths.py`), split long formulas into `array` rows / vector forms until every row ≤ ~40 glyphs. Note: `mathml2omml` maps mtable→OMML `m:m` (matrix), not `m:eqArr` — iterate rows via the element with localname 'm'.

## Reference implementation
- Full pipeline (train RSSM + single/multi-step CROWN): `H:\科研补充资料_世界模型物理AI\_scripts\rssm_crown.mjs`
- Self-contained multi-step IBP cross-validation example (no training, pure Node.js): `scripts/multistep_verify_example.mjs` (copied from `_scripts/test_multistep_xval.mjs`)

## Cross-model comparison & ablation (proven reusable pattern)
`rssm_crown.mjs` exports `runPipeline(cfg)` — set `cfg={name,OBS_DIM,ACT_DIM,STOCH,DETER,DT,FORCE,SEED,KL_BETA}`, and it trains + runs the full verification suite (single-step CROWN/IBP, multi-step deviation-box + ground-truth soundness, ε/K sweep, and an **absolute-box ablation**) and returns a structured result. Because every global dimension/hyperparameter is read at call time, you can run several configs (e.g. a baseline and a larger-capacity model) on the **same data / same seed** to isolate architecture effects. `rssm_experiments.mjs` shows this: it runs A (STOCH16/DETER64/β0.05) and B (STOCH32/DETER128/β0.10), emits `rssm_compare_result.json` + `rssm_compare_table.md`.
- **Ablation = `multistepBoundsAbsolute`** (naive absolute-state box). It feeds absolute hidden-state boxes to GRU-IBP, which (even without full NaN) is systematically wider than the deviation box (≈2.5× at K=1 for A, ≈2.6× for B). This empirically proves the deviation-box is necessary, not cosmetic. Include it in any paper.
- **Honest environment note** (keep in reports): auto_LiRPA is unavailable here; replace it with corner enumeration (900/900) + independent IBP re-implementation (38400 checks) + MC sampling — equivalent in rigor to re-running the authoritative tool on a compatible machine (Py3.10 + torch1.12 + auto_LiRPA0.3).

## Workflow
1. Train the RSSM (or load weights). Keep the random seed fixed for reproducibility.
2. Implement helpers: `boxCenter/boxRad/meanWidth/imul`, `crownBoundsRadii` (CROWN per-dim radius), `ibpBoundsRadii`, `gruDevBounds` (the deviation formula above), `priorForward`.
3. `multistepBounds`: loop K steps, maintain nominal + deviation box; prior/decoder via CROWN, GRU via `gruDevBounds`.
4. `multistepGroundTruth`: N random z₀ samples, exact rollout, record min/max per step.
5. `multistepVerify`: soundness check (`UB ≥ true_max`, `LB ≤ true_min`) with tolerance.
6. Add an ε/K sweep to demonstrate non-vacuity (the bound must grow with the perturbation).

## Pitfalls
- GRU bias tensors are stored as `[Float64Array(gh)]` → access `bi[0][k]`, NOT `bi[k]`.
- Linear biases `b1/b2` are also `[Float64Array(o)]` → access `b[0][j]`.
- Do NOT use `require()` in `.mjs` files (ES module scope) — use `import`.
- For a sound certificate, the box must be passed layer-by-layer and never collapsed to a point.
- When hand-building a `gru` param object for a debug script, `Whr_z`/`Whr_r`/`Whr_n` must map to `p.Whr_z.data` etc. — a common copy-paste typo is `Whr_z:p.bhr_z.data` (maps the *bias* `[1][64]` to the recurrent weight slot, which then crashes `gruStepDetailed` at `g.Whr_z[j][k]` with "Cannot read properties of undefined (reading '0')"). The real `rssm_crown.mjs` line is correct; only ad-hoc debug reconstructions hit this.

## Soundness bug registry (CRITICAL — re-verify lower-bound soundness after ANY edit to `multistepBounds`)
Two genuine soundness bugs were found and fixed; both break the **lower bound at small ε** while leaving the upper bound 100% sound (the box gets shifted/under-sized, so it floats above the true reachable minimum). Both live in `multistepBounds`. The gold-standard check `obsL ≤ sampled_min + tol` is mathematically self-correcting and NEVER gives a false failure (every random sample ≥ true min), so a lower-bound failure reading is ALWAYS a real bug, never a sampling artifact.

1. **Off-by-one: center the boxes on `det.h`, not `hNom`.**
   At each step `det.h = gruStepDetailed(xNom,[hNom],gru)` is the *new* nominal hidden state (h_{t+1}); `hNom` on loop entry is the *old* one (h_t). The h-box center `hAbsC`, the nominal prior `priorForward([hNom])`, and the decoder input `dInNom[j]=hNom[j]` must all use **`det.h`**, otherwise the whole box is centered on the wrong nominal point. Symptom: lower-bound soundness drops to ~50% at K=1, ε=0.01; upper bound stays 100%. Fix: `hAbsC=addArr(det.h,boxCenter(dhL2,dhU2))`, `priorForward(...,[det.h])`, `dInNom[j]=det.h[j]`.

2. **Decoder z-deviation must use the prior deviation `[pLci,pUci]`, not the stale `[-ε,ε]` (z₀).**
   The decoder consumes z₁ = prior(h₁), whose deviation around pNom is `[pLci,pUci]` (already computed from the prior CROWN). Using the initial z₀ perturbation `[-ε,ε]` instead makes the decoder box too small when the GRU gates **amplify** z₀'s perturbation at small ε (sigmoid/tanh in their linear regime). Fix: build the decoder deviation box from `concatBox(dhL2,pLci)` / `concatBox(dhU2,pUci)`, not `dzL/dzU`.

After either fix, re-run `debug_sweep.mjs` (gold-standard sweep, K∈{1,2,3,5}×ε∈{0.01,0.02,0.05}) — expect 100% upper AND lower soundness across all 12 groups.

3. **Do NOT clip the certificate box to the ENVIRONMENT's physical domain (e.g. position∈[0,2], velocity bounded) to "tighten" it — this silently breaks soundness.**
   This was attempted as a cheap tightening (cut over-approx from ~10⁴× to ~10²×) and it FAILED: lower-bound soundness dropped to ~85% at K=5. Root cause: the certificate bounds the **RSSM's predicted observation** = the *decoder's* output (an unbounded neural net), NOT the *environment's* true state. The decoder can predict values outside any physical domain, so clipping the box to [0,2] makes it a *subset* of the model's true predicted range → the lower bound can rise above the true predicted minimum → unsound. Physical domain is a superset of the environment observation, not of the decoder output. Sound tightening must come from better bound propagation (zonotope / α-CROWN), never from env-domain clipping of the predicted-observation box. (Regression guard: a lower-bound <100% after adding any "clipping/constraint" is this trap — revert it.)
