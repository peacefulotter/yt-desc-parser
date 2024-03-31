import gspread
import pandas as pd

from gspread_formatting.dataframe import format_with_dataframe
from gspread_dataframe import get_as_dataframe, set_with_dataframe

WORKSHEET_KEY = "1d-ajZTAA2DHnip3LWsMZQzfty817B6VWBumiaLV-XTs"
WORKSHEET_NAME = "YT-PARSER"

gc = gspread.service_account(filename="creds.json")


def save_to_spreadsheet(links):
    wks = gc.open_by_key(WORKSHEET_KEY)
    ws = wks.worksheet(WORKSHEET_NAME)

    df = get_as_dataframe(ws, parse_dates=True)
    df = df.dropna()
    df = pd.concat([df, links], ignore_index=True)
    df = df.drop_duplicates(subset=["link"])
    df = df.sort_values(by="type")

    print(df)

    set_with_dataframe(ws, df)
    format_with_dataframe(ws, df, include_column_header=True)
