import pandas as pd

# Read the CSV file
df = pd.read_csv(
    "data/Sample - Superstore.csv",
    encoding="cp1252"
)

# Convert column names
df.columns = [
    col.strip().lower().replace(" ", "_").replace("-", "_")
    for col in df.columns
]

# Convert dates
df["order_date"] = pd.to_datetime(
    df["order_date"],
    format="%m/%d/%Y"
)

df["ship_date"] = pd.to_datetime(
    df["ship_date"],
    format="%m/%d/%Y"
)

# Display results
print(df[["order_date", "ship_date"]].head())

print("\nUpdated column names:")
print(df.columns)

print("\nTotal rows:", len(df))

import mysql.connector
from getpass import getpass

# Step 1: Connect to MySQL
password = getpass("Enter MySQL password: ")

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password=password,
    database="sales_forecasting"
)

cursor = mydb.cursor()

# Step 2: Prepare SQL query
columns = ", ".join(df.columns)
placeholders = ", ".join(["%s"] * len(df.columns))

query = f"""
INSERT INTO sales_data ({columns})
VALUES ({placeholders})
"""

# Step 3: Convert DataFrame into records
records = []

for row in df.itertuples(index=False, name=None):
    converted_row = []

    for value in row:
        if isinstance(value, pd.Timestamp):
            converted_row.append(value.date())
        elif hasattr(value, "item"):
            converted_row.append(value.item())
        else:
            converted_row.append(value)

    records.append(tuple(converted_row))

# Step 4: Insert records into MySQL
try:
    cursor.executemany(query, records)
    mydb.commit()

    print("\nData imported successfully!")
    print("Rows inserted:", cursor.rowcount)

except mysql.connector.Error as error:
    mydb.rollback()
    print("Import failed:", error)

finally:
    cursor.close()
    mydb.close()