"""12-month forecast misses at each fund's maturity, every month-end since 1990.
miss_k(t) = y_k(t+12m) - y_k(t) - forecast change_k(t), with the forecast from ACM's expected short-rate path at t.
Also: loadings for the two view knobs, all measured from the same data."""
import sys, json, numpy as np, pandas as pd
H = sys.argv[1]
tsy = pd.read_pickle(f'{H}/tsy.pkl'); acm = pd.read_pickle(f'{H}/acm.pkl')
TEN = np.array([1/12, 0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30])
COLS = ['m1', 'm3', 'm6', 'y1', 'y2', 'y3', 'y5', 'y7', 'y10', 'y20', 'y30']
WAM = {'SGOV': 0.12, 'SHY': 1.89, 'IEF': 8.41, 'TLT': 26.03}
m = tsy.resample('ME').last()[COLS]; a = acm.resample('ME').last()

def yld(row, T):
    ok = ~np.isnan(row.values.astype(float))
    return float(np.interp(T, TEN[ok], row.values.astype(float)[ok]))   # flat beyond the last available maturity
def path(t):
    r = a.loc[t]; rn = [r[f'ACMRNY{n:02d}'] for n in range(1, 11)]
    fwd = [rn[0]] + [(n + 1) * rn[n] - n * rn[n - 1] for n in range(1, 10)]
    return np.array([fwd[min(q // 4, 9)] for q in range(4 * 32)])
def fc_change(M, T):
    N = max(1, int(round(4 * T))); return float(M[4:4 + N].mean() - M[0:N].mean())

rows = []
for t in m.index:
    t1 = t + pd.offsets.MonthEnd(12)
    if t < pd.Timestamp('1990-01-31') or t1 not in m.index: continue
    M = path(t); r = {'t': str(t.date())}
    for k, T in WAM.items():
        r[k] = yld(m.loc[t1], T) - yld(m.loc[t], T) - fc_change(M, T)
    r['y2'] = yld(m.loc[t1], 2) - yld(m.loc[t], 2) - fc_change(M, 2)
    r['dtp10'] = float(a.loc[t1, 'ACMTP10'] - a.loc[t, 'ACMTP10'])
    rows.append(r)
df = pd.DataFrame(rows).set_index('t')
raw_mean = df.mean()
dm = df - raw_mean                       # centered on zero: keep the spread, drop the 1990-2020 downward drift
print('windows', len(df), df.index[0], df.index[-1])
print('raw mean miss', raw_mean.round(2).to_dict())
pct = [5, 10, 25, 50, 75, 90, 95]
dist = {c: dict(zip(map(str, pct), np.percentile(dm[c], pct).round(2).tolist())) for c in ['y2', 'SHY', 'IEF', 'TLT', 'SGOV', 'dtp10']}
print('centered percentiles', dist)

# knob 1: shift in the Fed path, expressed as a 2-year miss; each fund moves by its historical slope on the 2-year miss
def slope(y, x): x = x - x.mean(); y = y - y.mean(); return float((x * y).sum() / (x * x).sum())
beta_fed = {k: round(slope(dm[k].values, dm['y2'].values), 2) for k in WAM}
# knob 2: change in the 10-year term premium; loadings from ACM (term premium by maturity on the 10-year), 12-month changes
ad = (a - a.shift(12)).dropna(subset=['ACMTP10']).loc['1990':]
tp_load = {n: slope(ad[f'ACMTP{n:02d}'].values, ad['ACMTP10'].values) for n in range(1, 11)}
def load_at(T):
    if T >= 10: return 0.89     # 30-year yield on the 10-year term premium, expected path held fixed (1990-2026 regression)
    if T < 1: return tp_load[1] * T
    return float(np.interp(T, range(1, 11), [tp_load[n] for n in range(1, 11)]))
beta_tp = {k: round(load_at(T), 2) for k, T in WAM.items()}
corr = dm[['SGOV', 'SHY', 'IEF', 'TLT']].corr().round(2)
print('beta_fed', beta_fed, 'beta_tp', beta_tp); print(corr)
# forecast change in each fund's yield over the next 12 months, from today's ACM path
M0 = path(a.index[-1]); F = {k: round(fc_change(M0, T), 3) for k, T in WAM.items()}
print('acm date', a.index[-1].date(), 'forecast change', F)
json.dump({'draws': dm[['SGOV', 'SHY', 'IEF', 'TLT']].round(4).values.tolist(), 'dates': list(dm.index),
           'raw_mean': raw_mean.round(3).to_dict(), 'dist': dist, 'beta_fed': beta_fed, 'beta_tp': beta_tp,
           'corr': corr.to_dict(), 'F': F, 'n': len(df)}, open(f'{H}/misses.json', 'w'))
