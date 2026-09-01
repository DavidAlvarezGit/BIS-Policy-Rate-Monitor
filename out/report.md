# BIS Policy Rate Monitor

> Latest central-bank policy rates and recent developments from the Bank for International Settlements.

**Generated:** 2026-09-01 10:04 UTC  
**Period:** 2015-01-01 → latest available observation  
**Coverage:** United States, Euro area, United Kingdom, Japan, Switzerland  
**Requested:** ES, US, EA, GB, JP, CH  
**BIS codes:** ES, US, XM, GB, JP, CH  

---

## Latest Policy Rate Snapshot

| Country / Area   |    Rate | Latest Date   |   Monthly Δ | Last Move   | Last Change   |   Days Since Last Change |
|:-----------------|--------:|:--------------|------------:|:------------|:--------------|-------------------------:|
| United States    | 3.6250% | 2026-08-25    |           — | ↓ 0.2500 pp | 2025-12-11    |                      257 |
| Euro area        | 2.2500% | 2026-08-25    |           — | ↑ 0.2500 pp | 2026-06-17    |                       69 |
| United Kingdom   | 3.7500% | 2026-08-24    |           — | ↓ 0.2500 pp | 2025-12-18    |                      249 |
| Japan            | 1.0000% | 2026-08-25    |           — | ↑ 0.2500 pp | 2026-06-17    |                       69 |
| Switzerland      | 0.0000% | 2026-08-25    |           — | ↓ 0.2500 pp | 2025-06-20    |                      431 |

*Monthly Δ compares the latest observation with the final available observation before the current month. ↑ indicates a hike, ↓ a cut, and — no change.*

> [!WARNING]
> **Incomplete coverage:** Spain could not be included in the current policy-rate snapshot.
>
> ### Spain (ES)
>
> No policy-rate observations are available for Spain on or after **2015-01-01**.
>
> The most recent available BIS observation is **3.0000%** on **1998-12-31**.
>
> **BIS metadata**
>
> From 1 Jan 1999 onwards: the series is discontinued as Spain joined the euro area; from 14 May 1990 to 31 Dec 1998: the main policy rate was the marginal interest rate of the ten day auctions of Bank of Spain certificates; from 4 May 1983 to 13 May 1990: marginal interest rate of day-by-day monetary adjustment loans; from 14 Sep 1977 to 3 May 1983: marginal interest rate of overnight monetary adjustment loans; from 1 Jan 1945 to 13 Sep 1977: the rediscount interest rate.
>

---

## Policy Rate Developments

Policy-rate developments across the selected economies over the reporting period.

![Policy rate developments](policy_rates.png)

*Figure 1. Central-bank policy rates over time. Daily observations are shown where available, with monthly observations used as a fallback.*

---

## Methodology

Daily observations are used when available, with monthly observations used as a fallback. Countries must have at least one usable observation within the selected reporting period to be included in the snapshot. Monthly change compares the latest policy rate with the final available observation before the current month.

The last change is the most recent non-zero policy-rate move in the available BIS series. Days since change is measured from that observation to the latest available observation. Missing BIS observations are retained during transformation but excluded from calculations.

## Data Source

**Bank for International Settlements (BIS)**  
Central bank policy rates — bulk-download dataset.
