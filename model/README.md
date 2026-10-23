# Model behind the brief

Scripts that produce every number in `../index.html`. Run with `python3 -I <script> <data_dir> [...]`.

## Data (download into one directory)
- Treasury par yield curve, one XML file per year 1990-2026: `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=YYYY` saved as `tsy_YYYY.xml`
- ACM term premia: `https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls` as `acm.xls`
- Laubach-Williams r*: `https://www.newyorkfed.org/medialibrary/media/research/economists/williams/data/Laubach_Williams_current_estimates.xlsx` as `lw.xlsx`
- Fed funds monthly: DBnomics `FED/H15/RIFSPFF_N.M` as `ff_m.json`
- PCE price indexes: DBnomics `BEA/NIPA-T20804` as `pce_t20804.json`
- Unemployment: DBnomics `BLS/ln/LNS14000000` as `un_dbn.json`, plus the BLS API for recent months (`../data/bls.json` relative to the data directory)

## Order
1. `load.py DIR` cleans raw files into pickles
2. `estimate.py DIR` episodes, curve regressions, distributions, hiking cycles, ACM path today
3. `rule2.py DIR` Fed reaction function (the page uses the `du4` version)
4. `analogs.py DIR` episode surprises vs forwards
5. `engine2.py DIR .` structural-model backtest (needs `engine_core.py` beside it)
6. `pricing.py DIR` fund ladder calibration and 2026 YTD check
7. `scen2.py DIR` scenario results, writes `data_engine.json`
8. `build.py DIR <folder with template.html and scripts/engine.js> ../index.html`

Update `TODAY` (curve) and fund yields in `scen2.py` and the copy in `template.html` when refreshing.
