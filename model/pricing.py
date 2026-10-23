import sys, json, numpy as np, pandas as pd
H = sys.argv[1]
tsy = pd.read_pickle(f'{H}/tsy.pkl')
TEN = np.array([1/12, 0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30]); COLS = ['m1','m3','m6','y1','y2','y3','y5','y7','y10','y20','y30']
def interp(curve, T): return float(np.interp(T, TEN, curve))
def price(c, T, y, f=2):
    """Clean price per 100 of a bond with annual coupon c%, T years left, yield y% (semiannual)."""
    if T <= 0: return 100.0
    n = int(np.ceil(T * f - 1e-9)); acc = (n - T * f)   # fraction of period elapsed since last coupon
    i = y / 100 / f; cf = c / f
    t = np.arange(1, n + 1) - acc
    dirty = (cf * ((1 + i) ** -t)).sum() + 100 * (1 + i) ** -t[-1]
    return dirty - cf * acc
LADDERS = {'SHY': (1, 3), 'IEF': (7, 10), 'TLT': (20, 30)}
FEE = {'SGOV': 0.09, 'SHY': 0.15, 'IEF': 0.15, 'TLT': 0.15}
YTM_ISH = {'SHY': 4.78, 'IEF': 5.09, 'TLT': 5.47}  # iShares, Oct 21 2026
DUR_ISH = {'SHY': 1.79, 'IEF': 6.83, 'TLT': 14.87}
def rungs(k): a, b = LADDERS[k]; return np.linspace(a, b, int((b - a) * 12) + 1)
def ladder_yield(curve, k, s=0): return float(np.mean([interp(curve, T) + s for T in rungs(k)]))
def ladder_return(c0, c1, k, t, s):
    r = []
    for T in rungs(k):
        y0 = interp(c0, T) + s; y1 = interp(c1, max(T - t, 1/12)) + s
        r.append((price(y0, T - t, y1) - price(y0, T, y0) + y0 * t) / 100)
    return float(np.mean(r)) * 100
def ladder_duration(curve, k, s):
    d = []
    for T in rungs(k):
        y = interp(curve, T) + s; p0 = price(y, T, y); d.append((price(y, T, y - 0.01) - price(y, T, y + 0.01)) / (2 * 0.01) / p0 * 100)
    return float(np.mean(d))
c_oct21 = tsy.loc['2026-10-21', COLS].values.astype(float)
spread = {k: YTM_ISH[k] - ladder_yield(c_oct21, k) for k in LADDERS}
out = {'spread': spread, 'dur_model': {k: ladder_duration(c_oct21, k, spread[k]) for k in LADDERS}, 'dur_ishares': DUR_ISH}
# YTD validation: Jan 2 -> Oct 21, 2026
c0 = tsy.loc['2026-01-02', COLS].values.astype(float); t = (pd.Timestamp('2026-10-21') - pd.Timestamp('2026-01-02')).days / 365.25
ytd = {k: ladder_return(c0, c_oct21, k, t, spread[k]) - FEE[k] * t for k in LADDERS}
bills = tsy.loc['2026-01-02':'2026-10-21', ['m1', 'm3']].mean(axis=1).mean()
ytd['SGOV'] = (bills - 0.22) * t - FEE['SGOV'] * t   # SGOV yields ~0.22 below the 3-month par yield (Oct 22: 4.00 vs 4.22)
out['ytd_model'] = ytd; out['ytd_ishares'] = {'SGOV': 2.94, 'SHY': 0.78, 'IEF': -3.30, 'TLT': -4.80}
print(json.dumps(out, indent=1, default=lambda x: round(float(x), 3)))
json.dump(out, open(f'{H}/pricing.json', 'w'), default=float)

# ---- monthly-rebalanced constant-maturity ladders (how the funds actually behave) ----
def cm_return(curves, k, s, dt):
    """Compound monthly returns of a ladder that is reset to its maturity range every step."""
    tot = 1.0
    for c0, c1 in zip(curves[:-1], curves[1:]):
        r = []
        for T in rungs(k):
            y0 = interp(c0, T) + s; y1 = interp(c1, max(T - dt, 1/12)) + s
            r.append((price(y0, T - dt, y1) - 100 + y0 * dt) / 100)
        tot *= 1 + np.mean(r)
    return (tot - 1) * 100
for trange in [(20, 30), (22, 30), (23, 30), (24, 30)]:
    LADDERS['TLT'] = trange
    sp = YTM_ISH['TLT'] - ladder_yield(c_oct21, 'TLT')
    print('TLT', trange, 'duration', round(ladder_duration(c_oct21, 'TLT', sp), 2))
LADDERS['TLT'] = (22, 30)
spread = {k: YTM_ISH[k] - ladder_yield(c_oct21, k) for k in LADDERS}
d = tsy.loc['2026-01-02':'2026-10-21', COLS].dropna()
pts = [d.index[0]] + list(d.resample('ME').last().index[:-1]) + [d.index[-1]]
pts = [d.loc[:p].index[-1] for p in pts]
curves = [d.loc[p].values.astype(float) for p in pts]
dts = np.diff([p.toordinal() for p in pts]) / 365.25
ytd2 = {}
for k in LADDERS:
    tot = 1.0
    for i in range(len(curves) - 1):
        tot *= 1 + cm_return([curves[i], curves[i + 1]], k, spread[k], dts[i]) / 100
    ytd2[k] = (tot - 1) * 100 - FEE[k] * t
print('monthly-rebalanced YTD', {k: round(v, 2) for k, v in ytd2.items()}, 'iShares', out['ytd_ishares'])
print('durations', {k: round(ladder_duration(c_oct21, k, spread[k]), 2) for k in LADDERS})
out.update({'ladders': LADDERS, 'spread': spread, 'ytd_model_monthly': ytd2, 'dur_model': {k: ladder_duration(c_oct21, k, spread[k]) for k in LADDERS}})
json.dump(out, open(f'{H}/pricing.json', 'w'), default=float)
