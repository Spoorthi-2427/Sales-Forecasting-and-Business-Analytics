
import mysql.connector
import pandas as pd
from getpass import getpass

# Connect to MySQL
password = getpass("Enter MySQL password: ")

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password=password,
    database="sales_forecasting"
)

# Fetch monthly sales data
query = """
SELECT
    DATE_FORMAT(order_date, '%Y-%m') AS month,
    ROUND(SUM(sales), 2) AS total_sales
FROM sales_data
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY month;
"""

cursor = mydb.cursor()
cursor.execute(query)

rows = cursor.fetchall()

# Convert the result into a Pandas DataFrame
df = pd.DataFrame(rows, columns=["month", "total_sales"])

# Convert sales values into numbers
df["total_sales"] = pd.to_numeric(df["total_sales"])

print(df)
print("\nTotal months:", len(df))

cursor.close()
mydb.close()
##connecting sql,python,pandas dataframe

# Moving Average Forecasting

# Predict using the previous 3 months
df["predicted_sales"] = (
    df["total_sales"]
    .shift(1)
    .rolling(window=3)
    .mean()
)

print("\nActual vs Predicted Sales:")
print(df[["month", "total_sales", "predicted_sales"]].tail(12))

# Evaluate on the last 12 months only
test_df = df.tail(12).copy()

# Calculate absolute error
test_df["absolute_error"] = abs(
    test_df["total_sales"] - test_df["predicted_sales"]
)

# Calculate Mean Absolute Error
mae = test_df["absolute_error"].mean()

print("\nMoving Average Model Evaluation")
print("Test period:", test_df["month"].iloc[0],
      "to", test_df["month"].iloc[-1])
print("MAE:", round(mae, 2))
import matplotlib.pyplot as plt

# Create graph
plt.figure(figsize=(12, 6))

# Actual sales
plt.plot(
    test_df["month"],
    test_df["total_sales"],
    marker="o",
    label="Actual Sales"
)

# Predicted sales
plt.plot(
    test_df["month"],
    test_df["predicted_sales"],
    marker="s",
    linestyle="--",
    label="Predicted Sales"
)

plt.title("Actual vs Predicted Monthly Sales (2017)")
plt.xlabel("Month")
plt.ylabel("Sales")
plt.xticks(rotation=45)
plt.legend()
plt.grid(True)

plt.tight_layout()

# Save graph
plt.savefig("sales_forecast.png")

# Display graph
#plt.show()


from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

# Assign a number to each month
df["month_number"] = range(len(df))

# Training: January 2014 to December 2016
train_df = df.iloc[:36]

# Testing: January 2017 to December 2017
test_df = df.iloc[36:].copy()

# Create Linear Regression model
model = LinearRegression()

# Train the model using historical sales
model.fit(
    train_df[["month_number"]],
    train_df["total_sales"]
)

# Predict monthly sales for 2017
test_df["linear_prediction"] = model.predict(
    test_df[["month_number"]]
)

# Calculate Mean Absolute Error
linear_mae = mean_absolute_error(
    test_df["total_sales"],
    test_df["linear_prediction"]
)

print("\nLinear Regression Model Evaluation")
print("MAE:", round(linear_mae, 2))

print("\nModel Comparison")
print("Moving Average MAE:", round(mae, 2))
print("Linear Regression MAE:", round(linear_mae, 2))



# Combined Model Comparison Graph

import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))

# Actual monthly sales
plt.plot(
    test_df["month"],
    test_df["total_sales"],
    marker="o",
    label="Actual Sales"
)

# Moving Average predictions
plt.plot(
    test_df["month"],
    test_df["predicted_sales"],
    marker="s",
    linestyle="--",
    label="Moving Average"
)

# Linear Regression predictions
plt.plot(
    test_df["month"],
    test_df["linear_prediction"],
    marker="^",
    linestyle=":",
    label="Linear Regression"
)

plt.title("Sales Forecasting: Model Comparison (2017)")
plt.xlabel("Month")
plt.ylabel("Monthly Sales")
plt.xticks(rotation=45)
plt.legend()
plt.grid(True)
plt.tight_layout()

plt.savefig("model_comparison.png")
plt.show()



# Save model predictions into MySQL

password = getpass("Enter MySQL password again: ")

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password=password,
    database="sales_forecasting"
)

cursor = mydb.cursor()

# Prepare prediction records
forecast_records = []

for _, row in test_df.iterrows():
    forecast_records.append((
        row["month"],
        "Moving Average",
        round(float(row["predicted_sales"]), 2)
    ))

    forecast_records.append((
        row["month"],
        "Linear Regression",
        round(float(row["linear_prediction"]), 2)
    ))

# Insert predictions
query = """
INSERT INTO forecasts (period, method, predicted_value)
VALUES (%s, %s, %s)
"""

try:
    cursor.executemany(query, forecast_records)
    mydb.commit()

    print("\nForecasts saved successfully!")
    print("Records inserted:", cursor.rowcount)

except mysql.connector.Error as error:
    mydb.rollback()
    print("Error saving forecasts:", error)

finally:
    cursor.close()
    mydb.close()
