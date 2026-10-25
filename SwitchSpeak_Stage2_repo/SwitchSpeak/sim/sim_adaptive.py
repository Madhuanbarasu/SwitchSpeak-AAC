"""SwitchSpeak adaptive scan-order simulation (reproducible).
Compares scan time per selection for: static order, usage-adaptive order,
usage+context adaptive order, and a stability-bounded variant.
Run: python3 sim_adaptive.py   -> writes out/sim_results.json
"""
import json, numpy as np

N_SYM, STEP_S, N_CTX = 12, 1.5, 4          # symbols, seconds per scan step, contexts (morning/meal/school/night)
N_SEL, WARM, SEEDS = 6000, 500, 30
DECAY = 0.995

def zipf(n, s=1.0):
    w = 1.0 / np.arange(1, n + 1) ** s
    return w / w.sum()

def make_user(rng):
    base = np.zeros(N_SYM); base[rng.permutation(N_SYM)] = zipf(N_SYM)      # user's overall habits
    ctx = []
    for _ in range(N_CTX):
        c = np.zeros(N_SYM); c[rng.permutation(N_SYM)] = zipf(N_SYM)         # context-specific habits
        p = 0.4 * base + 0.6 * c
        ctx.append(p / p.sum())
    return ctx

def positions(order):                      # 1-based scan position of each symbol
    pos = np.empty(N_SYM, int); pos[order] = np.arange(1, N_SYM + 1); return pos

def run(policy, seed):
    rng = np.random.default_rng(seed)
    ctx_p = make_user(rng)
    static = rng.permutation(N_SYM)                       # fixed, hand-set order
    g = np.zeros(N_SYM); c = np.zeros((N_CTX, N_SYM))
    order = static.copy(); steps, churn = [], []
    BLOCK = 60                                            # a context (e.g. mealtime) lasts ~60 selections
    ctx_seq = np.repeat(rng.integers(0, N_CTX, N_SEL // BLOCK + 1), BLOCK)[:N_SEL]
    for t in range(N_SEL):
        k = ctx_seq[t]
        sym = rng.choice(N_SYM, p=ctx_p[k])
        if policy == "static":
            cur = static
        elif policy == "adaptive":
            cur = np.argsort(-g, kind="stable")
        else:
            score = c[k] + 0.25 * g
            target = np.argsort(-score, kind="stable")
            cur = target
        pos = positions(cur)
        if t >= WARM:
            steps.append(pos[sym])
            churn.append(int((positions(order) != pos).sum()) if policy != "static" else 0)
        order = cur
        g = g * DECAY; g[sym] += 1
        c[k] = c[k] * DECAY; c[k][sym] += 1
    return float(np.mean(steps)), float(np.mean(churn))

res = {}
for pol in ["static", "adaptive", "adaptive_context"]:
    out = np.array([run(pol, s) for s in range(SEEDS)])
    res[pol] = {"steps_mean": float(out[:, 0].mean()), "steps_sd": float(out[:, 0].std()),
                "seconds_mean": float(out[:, 0].mean() * STEP_S), "churn_mean": float(out[:, 1].mean())}
base = res["static"]["seconds_mean"]
for pol in res: res[pol]["reduction_pct"] = 100 * (1 - res[pol]["seconds_mean"] / base)
res["params"] = dict(symbols=N_SYM, step_s=STEP_S, contexts=N_CTX, context_block=60, selections=N_SEL, warmup=WARM, seeds=SEEDS, decay=DECAY)
json.dump(res, open("out/sim_results.json", "w"), indent=2)
for k, v in res.items(): print(k, v)
