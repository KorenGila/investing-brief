import json, numpy as np, pandas as pd, sys
H = sys.argv[1]
acm = pd.read_pickle(f'{H}/acm.pkl')
rule = json.load(open(f'{H}/rule2.json'))['du4']
RHO, BPI, BDU = rule['rho'], rule['b'][0], rule['b'][1]
PHI_PI, PHI_U, K_DECAY, L30, NQ = 0.956, 0.982, 0.13, 0.89, 4 * 32
VARIANT = 'decay_from_H'
def acm_state(date):
    row = acm.loc[:date].dropna(subset=['ACMRNY10']).iloc[-1]
    rn = np.array([row[f'ACMRNY{n:02d}'] for n in range(1, 11)]); tp = np.array([row[f'ACMTP{n:02d}'] for n in range(1, 11)])
    fwd = np.array([rn[0]] + [(n + 1) * rn[n] - n * rn[n - 1] for n in range(1, 10)])
    return np.array([fwd[min(q // 4, 9)] for q in range(NQ)]), tp
def tp_loading(n, tp):
    if n >= 10: return 1.0 if n == 10 else L30
    if n < 1: return tp[0] / tp[9] * n
    i = int(np.floor(n)); f = n - i; lo = tp[i - 1] / tp[9]; hi = tp[min(i, 9)] / tp[9]
    return lo + f * (hi - lo)
def rule_path(dpi, du, drs, nq):
    q = np.arange(nq); ramp = np.minimum(q / 4.0, 1.0)
    pi = dpi * np.where(q <= 4, ramp, PHI_PI ** (q - 4)); u = du * np.where(q <= 4, ramp, PHI_U ** (q - 4)); rs = drs * ramp
    ul = np.concatenate([np.zeros(4), u[:-4]]); tgt = rs + BPI * pi + BDU * (u - ul)
    d = np.zeros(nq)
    for t in range(1, nq): d[t] = RHO * d[t - 1] + (1 - RHO) * tgt[t]
    return d
def fed_path(dpi, du, drs):
    """Deviation of the Fed rate from market pricing, by quarter."""
    hold = 4 if VARIANT == 'decay_from_H' else 12
    r = rule_path(dpi, du, drs, hold + 1)
    d = np.zeros(NQ); d[:hold + 1] = r
    D = r[hold]
    for t in range(hold + 1, NQ):
        tau = (t - hold) / 4.0
        d[t] = drs + (D - drs) * np.exp(-K_DECAY * tau)
    return d
def curve_change(m, tp, d, dtp10, tenors):
    out = {}
    for n in tenors:
        N = max(1, int(round(4 * n)))
        out[n] = float(m[4:4 + N].mean() - m[0:N].mean() + d[4:4 + N].mean() + dtp10 * tp_loading(n, tp))
    return out
