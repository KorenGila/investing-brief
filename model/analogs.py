"""Episode surprises vs the ACM forward curve at the start of each episode. Writes analogs.json."""
import sys, json, numpy as np, pandas as pd
H = sys.argv[1]
acm = pd.read_pickle(f'{H}/acm.pkl'); est = json.load(open(f'{H}/estimates.json'))
def state(date):
    row = acm.loc[:date].dropna(subset=['ACMRNY10']).iloc[-1]
    rn = np.array([row[f'ACMRNY{n:02d}'] for n in range(1, 11)])
    fwd = np.array([rn[0]] + [(n + 1) * rn[n] - n * rn[n - 1] for n in range(1, 10)])
    return np.array([fwd[min(q // 4, 9)] for q in range(128)])
rows = []
for e in est['episodes']:
    m = state(e['start']); h = int(round(4 * (pd.Timestamp(e['end']) - pd.Timestamp(e['start'])).days / 365.25))
    roll = {n: m[h:h + 4 * n].mean() - m[:4 * n].mean() for n in [2, 10, 30]}
    rows.append({'kind': e['kind'], 'name': e['name'], 's_ff': round(e['d_ff'] - (m[h] - m[0]), 2), 's_y2': round(e['d_y2'] - roll[2], 2),
                 's_y10': round(e['d_y10'] - roll[10], 2), 's_y30': round(e['d_y30'] - roll[30], 2), 'roll_y2': round(roll[2], 2),
                 'd_tp10': e['d_tp10'], 'd_corepce': e['d_corepce'], 'd_unemp': e['d_unemp'], 'd_rstar': e['d_rstar']})
avg = {}
for k in ['soft', 'hike', 'bust', 'boom', 'tp']:
    g = [r for r in rows if r['kind'] == k and 'Covid' not in r['name']]
    avg[k] = {c: round(float(np.mean([r[c] for r in g])), 2) for c in ['s_ff', 's_y2', 's_y10', 's_y30', 'd_tp10', 'd_corepce', 'd_unemp', 'd_rstar']}
    avg[k]['n'] = len(g); avg[k]['names'] = [r['name'] for r in g]
json.dump({'rows': rows, 'avg': avg}, open(f'{H}/analogs.json', 'w')); print(json.dumps(avg, indent=1))
