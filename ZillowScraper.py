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
url = "https://www.zillow.com/homedetails/1162-N-Reese-Dr-Provo-UT-84601/79764627_zpid/"
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

        # Extracting the variables
        price = house['list_price']
        city = house['city']
        state = house['state']
        zip_code = house['zip_code']
        beds = house['beds']
        status = house['status']  # <--- NEW VARIABLE
        hoa_monthly = house['hoa_fee'] if not pd.isna(house['hoa_fee']) else 0
        fips_code = house['fips_code']
        days_on_mls = house['days_on_mls']
        tax = house['tax']
        tax_history = house['tax_history']

        # Tax non-disclosure Handling:
        if pd.isna(tax):
            tax = get_tax_estimate(price, state, fips_code)
            print(f"Tax per year (ESTIMATED): ${tax:,.2f}")
        else:
            print(f"Tax per year: ${tax:,.2f}")

        print("\n--- Property Details ---")
        print(f"Status: {status.upper()}")  # Prints FOR_SALE, PENDING, etc.
        print(f"Price:  ${price:,}" if price else "Price:  N/A")
        print(f"City:   {city}")
        print(f"State:  {state}")
        print(f"Zip:    {zip_code}")
        print(f"Beds:   {beds}")
        print(f"HOA Monthly:   {hoa_monthly}")
        print(f"Fips Code:   {fips_code}")
        print(f"Days on Multiple listing service (mls):   {days_on_mls}")
        print(f"Tax per year:   {tax}")

    else:
        print("No results found. The house might be off-market or blocked.")
else:
    print("Could not parse address from URL.")
