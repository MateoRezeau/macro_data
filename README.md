# Global Macroeconomic Dashboard

An automated Python dashboard that pulls live macroeconomic data from three public APIs and renders an interactive, single-page chart in your browser. Updated weekly.

---

## What It Shows

The dashboard contains 14 panels in a single scrollable window:

**United States (monthly, FRED)**
- Monetary policy: Fed Funds Rate, yield curve (10y-2y), inflation expectations
- Labor market: unemployment rate, labor force participation, wage growth (YoY)
- Activity: industrial production, retail sales, capacity utilization
- Financial conditions: M2 money supply growth, high-yield credit spread

**Cross-Country Comparison — USA · Euro Area · UK · Canada · Japan · China · Australia (annual)**
- Real GDP growth (IMF + World Bank)
- Inflation — CPI %
- Unemployment rate
- Government gross debt (% GDP)
- Fiscal balance (% GDP)
- Current account balance (% GDP)
- GDP per capita (USD)
- Exports & imports (% GDP)

---

## Data Sources

| Source | Access | Frequency | Coverage |
|---|---|---|---|
| [FRED](https://fred.stlouisfed.org/) — Federal Reserve Bank of St. Louis | Free API key | Monthly | US only |
| [IMF DataMapper](https://www.imf.org/external/datamapper) | Open, no key needed | Annual | 7 economies |
| [World Bank](https://data.worldbank.org/) via `wbgapi` | Open, no key needed | Annual | 7 economies |

All data covers the last 10 years.

---

## Setup

**1. Clone the repository**
```bash
git clone https://github.com/MateoRezeau/macro_data.git
cd macro_data_
```

**2. Install dependencies**
```bash
pip install fredapi wbgapi requests plotly pandas
```

**3. Add your FRED API key**

Get a free key at [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html), then open `macro_dashboard.py` and replace the value on line 24:
```python
FRED_API_KEY = "your_key_here"
```
