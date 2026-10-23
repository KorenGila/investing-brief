"""Load and clean all raw data into pickles for analysis."""
import re, glob, json, sys
import pandas as pd, numpy as np

H = sys.argv[1]  # hist dir

# Treasury par curve, daily
K = {'BC_1MONTH':'m1','BC_3MONTH':'m3','BC_6MONTH':'m6','BC_1YEAR':'y1','BC_2YEAR':'y2','BC_3YEAR':'y3',
     'BC_5YEAR':'y5','BC_7YEAR':'y7','BC_10YEAR':'y10','BC_20YEAR':'y20','BC_30YEAR':'y30'}
rows = []
for f in sorted(glob.glob(f'{H}/tsy_*.xml')):
    s = open(f).read()
    for e in s.split('<m:properties>')[1:]:
        d = re.search(r'NEW_DATE[^>]*>([^<]+)', e).group(1)[:10]
        r = {'date': d}
        for k, v in K.items():
            m = re.search(rf'<d:{k}(?: [^>]*)?>([^<]*)<', e)
            r[v] = float(m.group(1)) if m and m.group(1) else np.nan
        rows.append(r)
tsy = pd.DataFrame(rows)
tsy['date'] = pd.to_datetime(tsy['date'])
tsy = tsy.drop_duplicates('date').set_index('date').sort_index()
tsy.to_pickle(f'{H}/tsy.pkl')
print('tsy', tsy.index.min().date(), tsy.index.max().date(), len(tsy))

# ACM daily
acm = pd.read_excel(f'{H}/acm.xls', sheet_name='ACM Daily')
acm['DATE'] = pd.to_datetime(acm['DATE'], format='%d-%b-%Y')
acm = acm.set_index('DATE').sort_index()
acm.to_pickle(f'{H}/acm.pkl')
print('acm', acm.index.min().date(), acm.index.max().date())

# Fed funds monthly
d = json.load(open(f'{H}/ff_m.json'))['series']['docs'][0]
ff = pd.Series(d['value'], index=pd.to_datetime(d['period']), name='ff').astype(float)
ff.index = ff.index.to_period('M')
ff.to_pickle(f'{H}/ff.pkl')
print('ff', ff.index.min(), ff.index.max(), ff.iloc[-1])

# PCE price indexes monthly
d = json.load(open(f'{H}/pce_t20804.json'))['series']['docs']
def ser(code):
    x = [s for s in d if s['series_code'] == code][0]
    v = pd.Series(x['value'], index=pd.PeriodIndex(x['period'], freq='M'))
    return pd.to_numeric(v, errors='coerce')
pce = pd.DataFrame({'core': ser('DPCCRG-M'), 'head': ser('DPCERG-M')})
pce.to_pickle(f'{H}/pce.pkl')
print('pce', pce.index.min(), pce.index.max(), pce.iloc[-1].tolist())

# Unemployment monthly: DBnomics (to 2025-01) + BLS API (2025-2026)
d = json.load(open(f'{H}/un_dbn.json'))['series']['docs'][0]
un = pd.Series(d['value'], index=pd.PeriodIndex(d['period'], freq='M'))
un = pd.to_numeric(un, errors='coerce')
b = json.load(open(f'{H}/../data/bls.json'))
for s in b['Results']['series']:
    if s['seriesID'] == 'LNS14000000':
        for o in s['data']:
            if o['value'] != '-':
                un[pd.Period(f"{o['year']}-{o['period'][1:]}", 'M')] = float(o['value'])
un = un.sort_index()
un.to_pickle(f'{H}/un.pkl')
print('un', un.index.min(), un.index.max(), un.iloc[-1])

# Laubach-Williams quarterly (one-sided)
lw = pd.read_excel(f'{H}/lw.xlsx', sheet_name='data', header=None)
lw = lw[pd.to_datetime(lw[0], errors='coerce').notna()].copy()
lw = pd.DataFrame({'rstar': lw[2].astype(float).values, 'g': lw[3].astype(float).values, 'gap': lw[5].astype(float).values},
                  index=pd.PeriodIndex(pd.to_datetime(lw[0]), freq='Q'))
lw.to_pickle(f'{H}/lw.pkl')
print('lw', lw.index.min(), lw.index.max(), lw.iloc[-1].round(2).tolist())
