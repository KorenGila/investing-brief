"""Inertial Taylor rule with a time-varying neutral rate.
ff_t = rho*ff_{t-1} + (1-rho)*[r*_t + 2 + b_pi*(pi_t - 2) + b_x*x_t] + e_t
Grid search over rho; OLS for b_pi, b_x given rho. Two slack measures: LW output gap, unemployment gap."""
import sys, json
import numpy as np, pandas as pd

H = sys.argv[1]
ff = pd.read_pickle(f'{H}/ff.pkl'); pce = pd.read_pickle(f'{H}/pce.pkl')
un = pd.read_pickle(f'{H}/un.pkl'); lw = pd.read_pickle(f'{H}/lw.pkl')
core = (pce['core'] / pce['core'].shift(12) - 1) * 100
Q = lambda s: s.groupby(s.index.asfreq('Q')).mean()
q = pd.DataFrame({'ff': Q(ff), 'pi': Q(core), 'u': Q(un)}).join(lw[['gap', 'rstar']])
# unemployment gap: u* = 10-year trailing mean of unemployment (slow-moving natural rate proxy)
q['ustar'] = q['u'].rolling(40, min_periods=40).mean()
q['ugap'] = -2.0 * (q['u'] - q['ustar'])  # Okun: 1 point of unemployment ~ 2 points of output
q['ff_l'] = q['ff'].shift(1)
s = q.loc['1988Q1':'2026Q2'].dropna()
s = s[(s['ff'] > 0.5) & (s['ff_l'] > 0.5)]

def fit(xcol):
    best = None
    for rho in np.arange(0.50, 0.981, 0.005):
        y = s['ff'] - rho * s['ff_l'] - (1 - rho) * (s['rstar'] + 2)
        X = np.column_stack([(1 - rho) * (s['pi'] - 2), (1 - rho) * s[xcol]])
        b, *_ = np.linalg.lstsq(X, y.values, rcond=None)
        e = y.values - X @ b
        sse = e @ e
        if best is None or sse < best[0]:
            best = (sse, rho, b, e)
    sse, rho, b, e = best
    n = len(e); sd = np.sqrt(sse / (n - 3))
    fitted = s['ff'] - e
    r2 = 1 - sse / ((s['ff'] - s['ff'].mean()) ** 2).sum()
    # in-sample 4-quarter-ahead dynamic forecast error of the rule (iterate rule 4 quarters from actual)
    errs = []
    idx = list(s.index)
    for i in range(len(idx) - 4):
        if (idx[i + 4] - idx[i]).n != 4: continue
        f = s['ff'].iloc[i]
        for k in range(1, 5):
            row = s.iloc[i + k]
            f = rho * f + (1 - rho) * (row['rstar'] + 2 + b[0] * (row['pi'] - 2) + b[1] * row[xcol])
        errs.append(s['ff'].iloc[i + 4] - f)
    errs = np.array(errs)
    return {'rho_q': round(float(rho), 3), 'b_pi': float(b[0]), 'b_x': float(b[1]), 'r2': float(r2), 'resid_sd': float(sd), 'n': int(n),
            'dyn4_rmse': float(np.sqrt((errs ** 2).mean())), 'dyn4_n': int(len(errs)),
            'fit': [[str(i), round(float(a), 2), round(float(f), 2)] for i, a, f in zip(s.index, s['ff'], fitted)]}

out = {'lwgap': fit('gap'), 'ugap': fit('ugap')}
last = q.dropna(subset=['pi']).iloc[-1]
out['latest'] = {'q': str(q.dropna(subset=['pi']).index[-1]), 'pi': float(last['pi']), 'u': float(last['u']), 'ustar': float(last['ustar']),
                 'ugap': float(last['ugap']), 'gap_lw_2026Q2': float(lw['gap'].iloc[-1]), 'rstar': float(lw['rstar'].iloc[-1])}
for k in ['lwgap', 'ugap']:
    r = out[k]; x = out['latest']['gap_lw_2026Q2'] if k == 'lwgap' else out['latest']['ugap']
    r['target_now'] = out['latest']['rstar'] + 2 + r['b_pi'] * (out['latest']['pi'] - 2) + r['b_x'] * x
# persistence of inflation and slack deviations, quarterly AR(1) on 1990-2026 (ex 2020-21)
def ar1(series):
    z = series.loc['1990Q1':'2026Q2'].drop(pd.period_range('2020Q1', '2021Q4', freq='Q'), errors='ignore').dropna()
    y, x = z.values[1:], z.values[:-1]
    X = np.column_stack([np.ones(len(x)), x]); b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(b[1])
out['ar1'] = {'pi': ar1(q['pi']), 'lwgap': ar1(q['gap']), 'ugap': ar1(q['ugap'])}
json.dump(out, open(f'{H}/rule.json', 'w'), indent=1)
for k in ['lwgap', 'ugap']:
    print(k, {kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in out[k].items() if kk != 'fit'})
print(out['latest']); print(out['ar1'])
