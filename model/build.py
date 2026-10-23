"""Assemble page data and write index.html from template.html."""
import sys, json, numpy as np
H, SCR, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
de = json.load(open(f'{H}/data_engine.json')); est = json.load(open(f'{H}/estimates.json'))
r2 = json.load(open(f'{H}/rule2.json'))['du4']; pr = json.load(open(f'{H}/pricing.json'))
M = np.array(de['M'])
D = {k: de[k] for k in ['P', 'TEN', 'TODAY', 'M', 'ROLL', 'tp', 'rn', 'fwd', 'rs_resp', 'FUNDS', 'SG']}
D['SC'] = [{k: s[k] for k in ['id', 'name', 'kind', 'macro', 'analog_surp']} for s in de['SC']]
D['analogs'] = de['analogs']
D['backtest'] = de['backtest']
D['rule'] = {'rho': r2['rho'], 'b': r2['b'], 'se': r2['se'], 'r2': r2['r2'], 'sd': r2['sd'], 'dyn4': r2['dyn4'], 'n': r2['n'],
             'fit': r2['fit'], 'episodes': {k: r2['episodes'][k] for k in ['1994Q1', '1999Q2', '2000Q4', '2007Q3', '2018Q4', '2023Q3']}}
D['paths'] = {'market': [round(x, 2) for x in de['fwd'][:3]], 'rule': [4.24, 4.47, 4.50], 'sep': [4.10, 4.03, 3.80]}
D['tp_par'] = {'2': round(4.65 - M[:8].mean(), 2), '10': round(4.96 - M[:40].mean(), 2), '30': round(5.29 - M[:120].mean(), 2)}
D['ytd'] = {'model': dict(pr['ytd_model_monthly'], SGOV=2.89), 'actual': pr['ytd_ishares']}
D['trans'] = est['transmission']; D['dist12'] = est['dist12']; D['dist12_n'] = est['dist12_n']; D['cycles'] = est['hike_cycles']
tpl = open(f'{SCR}/template.html').read()
eng = open(f'{SCR}/scripts/engine.js').read()
html = tpl.replace('__DATA__', json.dumps(D, separators=(',', ':'), default=float)).replace('__ENGINE__', eng)
open(OUT, 'w').write(html)
print('wrote', OUT, len(html))
