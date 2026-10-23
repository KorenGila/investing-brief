# Model behind the brief

Three pieces, no fitted parameters:

1. Center: the NY Fed ACM model's forecast of rates.
2. Spread: for every month since 1990, how far each fund's yield ended up a year later from that month's forecast, with the 1990-2025 average miss removed.
3. Returns: average yield − fee − duration × change in yield + ½ × convexity × change², with iShares' published yield, duration and convexity, applied to each historical miss.

Two optional view knobs shift the center: a Fed-path view (as a 2-year miss, passed to each fund by its historical slope) and a 10-year term-premium change (passed by ACM's term-premium loadings).

## Data (download into one directory)
- Treasury par yield curve, one XML file per year 1990-2026: `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=YYYY` saved as `tsy_YYYY.xml`
- ACM term premia: `https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls` as `acm.xls`
- Fed funds monthly: DBnomics `FED/H15/RIFSPFF_N.M` as `ff_m.json`
- PCE price indexes: DBnomics `BEA/NIPA-T20804` as `pce_t20804.json`
- Unemployment: DBnomics `BLS/ln/LNS14000000` as `un_dbn.json`, plus the BLS API for recent months
- Laubach-Williams file `lw.xlsx` (used only by `estimate.py` for episode descriptions)

## Order
1. `python3 -I load.py DIR`
2. `python3 -I estimate.py DIR` (episodes, 12-month change percentiles, hiking cycles, ACM path today)
3. `python3 -I analogs.py DIR` (reference episodes quoted next to the knobs)
4. `python3 -I misses.py DIR` (12-month forecast misses and knob loadings)
5. `python3 -I build_v3.py DIR template_v3.html ../index.html`

When refreshing, update the curve date and the iShares fund figures in `build_v3.py`.
