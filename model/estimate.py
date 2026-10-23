"""Estimate the Fed reaction function, curve transmission, episode moves and base rates."""
import sys, json
import numpy as np, pandas as pd

H = sys.argv[1]
tsy = pd.read_pickle(f'{H}/tsy.pkl'); acm = pd.read_pickle(f'{H}/acm.pkl')
ff = pd.read_pickle(f'{H}/ff.pkl'); pce = pd.read_pickle(f'{H}/pce.pkl')
un = pd.read_pickle(f'{H}/un.pkl'); lw = pd.read_pickle(f'{H}/lw.pkl')
out = {}

def ols(y, X, names):
    X = np.column_stack([np.ones(len(y))] + X)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    n, k = X.shape
    s2 = e @ e / (n - k)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    return dict(zip(['const'] + names, b)), dict(zip(['const'] + names, se)), r2, n, np.sqrt(s2)

# ---------- 1. Reaction function (quarterly) ----------
core_yoy = (pce['core'] / pce['core'].shift(12) - 1) * 100
q = pd.DataFrame({'ff': ff.groupby(ff.index.asfreq('Q')).mean(),
                  'pi': core_yoy.groupby(core_yoy.index.asfreq('Q')).mean()}).join(lw[['gap', 'rstar']])
q['ff_l'] = q['ff'].shift(1)
s = q.loc['1988Q1':'2026Q2'].dropna()
s = s[(s['ff'] > 0.5) & (s['ff_l'] > 0.5)]  # drop zero-lower-bound quarters
b, se, r2, n, sig = ols(s['ff'].values, [s['ff_l'].values, s['pi'].values, s['gap'].values], ['rho', 'b_pi', 'b_gap'])
rho = b['rho']
rf = {'rho': rho, 'beta_pi': b['b_pi'] / (1 - rho), 'gamma_gap': b['b_gap'] / (1 - rho), 'const_lr': b['const'] / (1 - rho),
      'se_rho': se['rho'], 'se_bpi': se['b_pi'], 'se_bgap': se['b_gap'], 'r2': r2, 'n': n, 'resid_sd': sig,
      'sample': f"{s.index.min()}-{s.index.max()}, ZLB quarters excluded"}
# implied neutral nominal rate at pi=2, gap=0
rf['neutral_implied'] = rf['const_lr'] + 2 * rf['beta_pi']
out['reaction'] = rf
fit = (b['const'] + rho * s['ff_l'] + b['b_pi'] * s['pi'] + b['b_gap'] * s['gap'])
out['reaction_fit'] = [[str(i), round(a, 2), round(f, 2)] for i, a, f in zip(s.index, s['ff'], fit)]
# today's prescription
pi_now = float(core_yoy.dropna().iloc[-1]); gap_now = float(lw['gap'].iloc[-1]); rstar_now = float(lw['rstar'].iloc[-1])
out['now'] = {'core_pce_yoy': pi_now, 'core_pce_month': str(core_yoy.dropna().index[-1]), 'gap': gap_now, 'lw_rstar': rstar_now,
              'lw_g': float(lw['g'].iloc[-1]), 'ff': 3.88}
out['now']['rule_target'] = rf['const_lr'] + rf['beta_pi'] * pi_now + rf['gamma_gap'] * gap_now
# classic Taylor (1993) with LW r*
out['now']['taylor1993'] = rstar_now + pi_now + 0.5 * (pi_now - 2) + 0.5 * gap_now

# ---------- 2. Curve transmission, 12-month changes, month-end sampling ----------
m = tsy.resample('ME').last()
m['y30x'] = m['y30'].fillna(m['y20'])  # 30-year missing 2002-2006
a = acm.resample('ME').last()
m = m.join(a[['ACMTP02', 'ACMTP10', 'ACMRNY02', 'ACMRNY10']])
d12 = (m - m.shift(12)).dropna(subset=['y2', 'y10', 'y30x', 'ACMTP10'])
res = {}
for ylab in ['y10', 'y30x']:
    bb, ss, rr, nn, sg = ols(d12[ylab].values, [d12['y2'].values], ['dy2'])
    res[ylab + '_on_y2'] = {'beta': bb['dy2'], 'se_naive': ss['dy2'], 'r2': rr, 'n': nn, 'resid_sd': sg}
bb, ss, rr, nn, sg = ols(d12['ACMRNY10'].values, [d12['ACMRNY02'].values], ['drn2'])
res['rn10_on_rn2'] = {'beta': bb['drn2'], 'r2': rr, 'n': nn}
bb, ss, rr, nn, sg = ols(d12['y30x'].values, [d12['ACMRNY10'].values, d12['ACMTP10'].values], ['drn10', 'dtp10'])
res['y30_on_rn10_tp10'] = {'b_rn10': bb['drn10'], 'b_tp10': bb['dtp10'], 'r2': rr, 'n': nn}
bb, ss, rr, nn, sg = ols(d12['ACMTP02'].values, [d12['ACMTP10'].values], ['dtp10'])
res['tp2_on_tp10'] = {'beta': bb['dtp10'], 'r2': rr}
out['transmission'] = res
# distributions of 12-month changes since 1990
pct = [5, 10, 25, 50, 75, 90, 95]
out['dist12'] = {k: dict(zip(map(str, pct), np.percentile(d12[k].values, pct).round(2).tolist()))
                 for k in ['y2', 'y10', 'y30x', 'ACMTP10']}
out['dist12_n'] = int(len(d12))

# ---------- 3. Episodes: 12-month changes ----------
def at(df, dt, col):
    return float(df[col].loc[:dt].dropna().iloc[-1])
EP = [
 ('soft', 'Fed stops: 1995', '1995-02-01', '1996-02-01'),
 ('soft', 'Fed stops: 2006-07', '2006-06-29', '2007-06-29'),
 ('soft', 'Fed stops: 2019', '2018-12-19', '2019-12-19'),
 ('soft', 'Fed stops: 2023-24', '2023-07-26', '2024-07-26'),
 ('hike', 'Inflation keeps Fed hiking: 1994', '1994-02-04', '1995-02-03'),
 ('hike', 'Inflation keeps Fed hiking: 2022', '2022-03-16', '2023-03-16'),
 ('hike', 'Hiking resumes: 2004-05', '2004-06-30', '2005-06-30'),
 ('bust', 'Dot-com bust: 2000-01', '2000-12-01', '2001-12-01'),
 ('bust', 'Financial crisis: 2007-08', '2007-08-01', '2008-08-01'),
 ('bust', 'Covid: 2020', '2020-01-02', '2021-01-04'),
 ('boom', 'Productivity boom: 1999', '1998-12-31', '1999-12-31'),
 ('boom', 'Productivity boom: 1996-97', '1996-01-02', '1997-01-02'),
 ('tp', 'Term premium jump: 2023 (May-Oct, 5 months)', '2023-05-19', '2023-10-19'),
 ('tp', 'Taper tantrum: 2013 (May-Sep, 4 months)', '2013-05-02', '2013-09-05'),
]
eps = []
for kind, name, a0, a1 in EP:
    r = {'kind': kind, 'name': name, 'start': a0, 'end': a1}
    for c in ['m3', 'y2', 'y10']:
        r['d_' + c] = at(tsy, a1, c) - at(tsy, a0, c)
    y30a = tsy['y30'].loc[:a0].dropna(); y30b = tsy['y30'].loc[:a1].dropna()
    use = 'y30' if (pd.Timestamp(a0) - y30a.index[-1]).days < 10 and (pd.Timestamp(a1) - y30b.index[-1]).days < 10 else 'y20'
    r['d_y30'] = at(tsy, a1, use) - at(tsy, a0, use); r['y30_proxy'] = use
    r['d_tp10'] = at(acm, a1, 'ACMTP10') - at(acm, a0, 'ACMTP10')
    r['d_rn10'] = at(acm, a1, 'ACMRNY10') - at(acm, a0, 'ACMRNY10')
    p0, p1 = pd.Period(a0, 'M'), pd.Period(a1, 'M')
    r['d_ff'] = float(ff.loc[:p1].iloc[-1] - ff.loc[:p0].iloc[-1])
    r['d_corepce'] = float(core_yoy.loc[:p1].dropna().iloc[-1] - core_yoy.loc[:p0].dropna().iloc[-1])
    r['d_unemp'] = float(un.loc[:p1].iloc[-1] - un.loc[:p0].iloc[-1])
    q0, q1 = pd.Period(a0, 'Q'), pd.Period(a1, 'Q')
    r['d_gap'] = float(lw['gap'].loc[:q1].iloc[-1] - lw['gap'].loc[:q0].iloc[-1])
    r['d_rstar'] = float(lw['rstar'].loc[:q1].iloc[-1] - lw['rstar'].loc[:q0].iloc[-1])
    eps.append({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
out['episodes'] = eps

# ---------- 4. Base rates: hiking cycles ----------
ffm = ff.loc['1983-01':]
cycles = []
# first hike = month where ff rises >=0.2 vs 3 months earlier after at least 6 months of no rise
starts = ['1988-03', '1994-02', '1999-06', '2004-06', '2015-12', '2022-03']
for st in starts:
    p = pd.Period(st, 'M'); base = float(ffm.loc[p - 1])
    win = ffm.loc[p:p + 36]
    peak = float(win.max()); pk = win.idxmax()
    cycles.append({'start': st, 'ff_before': round(base, 2), 'peak': round(peak, 2), 'peak_month': str(pk),
                   'total_rise': round(peak - base, 2), 'rise_after_first_25': round(peak - base - 0.25, 2),
                   'months_to_peak': int((pk - p).n)})
out['hike_cycles'] = cycles

# ---------- 5. Today's market-expected path from ACM risk-neutral yields ----------
last = acm.dropna(subset=['ACMRNY10']).iloc[-1]
rn = [float(last[f'ACMRNY{n:02d}']) for n in range(1, 11)]
tp = [float(last[f'ACMTP{n:02d}']) for n in range(1, 11)]
fwd = [rn[0]] + [(n + 1) * rn[n] - n * rn[n - 1] for n in range(1, 10)]  # 1-year forwards, year n to n+1
out['acm_today'] = {'date': str(acm.dropna(subset=['ACMRNY10']).index[-1].date()), 'rn': rn, 'tp': tp,
                    'fwd1y': fwd, 'y': [float(last[f'ACMY{n:02d}']) for n in range(1, 11)]}

json.dump(out, open(f'{H}/estimates.json', 'w'), indent=1, default=float)
print(json.dumps({k: out[k] for k in ['reaction', 'now', 'transmission', 'dist12', 'hike_cycles', 'acm_today']}, indent=1, default=lambda x: round(float(x), 3))[:6000])
print('episodes')
for e in eps: print(e)
