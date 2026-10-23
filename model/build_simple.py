"""Simple model: market forecast (ACM) + historical-analog surprises + one-line return formula.
Writes the page from template_simple.html."""
import sys, json, numpy as np, pandas as pd
H, TPL, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
est = json.load(open(f'{H}/estimates.json')); an = json.load(open(f'{H}/analogs.json'))
tsy = pd.read_pickle(f'{H}/tsy.pkl')
TEN = [1/12, 0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30]
COLS = ['m1', 'm3', 'm6', 'y1', 'y2', 'y3', 'y5', 'y7', 'y10', 'y20', 'y30']
TODAY = [float(x) for x in tsy.loc['2026-10-22', COLS].values]
# market forecast: ACM expected short rate, 1-year forwards, flat after 10 years
rn = est['acm_today']['rn']
fwd = [rn[0]] + [(n + 1) * rn[n] - n * rn[n - 1] for n in range(1, 10)]
M = np.array([fwd[min(q // 4, 9)] for q in range(4 * 32)])
nq = lambda n: max(1, int(round(4 * n)))
ROLL = [float(M[4:4 + nq(n)].mean() - M[0:nq(n)].mean()) for n in TEN]   # forecast change in each yield over 12 months
TP = {'2': round(TODAY[4] - M[:8].mean(), 2), '10': round(TODAY[8] - M[:40].mean(), 2), '30': round(TODAY[10] - M[:120].mean(), 2)}
# funds: all inputs as published by iShares for Oct 22, 2026
FUNDS = {'SGOV': dict(ytm=4.00, dur=0.12, cvx=0.00, wam=0.12, fee=0.09, nav=100.64),
         'SHY': dict(ytm=4.64, dur=1.79, cvx=0.04, wam=1.89, fee=0.15, nav=81.50),
         'IEF': dict(ytm=4.93, dur=6.84, cvx=0.56, wam=8.41, fee=0.15, nav=91.18),
         'TLT': dict(ytm=5.35, dur=14.96, cvx=3.16, wam=26.03, fee=0.15, nav=81.71)}
def ret(f, y0, dy, t=1.0):
    return ((y0 + y0 + dy) / 2 - f['fee']) * t - f['dur'] * dy + 0.5 * f['cvx'] * dy ** 2
# check: actual 2026 curves, Jan 2 -> Oct 21
c0 = tsy.loc['2026-01-02', COLS].values.astype(float); c1 = tsy.loc['2026-10-21', COLS].values.astype(float)
t = (pd.Timestamp('2026-10-21') - pd.Timestamp('2026-01-02')).days / 365.25
ACT = {'SGOV': 2.94, 'SHY': 0.78, 'IEF': -3.30, 'TLT': -4.80}
check = {}
for k, f in FUNDS.items():
    y0 = float(np.interp(f['wam'], TEN, c0)); y1 = float(np.interp(f['wam'], TEN, c1))
    check[k] = {'y0': round(y0, 2), 'y1': round(y1, 2), 'model': round(ret(f, y0, y1 - y0, t), 2), 'actual': ACT[k]}
print('check', check)
# episodes with dates
eps = []
for e, r in zip([e for e in est['episodes']], an['rows']):
    assert e['name'] == r['name']
    eps.append({'kind': r['kind'], 'name': r['name'], 'start': e['start'], 'end': e['end'],
                's_ff': r['s_ff'], 's_y2': r['s_y2'], 's_y10': r['s_y10'], 's_y30': r['s_y30']})
D = {'TEN': TEN, 'TODAY': TODAY, 'ROLL': ROLL, 'fwd': fwd[:3], 'tp': TP, 'sep': [4.10, 4.03, 3.80], 'FUNDS': FUNDS,
     'check': check, 'episodes': eps, 'cycles': est['hike_cycles'], 'dist12': est['dist12'], 'dist12_n': est['dist12_n']}
html = open(TPL).read().replace('__DATA__', json.dumps(D, separators=(',', ':')))
open(OUT, 'w').write(html); print('wrote', OUT, len(html))
