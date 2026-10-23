# Model behind the brief

Three pieces, all in plain Python with no fitted parameters:

1. Market forecast: the NY Fed ACM model's expected short-rate path.
2. Scenarios: for each past episode, how far the Fed rate and the 2-, 10- and 30-year yields ended up 12 months later from the ACM forecast at the start. A scenario is the average of its episodes.
3. Returns: average yield − fee − duration × change in yield + ½ × convexity × change², with iShares' published yield, duration and convexity.

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
3. `python3 -I analogs.py DIR` (episode surprises vs the forecast)
4. `python3 -I build_simple.py DIR template_simple.html ../index.html`

When refreshing, update the curve date and the iShares fund figures in `build_simple.py`.
