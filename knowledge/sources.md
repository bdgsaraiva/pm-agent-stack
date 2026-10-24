# Source registry

One row per source, with the fields from specialists-kickoff.md section 3.1: free or paid, licence for personal use, reachable from GitHub Actions, history, release time, and whether vintages exist. "In repo" rows come from the adapters and their config. "Checked" rows were verified in a build session (date in the row). "Candidate" rows are not checked yet. A source passes when it is free, its licence allows personal research use, it is reachable from Actions, and its history covers at least one full cycle of the series.

## In the repo

| Source | Adapter / block | Free | Licence (personal use) | Actions | History in repo | Release (local) | Vintages |
|---|---|---|---|---|---|---|---|
| EIA weekly petroleum (WPSR) | `eia`, `eia_bal` | yes (key `EIA_API_KEY`) | US government, public domain | yes | 2015 on (`eia_bal`), 2018 on (`eia`) | Wed 10:30 ET; Thu 12:00 ET after a Monday holiday | no (latest values only; first prints lost on revision) |
| FRED (incl. EIA spot prices) | `fred` | yes | per series; EIA/Treasury series public domain | yes | 1986 on (deep fetch) | daily | ALFRED has vintages (not wired) |
| CFTC disaggregated COT | `cftc` | yes | public | yes | 2006 on (agent 12 one-time fetch), 2020 on (daily block) | Fri 15:30 ET for Tuesday | no |
| Yahoo Finance prices | `prices`, `prices_rv` | yes | **unofficial, personal use only; never port** | yes | 1986 on where it exists | delayed intraday / daily | no |
| WASDE (USDA) | `wasde` | yes | public | yes | first-published CSVs | 12:00 ET on report day | yes (each report as first published) |
| USDA FAS PSD | `usda_psd` | yes (key `USDA_FAS_API_KEY`) | public | yes | 2007/08 on | monthly with WASDE | no |
| USDA NASS Quick Stats | `nass` | yes (key `NASS_API_KEY`) | public | yes | crop condition, Grain Stocks | Mon 16:00 ET (progress) | no |
| LME via Westmetall | `lme` | yes | **personal use only** (licensed LME data) | yes | 2018 on | daily | no |
| GDELT (DOC, GKG via BigQuery) | `gdelt`, `gdelt_bq`, `gdelt_bq_v2`, `gdelt_disc` | yes (BigQuery free tier) | cite "The GDELT Project" | yes | 2017 on (DOC), Aug 2025 on (GKG v2) | 15-minute updates | n/a |
| News RSS (headlines only) | `news` | yes | headlines, links, outlet and time only; 45 days | yes | 45 days | continuous | n/a |
| Japan MoF JGB yields | `mof_jgb` | yes | public | yes | 2015 on | daily | no |

## Candidates (from the brief; status updated as each is checked)

| Complex | Source | Status |
|---|---|---|
| Energy | EIA STEO (monthly; free archive of vintages) | checked in S1, see below |
| Energy | JODI oil database | checked in S1, see below |
| Energy | OPEC Monthly Oil Market Report | checked in S1, see below |
| Energy | Baker Hughes rig count | checked in S1, see below |
| Energy | ANP (Brazil) | checked in S1, see below |
| Metals | LME stocks, SHFE weekly stocks, China customs trade, USGS | candidate (S3) |
| Ags and sugar | USDA export sales, crop progress, Conab, UNICA, Secex, US Drought Monitor | candidate (S4) |
| Cross-cutting | NOAA ENSO, ECMWF open data, Copernicus Sentinel, FAO AMIS, World Bank Pink Sheet, ALFRED vintages | candidate |
