"""
Global Real-World Data Connector â€” World Bank Open Data (api.worldbank.org)
=============================================================================
No API key required. Free, public, real data covering ~217 countries and
economies. This module fetches actual World Bank indicator series â€” it does
not simulate, mock, or fabricate anything. If the API is unreachable or a
query returns nothing, functions say so explicitly rather than returning
fallback fake numbers.

Sector -> indicator mapping is curated from the real World Bank indicator
catalog (https://data.worldbank.org/indicator). "Sector" here is purely a
label for organizing the dropdown in the UI â€” every indicator uses the
exact same fetch/parse code path.
"""

from __future__ import annotations
import requests
import pandas as pd

BASE_URL = "https://api.worldbank.org/v2"
TIMEOUT = 20

SECTOR_INDICATORS = {
    "Economics & Finance": {
        "GDP (current US$)": "NY.GDP.MKTP.CD",
        "GDP growth (annual %)": "NY.GDP.MKTP.KD.ZG",
        "Inflation, consumer prices (annual %)": "FP.CPI.TOTL.ZG",
        "Unemployment (% of labor force)": "SL.UEM.TOTL.ZS",
        "GDP per capita (current US$)": "NY.GDP.PCAP.CD",
        "Domestic credit to private sector (% of GDP)": "FS.AST.PRVT.GD.ZS",
    },
    "Education": {
        "Primary school enrollment (% gross)": "SE.PRM.ENRR",
        "Government education expenditure (% of GDP)": "SE.XPD.TOTL.GD.ZS",
        "Adult literacy rate (% ages 15+)": "SE.ADT.LITR.ZS",
        "School enrollment, tertiary (% gross)": "SE.TER.ENRR",
    },
    "Healthcare": {
        "Life expectancy at birth (years)": "SP.DYN.LE00.IN",
        "Health expenditure (% of GDP)": "SH.XPD.CHEX.GD.ZS",
        "Maternal mortality ratio (per 100,000 live births)": "SH.STA.MMRT",
        "Physicians (per 1,000 people)": "SH.MED.PHYS.ZS",
    },
    "Agriculture": {
        "Agricultural land (% of land area)": "AG.LND.AGRI.ZS",
        "Cereal yield (kg per hectare)": "AG.YLD.CREL.KG",
        "Arable land (% of land area)": "AG.LND.ARBL.ZS",
    },
    "Security": {
        "Intentional homicides (per 100,000 people)": "VC.IHR.PSRC.P5",
    },
    "Engineering & Infrastructure": {
        "Access to electricity (% of population)": "EG.ELC.ACCS.ZS",
        "Individuals using the Internet (% of population)": "IT.NET.USER.ZS",
        "Mobile cellular subscriptions (per 100 people)": "IT.CEL.SETS.P2",
    },
    "Population & Demographics": {
        "Total population": "SP.POP.TOTL",
        "Urban population (% of total)": "SP.URB.TOTL.IN.ZS",
    },
    "Environment & Climate": {
        "CO2 emissions (metric tons per capita)": "EN.ATM.CO2E.PC",
        "Forest area (% of land area)": "AG.LND.FRST.ZS",
    },
}


def fetch_country_list() -> pd.DataFrame:
    """Real list of countries/economies from the World Bank API (excludes
    aggregate regions like 'World' or 'Sub-Saharan Africa')."""
    url = f"{BASE_URL}}/country"
    params = {"format": "json", "per_page": 400}
    resp = requests.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    if not isinstance(payload, list) or len(payload) < 2:
        raise RuntimeError("Unexpected response shape from World Bank country list API.")
    rows = []
    for c in payload[1]:
        region = (c.get("region") or {}).get("value", "")
        if region == "Aggregates":
            continue
        rows.append({
            "iso3": c.get("id"),
            "name": c.get("name"),
            "region": region,
            "income_level": (c.get("incomeLevel") or {}).get("value", ""),
        })
    return pd.DataFrame(rows).sort_values("name").reset_index(drop=True)


def fetch_indicator_series(country_iso3_list: list[str], indicator_code: str,
                            date_range: str = "1990:2025") -> pd.DataFrame:
    """Real indicator series for one or more countries. Returns a tidy
    DataFrame with columns: country, iso3, year, value. Raises/returns an
    empty frame with an explanatory message rather than fabricating data
    when the API has nothing for a given country/indicator combination."""
    if not country_iso3_list:
        raise ValueError("Provide at least one country ISO3 code.")
    countries = ";".join(country_iso3_list)
    url = f"{BASE_URL}}/country/{countries}}/indicator/{indicator_code}}"
    params = {"format": "json", "date": date_range, "per_page": 20000}
    resp = requests.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()

    if isinstance(payload, dict) and "message" in payload:
        msg = payload["message"][0].get("value", "Unknown World Bank API error.")
        raise RuntimeError(f"World Bank API error: {msg}}")
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        return pd.DataFrame(columns=["country", "iso3", "year", "value"])

    rows = []
    for rec in payload[1]:
        if rec.get("value") is None:
            continue
        rows.append({
            "country": (rec.get("country") or {}).get("value"),
            "iso3": rec.get("countryiso3code"),
            "year": int(rec["date"]),
            "value": float(rec["value"]),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["country", "year"]).reset_index(drop=True)


def fetch_multi_indicator(country_iso3_list: list[str], indicator_codes: dict[str, str],
                           date_range: str = "1990:2025") -> pd.DataFrame:
    """Fetch several indicators for the same countries and merge into one
    wide DataFrame (one row per country-year, one column per indicator
    label). Each indicator is a separate real API call â€” the World Bank
    API does not support multi-indicator queries in a single request."""
    merged = None
    errors = []
    for label, code in indicator_codes.items():
        try:
            df = fetch_indicator_series(country_iso3_list, code, date_range)
        except Exception as e:
            errors.append(f"{label}} ({code}}): {e}}")
            continue
        if df.empty:
            errors.append(f"{label}} ({code}}): no data returned for this selection.")
            continue
        df = df.rename(columns={"value": label})
        merged = df if merged is None else pd.merge(merged, df, on=["country", "iso3", "year"], how="outer")
    if merged is None:
        merged = pd.DataFrame(columns=["country", "iso3", "year"])
    return merged, errors
