"""
Global Macroeconomic Dashboard
================================
Sources  : FRED (US, monthly) · IMF DataMapper (multi-country, annual)
           World Bank / wbgapi (multi-country, annual)
Economies: USA · Euro Area · UK · Canada · Japan · China · Australia
Output   : Single scrollable Plotly window in your browser

Install  : pip install fredapi wbgapi requests plotly pandas
Run      : python macro_dashboard.py
"""

import warnings
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fredapi import Fred

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────────────────────

FRED_API_KEY = "your_key_here"
START_DATE   = "2015-01-01"
START_YEAR   = 2015

ECONOMIES = {
    "USA": {"wb": "USA", "imf": "USA",       "label": "United States"},
    "EU":  {"wb": "EMU", "imf": "EURO_AREA", "label": "Euro Area"},
    "UK":  {"wb": "GBR", "imf": "GBR",       "label": "United Kingdom"},
    "CAN": {"wb": "CAN", "imf": "CAN",       "label": "Canada"},
    "JPN": {"wb": "JPN", "imf": "JPN",       "label": "Japan"},
    "CHN": {"wb": "CHN", "imf": "CHN",       "label": "China"},
    "AUS": {"wb": "AUS", "imf": "AUS",       "label": "Australia"},
}

COLORS = {
    "USA": "#3b82f6", "EU": "#f59e0b", "UK": "#10b981",
    "CAN": "#ef4444", "JPN": "#8b5cf6", "CHN": "#ec4899", "AUS": "#06b6d4",
}

# ── FRED series that reliably return data ─────────────────────────────────────

FRED_SERIES = {
    "FEDFUNDS":      "Fed Funds Rate",
    "T10Y2Y":        "Yield Curve (10y-2y)",
    "T10YIE":        "10y Inflation Expectations",
    "UNRATE":        "Unemployment Rate",
    "PAYEMS":        "Nonfarm Payrolls",
    "CIVPART":       "Labor Force Participation",
    "CES0500000003": "Avg Hourly Earnings",
    "GDPC1":         "Real GDP",
    "INDPRO":        "Industrial Production",
    "RSXFS":         "Retail Sales ex-Auto",
    "TCU":           "Capacity Utilization",
    "PSAVERT":       "Personal Savings Rate",
    "BAMLH0A0HYM2":  "HY Credit Spread",
    "M2SL":          "M2 Money Supply",
}

# ── Fetch functions ───────────────────────────────────────────────────────────

def fetch_fred():
    print("[FRED] Fetching US series...")
    fred = Fred(api_key=FRED_API_KEY)
    frames = {}
    for sid, name in FRED_SERIES.items():
        try:
            frames[name] = fred.get_series(sid, observation_start=START_DATE)
            print(f"  ✓ {name}")
        except Exception as e:
            print(f"  ✗ {name}: {e}")
    df = pd.DataFrame(frames)
    df.index = pd.to_datetime(df.index)
    print(f"  → {len(df.columns)} series loaded.\n")
    return df.sort_index()


def fetch_imf():
    print("[IMF] Fetching WEO indicators...")
    base = "https://www.imf.org/external/datamapper/api/v1"
    indicators = {
        "NGDP_RPCH":   "Real GDP Growth (%)",
        "PCPIPCH":     "Inflation (%)",
        "LUR":         "Unemployment (%)",
        "BCA_NGDPD":   "Current Account (% GDP)",
        "GGXWDG_NGDP": "Govt Debt (% GDP)",
        "GGXCNL_NGDP": "Fiscal Balance (% GDP)",
    }
    result = {}
    eco_str = "/".join(c["imf"] for c in ECONOMIES.values())

    for code, label in indicators.items():
        try:
            r = requests.get(f"{base}/{code}/{eco_str}", timeout=20)
            r.raise_for_status()
            vals = r.json().get("values", {}).get(code, {})
            cols = {}
            for key, cfg in ECONOMIES.items():
                raw = vals.get(cfg["imf"], {})
                series = {pd.Timestamp(str(yr)): float(v)
                          for yr, v in raw.items()
                          if v is not None and int(yr) >= START_YEAR}
                if series:
                    cols[key] = pd.Series(series)
            if cols:
                result[label] = pd.DataFrame(cols).sort_index()
                print(f"  ✓ {label}")
            else:
                print(f"  ✗ {label}: no data")
        except Exception as e:
            print(f"  ✗ {label}: {e}")

    print(f"  → {len(result)} indicators loaded.\n")
    return result


def fetch_world_bank():
    import wbgapi as wb
    print("[World Bank] Fetching cross-country indicators...")
    indicators = {
        "NY.GDP.MKTP.KD.ZG": "GDP Growth (%)",
        "FP.CPI.TOTL.ZG":    "Inflation CPI (%)",
        "SL.UEM.TOTL.ZS":    "Unemployment (%)",
        "GC.DOD.TOTL.GD.ZS": "Govt Debt (% GDP)",
        "NE.EXP.GNFS.ZS":    "Exports (% GDP)",
        "NE.IMP.GNFS.ZS":    "Imports (% GDP)",
        "NE.GDI.TOTL.ZS":    "Gross Capital Formation (% GDP)",
        "NY.GDP.PCAP.CD":    "GDP per Capita (USD)",
    }
    wb_codes = [c["wb"] for c in ECONOMIES.values()]
    wb_to_key = {c["wb"]: k for k, c in ECONOMIES.items()}
    result = {}

    for code, label in indicators.items():
        try:
            raw = wb.data.DataFrame(code, economy=wb_codes,
                                    time=range(START_YEAR, 2025),
                                    numericTimeKeys=True)
            # Normalise orientation: rows = years, cols = economy codes
            if all(c in wb_codes for c in list(raw.index)[:3]):
                raw = raw.T
            raw.index = pd.to_datetime(raw.index.astype(str))
            raw.columns = [wb_to_key.get(c, c) for c in raw.columns]
            result[label] = raw.sort_index()
            print(f"  ✓ {label}")
        except Exception as e:
            print(f"  ✗ {label}: {e}")

    print(f"  → {len(result)} indicators loaded.\n")
    return result

# ── Build single-page dashboard ───────────────────────────────────────────────

def build_dashboard(fred, imf, wb):
    """
    Layout (14 subplots, 7 rows × 2 cols):
      Row 1 — US monetary policy            | US labor market
      Row 2 — US activity (IP + retail)     | US financial conditions
      Row 3 — Cross: GDP growth (IMF)       | Cross: GDP growth (WB)
      Row 4 — Cross: Inflation (IMF)        | Cross: Unemployment (IMF)
      Row 5 — Cross: Govt Debt (IMF)        | Cross: Fiscal Balance (IMF)
      Row 6 — Cross: Current Account (IMF)  | Cross: GDP per Capita (WB)
      Row 7 — Cross: Exports % GDP (WB)     | Cross: Imports % GDP (WB)
    """
    titles = [
        "US: Fed Funds Rate & Yield Curve",   "US: Labor Market",
        "US: Industrial Production & Retail (YoY %)", "US: M2 Growth & HY Spread",
        "Real GDP Growth % — IMF",             "GDP Growth % — World Bank",
        "Inflation % — IMF",                   "Unemployment % — IMF",
        "Govt Debt % GDP — IMF",               "Fiscal Balance % GDP — IMF",
        "Current Account % GDP — IMF",         "GDP per Capita USD — World Bank",
        "Exports % GDP — World Bank",          "Imports % GDP — World Bank",
    ]

    fig = make_subplots(
        rows=7, cols=2,
        subplot_titles=titles,
        vertical_spacing=0.055,
        horizontal_spacing=0.08,
        specs=[
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": True}],
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": False}],
        ],
    )

    # ── Helpers ───────────────────────────────────────────────────────────────
    def line(x, y, name, color, dash="solid", group=None, show=True, width=1.8):
        return go.Scatter(x=x, y=y, name=name,
                          line=dict(color=color, width=width, dash=dash),
                          legendgroup=group or name, showlegend=show,
                          hovertemplate="%{y:.2f}<extra>" + name + "</extra>")

    def add_cross(indicator, source, row, col, first_col=True):
        """Add one line per economy for a cross-country indicator."""
        if indicator not in source:
            return
        df = source[indicator]
        for i, (eco, cfg) in enumerate(ECONOMIES.items()):
            if eco not in df.columns:
                continue
            fig.add_trace(line(df.index, df[eco], cfg["label"], COLORS[eco],
                               group=eco, show=(row == 3 and first_col and i == 0)
                               or (row != 3)), row=row, col=col)

    # ── Row 1: US monetary ────────────────────────────────────────────────────
    if "Fed Funds Rate" in fred.columns:
        fig.add_trace(line(fred.index, fred["Fed Funds Rate"],
                           "Fed Funds Rate", "#60a5fa"), row=1, col=1)
    if "Yield Curve (10y-2y)" in fred.columns:
        yc = fred["Yield Curve (10y-2y)"].dropna()
        fig.add_trace(go.Scatter(x=yc.index, y=yc, name="Yield Curve (10y-2y)",
                                 line=dict(color="#f59e0b", width=1.5, dash="dot"),
                                 fill="tozeroy", fillcolor="rgba(245,158,11,0.09)",
                                 hovertemplate="%{y:.2f}<extra>Yield Curve</extra>"),
                      row=1, col=1)
        fig.add_hline(y=0, line_color="#475569", line_width=0.7, row=1, col=1)
    if "10y Inflation Expectations" in fred.columns:
        fig.add_trace(line(fred.index, fred["10y Inflation Expectations"],
                           "10y Inflation Exp.", "#a78bfa", dash="dash"), row=1, col=1)

    # ── Row 1: US labor ───────────────────────────────────────────────────────
    if "Unemployment Rate" in fred.columns:
        fig.add_trace(line(fred.index, fred["Unemployment Rate"],
                           "Unemployment Rate", "#f87171"), row=1, col=2)
    if "Labor Force Participation" in fred.columns:
        fig.add_trace(line(fred.index, fred["Labor Force Participation"],
                           "Labor Force Participation", "#34d399", dash="dash"), row=1, col=2)
    if "Avg Hourly Earnings" in fred.columns:
        ahe_yoy = fred["Avg Hourly Earnings"].dropna().pct_change(12) * 100
        fig.add_trace(line(ahe_yoy.index, ahe_yoy,
                           "Avg Hourly Earnings YoY%", "#fbbf24", dash="dot"), row=1, col=2)

    # ── Row 2: US activity ────────────────────────────────────────────────────
    for col_name, label, color in [
        ("Industrial Production", "Industrial Prod. YoY%", "#60a5fa"),
        ("Retail Sales ex-Auto",  "Retail Sales YoY%",     "#34d399"),
        ("Capacity Utilization",  "Capacity Utilization",  "#f59e0b"),
    ]:
        if col_name in fred.columns:
            if col_name == "Capacity Utilization":
                fig.add_trace(line(fred.index, fred[col_name], label, color, dash="dot"), row=2, col=1)
            else:
                yoy = fred[col_name].dropna().pct_change(12) * 100
                fig.add_trace(line(yoy.index, yoy, label, color), row=2, col=1)
    fig.add_hline(y=0, line_color="#475569", line_width=0.7, row=2, col=1)

    # ── Row 2: M2 + HY spread (dual axis) ────────────────────────────────────
    if "M2 Money Supply" in fred.columns:
        m2_yoy = fred["M2 Money Supply"].dropna().pct_change(12) * 100
        fig.add_trace(line(m2_yoy.index, m2_yoy, "M2 YoY%", "#67e8f9"),
                      row=2, col=2, secondary_y=False)
    if "HY Credit Spread" in fred.columns:
        hy = fred["HY Credit Spread"].dropna()
        fig.add_trace(line(hy.index, hy, "HY Credit Spread (bps)", "#f87171", dash="dot"),
                      row=2, col=2, secondary_y=True)

    # ── Rows 3–7: Cross-country ───────────────────────────────────────────────
    cross = [
        ("Real GDP Growth (%)",      imf, 3, 1),
        ("GDP Growth (%)",           wb,  3, 2),
        ("Inflation (%)",            imf, 4, 1),
        ("Unemployment (%)",         imf, 4, 2),
        ("Govt Debt (% GDP)",        imf, 5, 1),
        ("Fiscal Balance (% GDP)",   imf, 5, 2),
        ("Current Account (% GDP)",  imf, 6, 1),
        ("GDP per Capita (USD)",     wb,  6, 2),
        ("Exports (% GDP)",          wb,  7, 1),
        ("Imports (% GDP)",          wb,  7, 2),
    ]
    legend_shown = set()
    for indicator, source, row, col in cross:
        if indicator not in source:
            continue
        df = source[indicator]
        for eco, cfg in ECONOMIES.items():
            if eco not in df.columns:
                continue
            show = eco not in legend_shown
            if show:
                legend_shown.add(eco)
            fig.add_trace(line(df.index, df[eco], cfg["label"], COLORS[eco],
                               group=eco, show=show), row=row, col=col)

    # Zero lines for relevant panels
    for r, c in [(3,1),(3,2),(4,1),(5,2),(6,1)]:
        fig.add_hline(y=0, line_color="#475569", line_width=0.6, row=r, col=c)

    # ── Global layout ─────────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text="🌍 Global Macroeconomic Dashboard",
            font=dict(size=20, color="#f1f5f9"),
            x=0.5,
        ),
        height=4200,
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        font=dict(color="#e2e8f0", size=11),
        hovermode="x unified",
        legend=dict(
            bgcolor="#1e293b", bordercolor="#334155", borderwidth=1,
            orientation="h", x=0.5, xanchor="center", y=1.012, yanchor="bottom",
        ),
        margin=dict(l=60, r=40, t=120, b=60),
    )
    grid_style = dict(gridcolor="#334155", linecolor="#475569", zerolinecolor="#475569")
    fig.update_xaxes(**grid_style)
    fig.update_yaxes(**grid_style)

    return fig


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 55)
    print("  GLOBAL MACRO DASHBOARD")
    print("=" * 55 + "\n")

    fred_df  = fetch_fred()
    imf_data = fetch_imf()
    wb_data  = fetch_world_bank()

    print("Building dashboard...")
    fig = build_dashboard(fred_df, imf_data, wb_data)
    fig.show()
    print("Done — dashboard open in browser.\n")


if __name__ == "__main__":
    main()
