from fredapi import Fred
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
from boe_scrapper import get_uk_2y_yield
import os
import yfinance as yf

# Load Config
load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY")

# Setup Fred Client
fred = Fred(api_key="FRED_API_KEY")
 
# Get Latest US 2Y
if date.today().weekday() == 0:
    last_weekday = date.today() - timedelta(days=3)
else:
    last_weekday = date.today() - timedelta(days=1)

us_2y: pd.Series = fred.get_series("DGS2", last_weekday)

if us_2y.empty:
    latest_us_2y = None
else:
    latest_us_2y = us_2y.loc[last_weekday]

# Get Latest UK 2Y
latest_uk_2y = get_uk_2y_yield(target_date=last_weekday)

# Load historical data
# Load dtype map
dtype_map = pd.read_csv("data/uk_us_2y_spread_dtypes.csv", index_col=0).to_dict()

# Convert dtype strings to actual Python types
dtype_map = {
    col: eval(dtype_str) if "float" in dtype_str or "int" in dtype_str else "object"
    for col, dtype_str in dtype_map.items()
}

# Load cleaned data with correct types
spread_history = pd.read_csv("data/uk_us_2y_spread.csv", dtype=dtype_map, parse_dates=[0], index_col=0)

# Add latest data (calc spread and add to df)
# TODO: If either latest_us_2y or latest_uk_2y is None, skip
latest_spread = latest_uk_2y - latest_us_2y
spread_history.loc[last_weekday] = latest_spread

# Overwrite latest to CSV
spread_history.to_csv("data/uk_us_2y_spread.csv")
spread_history.dtypes.to_csv("data/uk_us_2y_spread_dtypes.csv")

# Generate live signal
spread_z_score = ((spread_history.loc[last_weekday] - spread_history.mean()) / spread_history.std()).iloc[0]

if spread_z_score > 1:
    signal = 1
elif spread_z_score < -1:
    signal = -1
else:
    signal = 0

# Get Account Equity
