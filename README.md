# GBP/USD Yield-Spread Research

An empirical investigation of UK–US two-year government bond yield spreads and their relationship with GBP/USD, using Python.

**Do interest-rate differentials contain useful information about FX behaviour?** This project uses the two-year yield spread as an imperfect proxy for expected rate differentials, then tests the idea through data analysis, an exploratory signal backtest and a demo execution prototype.

## What it demonstrates

- **Financial reasoning:** connects a macroeconomic hypothesis to observable yield and FX data.
- **Quantitative research:** compares FX levels and returns using regression, lag analysis, z-scores and rolling correlations.
- **Strategy experimentation:** builds a spread-based signal with transaction-cost assumptions, equity curves and drawdown analysis.
- **Implementation:** combines data collection, signal generation and an IG broker API client.

## Start here

| Material | Focus |
|---|---|
| [Main analysis and backtest](notebooks/spread_gpbusd_analysis.ipynb) | Regressions, lag comparisons and the exploratory trading signal |
| [Extended analysis](notebooks/spread_gpbusd_analysis_full.ipynb) | Rolling standardisation and changing relationships |
| [Spread features](notebooks/2y_spread_feature_engineering.ipynb) | Preparing the explanatory variables |
| [Signal prototype](scripts/live_signal_gen.py) | Bank of England/FRED data collection and signal-to-order workflow |
| [IG API client](scripts/ig_service.py) | Authentication, positions and order requests |

Historical CSV snapshots are included under [data/](data/), with cleaning and feature-engineering notebooks under [notebooks/](notebooks/).

## Findings and research limits

The analysis finds weak explanatory power for daily FX returns. Relationships in FX levels motivate further investigation, but non-stationarity, spurious correlation and searching across many lags prevent treating them as evidence of reliable predictability.

The backtest is **exploratory**: its full-sample z-scores introduce future information into historical signals. Performance reporting also needs correction, including Sharpe-ratio arithmetic and a win-rate calculation based on underlying FX returns rather than strategy profits. The next step is past-data-only signal construction, corrected metrics and held-out evaluation.

## Explore locally

From the cloned repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pandas numpy matplotlib statsmodels jupyter
cd notebooks
jupyter notebook
```

On Windows, activate with `.venv\Scripts\activate`. Open the analysis notebooks from the `notebooks/` directory so their relative CSV paths resolve. Saved outputs can be reviewed on GitHub without installing dependencies; a clean end-to-end rerun is not yet established, and dependency versions are not pinned.

## Execution prototype

The scripts illustrate a demo-account workflow and are not a ready-to-run trading system. They additionally use `fredapi`, `python-dotenv` and `requests`, with environment-based FRED/IG credentials.

The signal script references local history files absent from the repository and requires fixes to order sizing and position handling. Its endpoint is configurable through `IG_BASE_URL`; the printed “demo” label does not enforce a demo connection. Review and repair it before use, and use a demo account only.
