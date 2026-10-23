"""Final Fed rule: ff_t = rho*ff_{t-1} + (1-rho)*[r*_t + 2 + b_pi*(pi_t - 2) + b_du*du4_t]. Writes rule2.json."""
import sys, json, numpy as np, pandas as pd
H = sys.argv[1]
ff = pd.read_pickle(f'{H}/ff.pkl'); pce = pd.read_pickle(f'{H}/pce.pkl'); un = pd.read_pickle(f'{H}/un.pkl'); lw = pd.read_pickle(f'{H}/lw.pkl')
core = (pce['core'] / pce['core'].shift(12) - 1) * 100
Q = lambda s: s.groupby(s.index.asfreq('Q')).mean()
q = pd.DataFrame({'ff': Q(ff), 'pi': Q(core), 'u': Q(un)}).join(lw[['gap', 'rstar']])
q['ustar'] = q['u'].rolling(40, min_periods=40).mean(); q['ugap'] = -2 * (q['u'] - q['ustar'])
q['du4'] = q['u'] - q['u'].shift(4); q['ff_l'] = q['ff'].shift(1)
s = q.loc['1988Q1':'2026Q2'].dropna(); s = s[(s['ff'] > 0.5) & (s['ff_l'] > 0.5)]
res = {}
for cols in (['du4'], ['ugap', 'du4']):
    best = None
    for rho in np.arange(0.5, 0.981, 0.005):
        y = s['ff'] - rho * s['ff_l'] - (1 - rho) * (s['rstar'] + 2)
        X = np.column_stack([(1 - rho) * (s['pi'] - 2)] + [(1 - rho) * s[c] for c in cols])
        b, *_ = np.linalg.lstsq(X, y.values, rcond=None); e = y.values - X @ b; sse = e @ e
        if best is None or sse < best[0]: best = (sse, rho, b, e)
    sse, rho, b, e = best
    tgt = lambda row: row['rstar'] + 2 + b[0] * (row['pi'] - 2) + sum(bb * row[c] for bb, c in zip(b[1:], cols))
    errs = []; ep = {}; idx = list(s.index)
    for i in range(len(idx) - 4):
        if (idx[i + 4] - idx[i]).n != 4: continue
        f = s['ff'].iloc[i]
        for k in range(1, 5): f = rho * f + (1 - rho) * tgt(s.iloc[i + k])
        errs.append(s['ff'].iloc[i + 4] - f); ep[str(idx[i])] = (round(s['ff'].iloc[i + 4] - s['ff'].iloc[i], 2), round(f - s['ff'].iloc[i], 2))
    X = np.column_stack([(1 - rho) * (s['pi'] - 2)] + [(1 - rho) * s[c] for c in cols]); s2 = sse / (len(s) - len(b) - 1)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X))); sstot = ((s['ff'] - s['ff'].mean()) ** 2).sum()
    r = dict(cols=cols, rho=round(float(rho), 3), b=[round(float(x), 3) for x in b], se=[round(float(x), 3) for x in se], sd=round(float(np.sqrt(s2)), 3),
             r2=round(float(1 - sse / sstot), 3), dyn4=round(float(np.sqrt(np.mean(np.square(errs)))), 3), n=len(s))
    print(r)
    res['+'.join(cols)] = dict(r, episodes=ep, fit=[[str(i), round(float(a), 2), round(float(a - ee), 2)] for i, a, ee in zip(s.index, s['ff'], e)])
json.dump(res, open(f'{H}/rule2.json', 'w'))
