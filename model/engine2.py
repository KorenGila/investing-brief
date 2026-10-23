"""Engine v2: rule for the first year (and optionally momentum), then expected deviations decay at k per year
toward the permanent neutral-rate shift. k = 0.13 matches ACM's 10y/2y expectations pass-through (0.63)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, sys.argv[2])
H = sys.argv[1]
import importlib.util
spec = importlib.util.spec_from_file_location('eng', sys.argv[2] + '/engine_core.py'); eng = importlib.util.module_from_spec(spec); spec.loader.exec_module(eng)
est = json.load(open(f'{H}/estimates.json'))
res = {}
for variant in ['decay_from_H', 'momentum_8q']:
    eng.VARIANT = variant
    bt = []
    for e in est['episodes']:
        if e['kind'] == 'tp': continue
        m, tp = eng.acm_state(e['start'])
        d = eng.fed_path(e['d_corepce'], e['d_unemp'], e['d_rstar'])
        ch = eng.curve_change(m, tp, d, e['d_tp10'], [2, 10, 30])
        bt.append({'name': e['name'], 'pred_ff': round(float(m[4] + d[4] - m[0]), 2), 'act_ff': e['d_ff'],
                   'pred_y2': round(ch[2], 2), 'act_y2': e['d_y2'], 'pred_y10': round(ch[10], 2), 'act_y10': e['d_y10'],
                   'pred_y30': round(ch[30], 2), 'act_y30': e['d_y30']})
    K = ['ff', 'y2', 'y10', 'y30']
    rm = {k: round(float(np.sqrt(np.mean([(r['pred_' + k] - r['act_' + k]) ** 2 for r in bt]))), 2) for k in K}
    nv = {k: round(float(np.sqrt(np.mean([r['act_' + k] ** 2 for r in bt]))), 2) for k in K}
    co = {k: round(float(np.corrcoef([r['pred_' + k] for r in bt], [r['act_' + k] for r in bt])[0, 1]), 2) for k in K}
    m0, tp0 = eng.acm_state('2026-10-22')
    c = eng.curve_change(m0, tp0, eng.fed_path(0.5, 0, 0), 0, [2, 10, 30]); r0 = eng.curve_change(m0, tp0, np.zeros(eng.NQ), 0, [2, 10, 30])
    ratio = (round((c[10] - r0[10]) / (c[2] - r0[2]), 2), round((c[30] - r0[30]) / (c[2] - r0[2]), 2))
    print(variant, 'RMSE', rm, 'no-change', nv, 'corr', co, 'shock ratios', ratio)
    res[variant] = {'backtest': bt, 'rmse': rm, 'rmse_nochange': nv, 'corr': co, 'ratio_10_2_30_2': ratio}
json.dump(res, open(f'{H}/engine2.json', 'w'))
for r in res['decay_from_H']['backtest']: print(r)
