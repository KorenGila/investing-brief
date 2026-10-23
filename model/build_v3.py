"""Page build: market forecast as the center, historical 12-month forecast misses (centered) as the spread, two view knobs."""
import sys, json, numpy as np, pandas as pd
H, TPL, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
est = json.load(open(f'{H}/estimates.json')); ms = json.load(open(f'{H}/misses.json'))
tsy = pd.read_pickle(f'{H}/tsy.pkl')
TEN = [1/12, 0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30]; COLS = ['m1', 'm3', 'm6', 'y1', 'y2', 'y3', 'y5', 'y7', 'y10', 'y20', 'y30']
TODAY = [float(x) for x in tsy.loc['2026-10-22', COLS].values]
rn = est['acm_today']['rn']; fwd = [rn[0]] + [(n + 1) * rn[n] - n * rn[n - 1] for n in range(1, 10)]
M = np.array([fwd[min(q // 4, 9)] for q in range(128)])
TP = {'2': round(TODAY[4] - M[:8].mean(), 2), '10': round(TODAY[8] - M[:40].mean(), 2), '30': round(TODAY[10] - M[:120].mean(), 2)}
FUNDS = {'SGOV': dict(ytm=4.00, dur=0.12, cvx=0.00, wam=0.12, fee=0.09),
         'SHY': dict(ytm=4.64, dur=1.79, cvx=0.04, wam=1.89, fee=0.15),
         'IEF': dict(ytm=4.93, dur=6.84, cvx=0.56, wam=8.41, fee=0.15),
         'TLT': dict(ytm=5.35, dur=14.96, cvx=3.16, wam=26.03, fee=0.15)}
def ret(f, y0, dy, t=1.0): return ((2 * y0 + dy) / 2 - f['fee']) * t - f['dur'] * dy + 0.5 * f['cvx'] * dy ** 2
c0 = tsy.loc['2026-01-02', COLS].values.astype(float); c1 = tsy.loc['2026-10-21', COLS].values.astype(float)
t = (pd.Timestamp('2026-10-21') - pd.Timestamp('2026-01-02')).days / 365.25
ACT = {'SGOV': 2.94, 'SHY': 0.78, 'IEF': -3.30, 'TLT': -4.80}
check = {k: {'dy': round(float(np.interp(f['wam'], TEN, c1) - np.interp(f['wam'], TEN, c0)), 2),
             'model': round(ret(f, float(np.interp(f['wam'], TEN, c0)), float(np.interp(f['wam'], TEN, c1) - np.interp(f['wam'], TEN, c0)), t), 2),
             'actual': ACT[k]} for k, f in FUNDS.items()}
an = json.load(open(f'{H}/analogs.json'))
ref = {r['name']: {'y2': r['s_y2'], 'tp': r['d_tp10']} for r in an['rows']}
D = {'TODAY': TODAY, 'fwd': fwd[:3], 'tp': TP, 'sep': [4.10, 4.03, 3.80], 'FUNDS': FUNDS, 'F': ms['F'], 'check': check,
     'draws': ms['draws'], 'dates': ms['dates'], 'raw_mean': ms['raw_mean'], 'dist': ms['dist'], 'beta_fed': ms['beta_fed'],
     'beta_tp': ms['beta_tp'], 'corr': ms['corr'], 'n': ms['n'], 'cycles': est['hike_cycles'], 'ref': ref}
html = open(TPL).read().replace('__DATA__', json.dumps(D, separators=(',', ':')))
open(OUT, 'w').write(html); print('wrote', OUT, len(html)); print('check', check)
