import re
from homeharvest import scrape_property

def extract_address_from_url(url):
    # This regex pulls the address part out of Zillow/Realtor URLs
    # Example: /homedetails/1616-N-2100-W-Provo-UT-84604/... -> 1616 N 2100 W, Provo, UT 84604
    match = re.search(r'/(?:homedetails|realestateandhomes-detail)/([^/]+)', url)
    if match:
        address_part = match.group(1).split('_')[0] # Handle Realtor.com underscores
        address_clean = address_part.replace('-', ' ')
        return address_clean
    return None

# Your test URL
url = "https://www.zillow.com/homedetails/1616-N-2100-W-Provo-UT-84604/11901038_zpid/"
address = extract_address_from_url(url)

if address:
    print(f"Searching for: {address}")
    # FIXED CALL: Removed site_name
    data = scrape_property(
        location=address,
        listing_type="for_sale"
    )

    if not data.empty:
        # Get the first match
        house = data.iloc[0]
        print("--- Property Found ---")
        print(f"Price: ${house['list_price']}")
        print(f"City:  {house['city']}")
        print(f"State: {house['state']}")
        print(f"Zip:   {house['zip_code']}")
        print(f"Beds:  {house['beds']}")
    else:
        print("No results found. The site might be blocking the request.")
else:
    print("Could not parse address from URL.")
