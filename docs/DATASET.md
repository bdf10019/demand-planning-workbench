# Public dataset and evaluation

## Source and license

- Dataset: Online Retail II
- Creator: Daqing Chen
- Repository: UCI Machine Learning Repository
- DOI: `10.24432/C5CG6D`
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)
- Official page: <https://archive.ics.uci.edu/dataset/502/online%2Bretail>

The workbook contains 1,067,371 transactions from December 2009 through December 2011. The archive,
workbook, converted CSV and reports stay under `data/raw`, which is ignored by Git.

## Reproducible preparation

```powershell
python -m pip install -e ".[data]"
.\scripts\download-uci-dataset.ps1
.\scripts\prepare-uci-dataset.ps1 -TopSkus 12
```

`tools/prepare_uci.py` performs these documented transformations:

1. Reads both workbook sheets in streaming mode.
2. Keeps the configured country, defaulting to `United Kingdom`.
3. Removes cancellation invoices, non-positive quantities, invalid dates and negative prices.
4. Aggregates quantity and weighted average price by date, stock code and country.
5. Selects the 12 products with the highest active-day coverage, breaking ties by unit volume.
6. Emits no invoice, description or customer identifier.

The output retains gaps. The core input layer fills missing calendar dates with zero and reports that
assumption for every affected series.

## Recorded local evaluation

Evaluation date: 2026-08-22. Horizon: 28 days.

| Item | Result |
|---|---:|
| Source rows scanned | 1,067,371 |
| Rows filtered before aggregation | 106,153 |
| Converted daily rows | 6,928 |
| Selected SKU/location series | 12 |
| Source workbook SHA-256 | `bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980` |
| Converted CSV SHA-256 | `76f546f15d78290caa6944d54601e0df16e9e03a6317b72b885e6a201d154110` |
| Mean selected-model WAPE | 82.84% |
| Median selected-model WAPE | 82.53% |
| Selected models | Moving Average 10, Seasonal Naive 1, Croston-SBA 1 |
| CSV-to-forecast median, 20 runs | 64.71 ms |
| p95, 20 runs | 73.05 ms |
| Median throughput | 107,070 accepted rows/s |

The timing is a local development-machine observation, not a service-level objective. Generated reports
and the SQLite evaluation database remain ignored. Re-run the commands to reproduce results on another
machine.

## Interpretation limits

The large WAPE is an important negative result: these are intermittent retail sales with cancellations,
possible stockouts, missing business drivers and large order spikes. The evaluation proves the workflow,
evidence retention and honest metric handling; it does not support a production-accuracy claim. A real
deployment needs inventory availability, promotion and holiday features, product lifecycle information,
hierarchical reconciliation, richer models and planner review.
