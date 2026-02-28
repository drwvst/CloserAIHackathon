import re
from typing import Any

import pandas as pd
from homeharvest import scrape_property


def extract_address_from_url(url: str) -> str | None:
    """Extract a best-effort address token from supported listing URLs."""
    match = re.search(r"/(?:homedetails|realestateandhomes-detail)/([^/]+)", url)
    if not match:
        return None
    address_part = match.group(1).split("_")[0]
    return address_part.replace("-", " ")


def get_tax_estimate(price: float, state: str, fips_code: str) -> float:
    """Estimate annual tax when listing data omits it."""
    if state == "TX":
        return price * 0.021
    return price * 0.012


def _safe_float(value: Any, default: float = 0.0) -> float:
    return float(value) if not pd.isna(value) else default


def _safe_int(value: Any, default: int = 0) -> int:
    return int(value) if not pd.isna(value) else default


def _safe_str(value: Any, default: str = "") -> str:
    return str(value) if not pd.isna(value) else default


def normalize_property_row(row: pd.Series) -> dict[str, Any]:
    price = _safe_float(row.get("list_price"), 0)
    state = _safe_str(row.get("state"), "N/A")
    fips_code = _safe_str(row.get("fips_code"), "N/A")

    raw_tax = row.get("tax")
    if pd.isna(raw_tax):
        tax = get_tax_estimate(price, state, fips_code)
        tax_estimated = True
    else:
        tax = float(raw_tax)
        tax_estimated = False

    return {
        "price": price,
        "city": _safe_str(row.get("city"), "Unknown"),
        "state": state,
        "zip_code": _safe_str(row.get("zip_code"), "N/A"),
        "beds": _safe_int(row.get("beds"), 0),
        "baths": _safe_float(row.get("full_baths"), 0),
        "sqft": _safe_int(row.get("sqft"), 0),
        "year_built": _safe_int(row.get("year_built"), 0),
        "status": _safe_str(row.get("status"), "UNKNOWN").upper(),
        "hoa_monthly": _safe_float(row.get("hoa_fee"), 0),
        "fips_code": fips_code,
        "days_on_mls": _safe_int(row.get("days_on_mls"), 0),
        "tax_annual": tax,
        "tax_estimated": tax_estimated,
        "nearby_schools": row.get("nearby_schools") if not pd.isna(row.get("nearby_schools")) else [],
        "street": _safe_str(row.get("street"), ""),
        "latitude": _safe_float(row.get("latitude"), 0),
        "longitude": _safe_float(row.get("longitude"), 0),
    }


def scrape_listing(url: str) -> dict[str, Any]:
    """Scrape and normalize a listing from a Zillow/Realtor URL."""
    address = extract_address_from_url(url)
    if not address:
        raise ValueError("Could not parse address from URL.")

    data = scrape_property(location=address, listing_type=["for_sale", "pending", "sold", "off_market"])
    if data.empty:
        raise ValueError("No listing data found for this URL.")

    return normalize_property_row(data.iloc[0])


def get_area_comps(city: str, state: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Get simple comparable nearby listings for recommendation context."""
    if not city or not state:
        return []

    try:
        data = scrape_property(location=f"{city}, {state}", listing_type=["for_sale"])
    except Exception:
        return []

    if data.empty:
        return []

    comps = []
    for _, row in data.head(max_results).iterrows():
        comps.append(
            {
                "street": _safe_str(row.get("street"), "Unknown"),
                "price": _safe_float(row.get("list_price"), 0),
                "beds": _safe_int(row.get("beds"), 0),
                "baths": _safe_float(row.get("full_baths"), 0),
                "sqft": _safe_int(row.get("sqft"), 0),
                "status": _safe_str(row.get("status"), "").upper(),
            }
        )
    return comps
