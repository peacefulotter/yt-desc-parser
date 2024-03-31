import gspread
from gspread_dataframe import get_as_dataframe

gc = gspread.service_account(filename="creds.json")

# Open a sheet from a spreadsheet in one go
wks = gc.open("BIBLE DES CONTACTS.xlsx")
print(wks)

# df = get_as_dataframe(worksheet, parse_dates=True)

# set_with_dataframe(worksheet, df)
