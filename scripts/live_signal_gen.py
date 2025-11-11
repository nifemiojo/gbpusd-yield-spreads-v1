from fredapi import Fred
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
from boe_scrapper import get_uk_2y_yield
import os
from ig_service import IGClient
from decimal import Decimal, ROUND_HALF_UP

def calculate_position_size(equity, current_price_obj, direction):
    desired_notional_exposure = 0.1 * equity

    current_price = current_price_obj["ask"] if direction == "BUY" else current_price_obj["bid"]
    notional_per_one_pound_per_point = current_price # Price is already per point

    size = desired_notional_exposure / notional_per_one_pound_per_point

    if size < 0.04: # Hardcoded min for GBP/USD
        print(f"Position size {size} too small. Setting to 0.04...")
        size = 0.04

    print(f"Calculated position size: {size:.2f}")

    return Decimal(size).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

print("Starting live execution service (demo account)...")
 
if date.today().weekday() == 0:
    last_weekday = date.today() - timedelta(days=3)
    print(f"Today is Monday so the latest yield data will be from {last_weekday.strftime("%A")}")
elif date.today().weekday() == 6:
    print("Today is Sunday so the script will exit.")
    exit("Today is Sunday so the script will exit.")
elif date.today().weekday() == 5:
    print("Today is Saturday so the script will exit.")
    exit("Today is Saturday so the script will exit.")
else:
    last_weekday = date.today() - timedelta(days=1)
    print(f"Today is a weekday so the latest yield data will be from {last_weekday.strftime("%A")}")


# Get Latest US 2Y

print("Getting latest US 2Y yield...")

# Load Config
load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY")

# Setup Fred Client
fred = Fred(api_key=FRED_API_KEY)

us_2y: pd.Series = fred.get_series("DGS2", last_weekday)

if us_2y.empty:
    print("No data found for US 2Y yield.")
    latest_us_2y = None
else:
    latest_us_2y = us_2y.iloc[0]
    print(f"Data found for US 2Y yield. Latest yield: {latest_us_2y}")

# Get Latest UK 2Y

print("Getting latest UK 2Y yield...")

latest_uk_2y = get_uk_2y_yield(target_date=last_weekday)

print(f"Retrieved latest UK 2Y yield. Latest yield: {latest_uk_2y}")

if latest_us_2y is None:
    print("No data found for US 2Y yield. Skipping...")
    exit("No data found for US 2Y yield. Skipping...")
elif latest_uk_2y is None:
    print("No data found for UK 2Y yield. Skipping...")
    exit("No data found for UK 2Y yield. Skipping...")

print("Both UK and US 2Y yields found. Continuing...")

print("Appending latest spread data to historical data and saving...")

# Load historical data
# Load dtype map
dtype_map = pd.read_csv("scripts/data/uk_us_2y_spread_dtypes.csv", index_col=0).to_dict()

# Convert dtype strings to actual Python types
dtype_map = {
    col: eval(dtype_str) if "float" in dtype_str or "int" in dtype_str else "object"
    for col, dtype_str in dtype_map.items()
}

# Load cleaned data with correct types
spread_history = pd.read_csv("scripts/data/uk_us_2y_spread.csv", dtype=dtype_map, parse_dates=[0], index_col=0)

# Add latest data (calc spread and add to df)
latest_spread = latest_uk_2y - latest_us_2y
spread_history.loc[last_weekday] = latest_spread

# Overwrite latest to CSV
spread_history.to_csv("scripts/data/uk_us_2y_spread.csv")
spread_history.dtypes.to_csv("scripts/data/uk_us_2y_spread_dtypes.csv")

print("Successfully calculated and saved spread history...")

# Generate live signal
print("Generating live signal...")
spread_z_score = ((spread_history.loc[last_weekday] - spread_history.mean()) / spread_history.std()).iloc[0]

if spread_z_score > 1:
    print("Spread is above 1 standard deviation. GBP/USD BUY signal...")
    signal = 1
elif spread_z_score < -1:
    print("Spread is below -1 standard deviation. GBP/USD SELL signal...")
    signal = -1
else:
    print("Spread is within 1 standard deviation. FLAT signal...")
    signal = 0

# Execution
ig_client = IGClient()

# Get Account Equity
print("Getting account equity...")
accounts_response = ig_client.get_accounts()

account = [a for a in accounts_response["accounts"] if a["accountId"] == "Z5YBJN"][0]
equity = account["balance"]["balance"] + account["balance"]["profitLoss"]

print(f"Account equity: {equity}")

# Get Account Position
print("Getting account position(s)...")
positions_response = ig_client.get_positions()

gbp_usd_positions = [position for position in positions_response["positions"] if position["market"]["instrumentName"] == "GBP/USD"]
has_open_gbp_position = len(gbp_usd_positions) > 0 # TODO: Handle cases where multiple positions exist

if has_open_gbp_position:
    existing_position_direction = gbp_usd_positions[0]["position"]["direction"]
    print(f"Account {account["accountId"]} has an open position for GBP/USD. Existing position direction: {existing_position_direction}")
else :
    print(f"Account {account['accountId']} does not have an open position for GBP/USD.")
    existing_position_direction = None

if (signal == -1 and existing_position_direction == "Sell") or (signal == 1 and existing_position_direction == "Buy") or (signal == 0 and existing_position_direction == None): 
    # Do nothing
    print("Signal and existing position direction match. No action required.")
    pass
elif signal == 0:
    print("Signal is flat. Closing existing position...")

    ig_client.close_position(gbp_usd_positions[0]["position"])
    
    print("Existing position closed. Now flat.")
elif existing_position_direction == None:
    new_direction = "BUY" if signal == 1 else "SELL"

    print(f"No existing position. Placing new {new_direction} order...")

    current_price = ig_client.get_current_price()
    position_size = calculate_position_size(equity, current_price, new_direction)

    ig_client.place_market_order(new_direction, equity)

    print("New position placed.")
else:
    print("Signal and existing position direction do not match. Closing existing position...")
    ig_client.close_position(gbp_usd_positions[0]["position"])
    
    new_direction = "BUY" if signal == 1 else "SELL"

    print(f"No existing position. Placing new {new_direction} order...")

    current_price = ig_client.get_current_price()
    position_size = calculate_position_size(equity, current_price, new_direction)

    ig_client.place_market_order(new_direction, equity)

    print("New position placed.")

print("Done.")


