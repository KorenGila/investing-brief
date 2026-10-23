"""Reference engine, both methods. Writes data.json for the page and ref.json for checking the JS port."""
import sys, json, numpy as np, pandas as pd
H = sys.argv[1]
est = json.load(open(f'{H}/estimates.json')); rule = json.load(open(f'{H}/rule2.json'))['du4']
an = json.load(open(f'{H}/analogs.json')); eng2 = json.load(open(f'{H}/engine2.json'))['decay_from_H']
pricing = json.load(open(f'{H}/pricing.json'))
P = dict(rho=rule['rho'], bpi=rule['b'][0], bdu=rule['b'][1], kd=0.13, l30=0.89, nq=128)
TEN = [1/12, 0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30]
TODAY = [4.11, 4.22, 4.29, 4.41, 4.65, 4.72, 4.78, 4.86, 4.96, 5.32, 5.29]
rn = est['acm_today']['rn']; tp = est['acm_today']['tp']
fwd = [rn[0]] + [(n + 1) * rn[n] - n * rn[n - 1] for n in range(1, 10)]
M = np.array([fwd[min(q // 4, 9)] for q in range(P['nq'])])
FUNDS = {'SHY': dict(lo=1.0, hi=2.8, cpn=None, fee=0.15, ytm=4.63), 'IEF': dict(lo=7, hi=10, cpn=None, fee=0.15, ytm=4.92),
         'TLT': dict(lo=20, hi=30, cpn=3.5, fee=0.15, ytm=5.33)}
SG = dict(fee=0.09, basis=-0.10)
def interp(c, T): return float(np.interp(T, TEN, c))
def price(c, T, y):
    if T <= 1e-9: return 100.0
    n = int(np.ceil(T * 2 - 1e-9)); acc = n - T * 2; i = y / 200; cf = c / 2
    t = np.arange(1, n + 1) - acc
    return float((cf * (1 + i) ** -t).sum() + 100 * (1 + i) ** -t[-1] - cf * acc)
def rungs(f): return np.linspace(f['lo'], f['hi'], int(round((f['hi'] - f['lo']) * 12)) + 1)
for f in FUNDS.values(): f['spread'] = f['ytm'] - float(np.mean([interp(TODAY, T) for T in rungs(f)]))
def nq(n): return max(1, int(round(4 * n)))
ROLL = [float(M[4:4 + nq(n)].mean() - M[0:nq(n)].mean()) for n in TEN]
def tp_load(n):
    if n >= 10: return 1.0 if n == 10 else P['l30']
    if n < 1: return tp[0] / tp[9] * n
    i = int(np.floor(n)); fr = n - i; lo = tp[i - 1] / tp[9]; hi = tp[min(i, 9)] / tp[9]
    return lo + fr * (hi - lo)
def fed_dev(dpi, du, drs):
    d = np.zeros(P['nq'])
    for t in range(1, 5):
        r = t / 4.0
        d[t] = P['rho'] * d[t - 1] + (1 - P['rho']) * (drs * r + P['bpi'] * dpi * r + P['bdu'] * du * r)
    D = d[4]
    for t in range(5, P['nq']): d[t] = drs + (D - drs) * np.exp(-P['kd'] * (t - 4) / 4)
    return d
def model_surprise(dpi, du, drs, dtp):
    d = fed_dev(dpi, du, drs)
    return [float(d[4:4 + nq(n)].mean() + dtp * tp_load(n)) for n in TEN], float(d[4]), d
def analog_surprise(sff, s2, s10, s30):
    out = []
    for n in TEN:
        if n <= 0.5: v = sff
        elif n == 1: v = (sff + s2) / 2
        elif n <= 2: v = s2
        elif n <= 10: v = s2 + (s10 - s2) * (n - 2) / 8
        else: v = s10 + (s30 - s10) * (n - 10) / 20
        out.append(v)
    return out
def returns(surp):
    dy = np.array(ROLL) + np.array(surp)
    curves = [np.array(TODAY) + dy * i / 12 for i in range(13)]
    res = {}
    inc = np.mean([(interp((curves[i] + curves[i + 1]) / 2, 1/12) + interp((curves[i] + curves[i + 1]) / 2, 0.25)) / 2 for i in range(12)])
    res['SGOV'] = inc + SG['basis'] - SG['fee']
    for k, f in FUNDS.items():
        tot = 1.0
        for i in range(12):
            r = []
            for T in rungs(f):
                y0 = interp(curves[i], T) + f['spread']; y1 = interp(curves[i + 1], max(T - 1/12, 1/12)) + f['spread']
                cp = f['cpn'] if f['cpn'] is not None else y0
                p0 = price(cp, T, y0); r.append((price(cp, T - 1/12, y1) - p0 + cp / 12) / p0)
            tot *= 1 + np.mean(r)
        res[k] = (tot - 1) * 100 - f['fee']
    return {k: round(v, 3) for k, v in res.items()}, dy.tolist()

A = an['avg']
# pure neutral-rate response from the structural model (used to extend the 1990s analog to a bigger AI boom)
rs_resp, _, _ = model_surprise(0, 0, 1.0, 0)
SC = [
 dict(id='cools', name='Inflation cools, Fed stops', kind='soft', macro=dict(dpi=A['soft']['d_corepce'], du=A['soft']['d_unemp'], drs=0.0, dtp=A['soft']['d_tp10'])),
 dict(id='market', name="The market's path", kind=None, macro=dict(dpi=0, du=0, drs=0, dtp=0)),
 dict(id='reheats', name='Economy reheats, Fed keeps hiking', kind='hike', macro=dict(dpi=A['hike']['d_corepce'], du=A['hike']['d_unemp'], drs=0.0, dtp=A['hike']['d_tp10'])),
 dict(id='bust', name='AI bust, recession', kind='bust', macro=dict(dpi=A['bust']['d_corepce'], du=A['bust']['d_unemp'], drs=A['bust']['d_rstar'], dtp=A['bust']['d_tp10'])),
 dict(id='boom', name='AI boom, trend growth +1 point', kind='boom', macro=dict(dpi=A['boom']['d_corepce'], du=A['boom']['d_unemp'], drs=1.07, dtp=A['boom']['d_tp10'])),
 dict(id='tp', name='Term premium shock', kind='tp', macro=dict(dpi=0, du=0, drs=0, dtp=A['tp']['d_tp10'])),
]
ref = {}
for s in SC:
    ms, ffH, d = model_surprise(**s['macro'])
    if s['kind']:
        a = A[s['kind']]; asurp = analog_surprise(a['s_ff'], a['s_y2'], a['s_y10'], a['s_y30'])
        if s['id'] == 'boom':  # extend the 1990s analog: extra neutral-rate shift beyond the 1990s' +0.31
            extra = s['macro']['drs'] - a['d_rstar']
            asurp = [v + extra * w for v, w in zip(asurp, rs_resp)]
        eps = [r for r in an['rows'] if r['kind'] == s['kind'] and 'Covid' not in r['name']]
        ep_ret = []
        for r in eps:
            es = analog_surprise(r['s_ff'], r['s_y2'], r['s_y10'], r['s_y30'])
            if s['id'] == 'boom': es = [v + (s['macro']['drs'] - a['d_rstar']) * w for v, w in zip(es, rs_resp)]
            ep_ret.append({'name': r['name'], 'ret': returns(es)[0]})
    else:
        asurp = [0.0] * len(TEN); ep_ret = []
    ra, dya = returns(asurp); rm, dym = returns(ms)
    s.update(analog_surp=asurp, model_surp=ms, ret_analog=ra, ret_model=rm, dy_analog=dya, dy_model=dym, ep_ret=ep_ret,
             fed_years_model=[round(float((M + d)[4 * y:4 * y + 4].mean()), 2) for y in range(4)])
    ref[s['id']] = {'ret_analog': ra, 'ret_model': rm}
    print(s['id'], 'analog', ra, 'model', rm, 'dy2/10/30 analog', [round(dya[i], 2) for i in (4, 8, 10)], 'model', [round(dym[i], 2) for i in (4, 8, 10)])
    for e in ep_ret: print('     ', e)
json.dump(ref, open(f'{H}/ref.json', 'w'))
json.dump({'P': P, 'TEN': TEN, 'TODAY': TODAY, 'M': M.tolist(), 'ROLL': ROLL, 'tp': tp, 'rn': rn, 'fwd': fwd, 'rs_resp': rs_resp,
           'FUNDS': FUNDS, 'SG': SG, 'SC': SC, 'analogs': an, 'backtest': eng2, 'pricing': pricing}, open(f'{H}/data_engine.json', 'w'), default=float)
