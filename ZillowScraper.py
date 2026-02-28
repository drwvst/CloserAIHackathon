import re
from homeharvest import scrape_property
import pandas as pd


def extract_address_from_url(url):
    match = re.search(r'/(?:homedetails|realestateandhomes-detail)/([^/]+)', url)
    if match:
        address_part = match.group(1).split('_')[0]
        address_clean = address_part.replace('-', ' ')
        return address_clean
    return None


# url = "https://www.zillow.com/homedetails/1616-N-2100-W-Provo-UT-84604/11901038_zpid/"
# url = "https://www.zillow.com/homedetails/1162-N-Reese-Dr-Provo-UT-84601/79764627_zpid/"
url = "https://www.zillow.com/homedetails/983-Anderson-Glen-Dr-Cincinnati-OH-45255/34273898_zpid/"
# url = "https://www.realtor.com/realestateandhomes-detail/23-N-Plum-Crest-Cir_The-Woodlands_TX_77382_M71493-19745"
address = extract_address_from_url(url)

def get_tax_estimate(price, state, fips_code):
    # Montgomery County, TX (FIPS 48339) has an avg tax rate of ~1.9% to 2.2%
    # We use a 2.0% estimate for Texas as a safe bet.
    if state == "TX":
        return price * 0.021 # Texas average is high because no state income tax
    else:
        return price * 0.012 # National average 1.2%


if address:
    print(f"Searching for: {address}...")

    # We pass a list of types to ensure we catch Pending or Off-Market houses
    data = scrape_property(
        location=address,
        listing_type=["for_sale", "pending", "sold", "off_market"]
    )

    if not data.empty:
        house = data.iloc[0]
        print(data.columns.tolist())

        # --- CLEAN/SANITIZE VARIABLES ---
        # This prevents the "Ambiguous NA" error by ensuring every variable is a standard Python type
        price = float(house['list_price']) if not pd.isna(house['list_price']) else 0
        city = str(house['city']) if not pd.isna(house['city']) else "Unknown"
        state = str(house['state']) if not pd.isna(house['state']) else "N/A"
        zip_code = str(house['zip_code']) if not pd.isna(house['zip_code']) else "N/A"
        beds = int(house['beds']) if not pd.isna(house['beds']) else 0
        status = str(house['status']).upper() if not pd.isna(house['status']) else "UNKNOWN"
        hoa_monthly = float(house['hoa_fee']) if not pd.isna(house['hoa_fee']) else 0
        fips_code = str(house['fips_code']) if not pd.isna(house['fips_code']) else "N/A"
        days_on_mls = int(house['days_on_mls']) if not pd.isna(house['days_on_mls']) else 0
        nearby_schools = house['nearby_schools']

        # Handle Tax (Keep as float for math later)
        raw_tax = house['tax']
        if pd.isna(raw_tax):
            tax = get_tax_estimate(price, state, fips_code)
            tax_label = f"${tax:,.2f} (ESTIMATED)"
        else:
            tax = float(raw_tax)
            tax_label = f"${tax:,.2f}"

        # --- UPDATED PRINT SECTION ---
        print("\n--- Property Details ---")
        print(f"Status:      {status}")
        print(f"Price:       ${price:,.2f}" if price > 0 else "Price:       N/A")
        print(f"City:        {city}")
        print(f"State:       {state}")
        print(f"Zip:         {zip_code}")
        print(f"Beds:        {beds}")
        print(f"HOA Monthly: ${hoa_monthly:,.2f}")
        print(f"Fips Code:   {fips_code}")
        print(f"Days on MLS: {days_on_mls}")
        print(f"Tax per year: {tax_label}")


    else:
        print("No results found. The house might be off-market or blocked.")
else:
    print("Could not parse address from URL.")
