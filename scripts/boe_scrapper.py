import requests
import zipfile
import io
import pandas as pd
from datetime import datetime
import re

def get_uk_2y_yield(target_date: datetime = None) -> float:
    """
    Fetches the latest UK 2-year nominal spot yield from the Bank of England's published ZIP file.
    
    Steps:
      1. Download ZIP file from BoE.
      2. Extract file containing "Nominal" in its name.
      3. Open the sheet containing "spot curve".
      4. Extract 2-year yield for the given date (or previous available date if not found).
    """
    # Use today by default
    if target_date is None:
        target_date = datetime.today()

    # Bank of England latest yield curve zip
    url = "https://www.bankofengland.co.uk/-/media/boe/files/statistics/yield-curves/latest-yield-curve-data.zip"

    print("Downloading latest yield curve data from BoE...")
    resp = requests.get(url)
    resp.raise_for_status()

    print("Successfully downloaded latest yield curve data from BoE.")

    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        # Find the Excel file with "Nominal" in its name
        nominal_files = [file for file in z.namelist() if re.search(r"nominal", file, re.IGNORECASE)]
        if not nominal_files:
            raise FileNotFoundError("No 'Nominal' file found in ZIP archive.")
        file_name = nominal_files[0]
        print(f"Found nominal file: {file_name}")

        # Extract Excel file into memory
        with z.open(file_name) as file:
            # Find sheet with "spot curve"
            xls = pd.ExcelFile(file)
            spot_sheet = next((sheet for sheet in xls.sheet_names if re.search(r"spot curve", sheet, re.IGNORECASE)), None)
            if spot_sheet is None:
                raise ValueError("No sheet containing 'spot curve' found.")
            
            df = pd.read_excel(xls, sheet_name=spot_sheet, header=None)

            print(f"Succesfully created dataframe from {file_name} sheet {spot_sheet}")
    
    # Clean up and identify where the data starts
    # Find the header row (contains "years")
    header_row_idx = df.index[df[df.columns[0]].astype(str).str.contains("year", case=False, na=False)][0]

    # Remove rows before the header
    df = df.iloc[header_row_idx :]

    # Rename first column
    df = df.rename(columns={df.columns[0]: "Date"})
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", format="%d %b %y")

    # Determine if target date is present
    target_date = pd.to_datetime(target_date)
    if target_date not in df["Date"].values:
        save_to_file(df)
        print(f"No yield data found for {target_date.date()}")
        return None

    maturities = pd.to_numeric(df.loc[header_row_idx], errors="coerce")

    # Extract 2-year yield
    if df.columns[maturities == 2].empty:
        save_to_file(df)
        raise ValueError("2.0-year maturity column not found in dataset.")
    
    uk_2y_yield = float(df.loc[df["Date"] == pd.to_datetime(target_date), df.columns[maturities == 2]].iloc[0, 0])
    print(f"UK 2Y yield on {target_date.date()}: {uk_2y_yield:.2f}%")
    return uk_2y_yield

def save_to_file(df):
    # Save to file
    file_name = f"yield_curve_{datetime.now().strftime('%Y-%m-%d')}.csv"
    df.to_csv(file_name, index=False)

# Example usage:
if __name__ == "__main__":
    yield_today = get_uk_2y_yield()
    print("Current UK 2Y Yield:", yield_today)
