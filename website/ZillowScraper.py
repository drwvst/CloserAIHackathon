import re
from typing import Any
import pandas as pd
from homeharvest import scrape_property

def extract_address_from_url(url: str) -> str | None:
    match = re.search(r"/(?:homedetails|realestateandhomes-detail)/([^/]+)", url)
    if not match: return None
    address_part = match.group(1).split("/")[0].split("_")[0]
    return address_part.replace("-", " ")

def extract_zpid_from_url(url: str) -> str | None:
    match = re.search(r"/(\d+)_zpid/?", url)
    return match.group(1) if match else None

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None and not pd.isna(value) else default
    except: return default

def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value) if value is not None and not pd.isna(value) else default
    except: return default

def normalize_property_row(row: pd.Series) -> dict[str, Any]:
    return {
        "street": str(row.get("street", "Unknown")),
        "city": str(row.get("city", "Unknown")),
        "state": str(row.get("state", "Unknown")),
        "price": _safe_float(row.get("list_price")),
        "beds": _safe_int(row.get("beds")),
        "baths": _safe_float(row.get("full_baths")),
        "sqft": _safe_int(row.get("sqft")),
        "year_built": _safe_int(row.get("year_built")),
        "hoa_monthly": _safe_float(row.get("hoa_fee")), # Added HOA
        "property_url": str(row.get("property_url", ""))
    }


def scrape_listing(url: str) -> dict[str, Any]:
    """Scrapes specific property with strict house-number matching."""
    address_str = extract_address_from_url(url)
    target_zpid = extract_zpid_from_url(url)

    # NEW: Extract just the house number (e.g., "1071") to use as a backup filter
    house_num_match = re.search(r"^(\d+)", address_str) if address_str else None
    house_num = house_num_match.group(1) if house_num_match else None

    if not address_str:
        raise ValueError("Could not parse address from URL.")

    # Fetch data - we include multiple statuses to ensure we find the listing
    data = scrape_property(location=address_str, listing_type=["for_sale", "pending", "sold", "off_market"])

    if data.empty:
        raise ValueError(f"No listing data found for: {address_str}")

    # MATCHING LOGIC
    best_row = data.iloc[0]  # Default to first

    for _, row in data.iterrows():
        row_url = str(row.get("property_url", ""))
        row_street = str(row.get("street", ""))

        # 1. Best case: ZPID match
        if target_zpid and target_zpid in row_url:
            best_row = row
            break

        # 2. Secondary case: Street number match (Fixes the "Wrong House" issue)
        if house_num and row_street.startswith(house_num):
            best_row = row
            # Continue loop in case a ZPID match is found further down
            continue

    return normalize_property_row(best_row)

def get_area_comps(city: str, state: str, max_results: int = 5) -> list[dict[str, Any]]:
    try:
        data = scrape_property(location=f"{city}, {state}", listing_type=["for_sale"])
        return [normalize_property_row(row) for _, row in data.head(max_results).iterrows()]
    except: return []