from flask import Flask, render_template, Response, request, redirect, url_for
from werkzeug.utils import secure_filename
from getpass import getpass

import mysql.connector
import pandas as pd
import os
import csv
import io

app = Flask(__name__)

# Ask for MySQL password when running locally
password = getpass("Enter MySQL password: ")


# Database connection function
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=password,
        database=os.environ.get("DB_NAME", "sales_forecasting"),
        port=int(os.environ.get("DB_PORT", "3306"))
    )


# -----------------------------------
# 1. Dashboard Home Page
# -----------------------------------

@app.route("/")
def home():

    mydb = get_db_connection()
    cursor = mydb.cursor()

    # Dashboard statistics
    cursor.execute("""
        SELECT
            ROUND(SUM(sales), 2),
            ROUND(SUM(profit), 2),
            COUNT(DISTINCT order_id)
        FROM sales_data
    """)

    total_sales, total_profit, total_orders = cursor.fetchone()

    # Monthly sales data
    cursor.execute("""
        SELECT
            DATE_FORMAT(order_date, '%Y-%m') AS month,
            ROUND(SUM(sales), 2) AS monthly_sales
        FROM sales_data
        GROUP BY DATE_FORMAT(order_date, '%Y-%m')
        ORDER BY month
    """)

    monthly_data = cursor.fetchall()

    months = [row[0] for row in monthly_data]
    sales_values = [float(row[1]) for row in monthly_data]

    # Fetch model predictions
    cursor.execute("""
        SELECT period, method, predicted_value
        FROM forecasts
        WHERE period BETWEEN '2017-01' AND '2017-12'
        ORDER BY forecast_id
    """)

    forecast_data = cursor.fetchall()

    moving_average = {}
    linear_regression = {}

    for period, method, value in forecast_data:

        if method == "Moving Average":
            moving_average[period] = float(value)

        elif method == "Linear Regression":
            linear_regression[period] = float(value)

    # Model comparison data
    test_months = months[-12:]
    actual_sales = sales_values[-12:]

    ma_predictions = [
        moving_average.get(month)
        for month in test_months
    ]

    lr_predictions = [
        linear_regression.get(month)
        for month in test_months
    ]

    # January 2018 forecast
    forecast_value = sum(sales_values[-3:]) / 3

    # Calculate Moving Average errors
    ma_errors = [
        abs(actual - predicted)
        for actual, predicted in zip(actual_sales, ma_predictions)
        if predicted is not None
    ]

    # Calculate Linear Regression errors
    lr_errors = [
        abs(actual - predicted)
        for actual, predicted in zip(actual_sales, lr_predictions)
        if predicted is not None
    ]

    # Calculate approximate forecast range
    if ma_errors:

        average_error = sum(ma_errors) / len(ma_errors)

        lower_bound = max(0, forecast_value - average_error)
        upper_bound = forecast_value + average_error

        forecast_lower = f"{lower_bound:,.2f}"
        forecast_upper = f"{upper_bound:,.2f}"

    else:
        forecast_lower = "Not available"
        forecast_upper = "Not available"

    # Format forecast
    next_month_forecast = f"{forecast_value:,.2f}"

    # Calculate MAE
    ma_mae = (
        f"{sum(ma_errors) / len(ma_errors):,.2f}"
        if ma_errors else "Not available"
    )

    lr_mae = (
        f"{sum(lr_errors) / len(lr_errors):,.2f}"
        if lr_errors else "Not available"
    )

    # Close database connection
    cursor.close()
    mydb.close()

    # Send data to dashboard
    return render_template(
        "index.html",
        total_sales=f"{total_sales:,.2f}",
        total_profit=f"{total_profit:,.2f}",
        total_orders=total_orders,
        months=months,
        sales_values=sales_values,
        test_months=test_months,
        actual_sales=actual_sales,
        ma_predictions=ma_predictions,
        lr_predictions=lr_predictions,
        ma_mae=ma_mae,
        lr_mae=lr_mae,
        next_month_forecast=next_month_forecast,
        forecast_lower=forecast_lower,
        forecast_upper=forecast_upper
    )


# -----------------------------------
# 2. Download Forecast CSV
# -----------------------------------

@app.route("/download")
def download_forecast():

    mydb = get_db_connection()
    cursor = mydb.cursor()

    # Fetch actual monthly sales
    cursor.execute("""
        SELECT
            DATE_FORMAT(order_date, '%Y-%m') AS month,
            ROUND(SUM(sales), 2) AS actual_sales
        FROM sales_data
        WHERE order_date >= '2017-01-01'
          AND order_date < '2018-01-01'
        GROUP BY DATE_FORMAT(order_date, '%Y-%m')
        ORDER BY month
    """)

    monthly_data = cursor.fetchall()

    # Fetch predictions
    cursor.execute("""
        SELECT period, method, predicted_value
        FROM forecasts
        WHERE period BETWEEN '2017-01' AND '2017-12'
        ORDER BY forecast_id
    """)

    forecast_data = cursor.fetchall()

    cursor.close()
    mydb.close()

    # Organize predictions
    predictions = {}

    for period, method, value in forecast_data:
        predictions[(period, method)] = float(value)

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Month",
        "Actual Sales",
        "Moving Average",
        "Linear Regression"
    ])

    for month, actual in monthly_data:
        writer.writerow([
            month,
            float(actual),
            predictions.get((month, "Moving Average"), ""),
            predictions.get((month, "Linear Regression"), "")
        ])

    # Download CSV
    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=forecast_comparison_2017.csv"
        }
    )
# -----------------------------------
# 3. Upload and Manual Entry Page
# -----------------------------------
@app.route("/upload")
def upload_page():
    mydb = get_db_connection()
    cursor = mydb.cursor()

    cursor.execute("""
        SELECT id, sale_date, sales_amount
        FROM user_sales
        ORDER BY sale_date DESC, id DESC
    """)

    sales_records = cursor.fetchall()

    cursor.execute("""
        SELECT COALESCE(SUM(sales_amount), 0)
        FROM user_sales
    """)

    total_user_sales = cursor.fetchone()[0]
    cursor.execute("""
        SELECT
            DATE_FORMAT(sale_date, '%Y-%m') AS month,
            SUM(sales_amount) AS monthly_total
        FROM user_sales
        GROUP BY DATE_FORMAT(sale_date, '%Y-%m')
        ORDER BY month
    """)

    monthly_data = cursor.fetchall()

    user_months = [row[0] for row in monthly_data]
    user_sales_values = [float(row[1]) for row in monthly_data]
    cursor.close()
    mydb.close()

    return render_template(
        "upload.html",
        sales_records=sales_records,
        total_user_sales=total_user_sales,
        user_months=user_months,
        user_sales_values=user_sales_values
    )
# -----------------------------------
# 3. Run Flask Application
# -----------------------------------
@app.route("/add-sale", methods=["POST"])
def add_sale():
    sale_date = request.form.get("sale_date")
    sales_amount = request.form.get("sales_amount")

    if not sale_date or not sales_amount:
        return "Please enter both date and sales amount.", 400

    try:
        amount = float(sales_amount)

        if amount < 0:
            return "Sales amount cannot be negative.", 400

    except ValueError:
        return "Please enter a valid sales amount.", 400

    mydb = get_db_connection()
    cursor = mydb.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO user_sales (sale_date, sales_amount)
            VALUES (%s, %s)
            """,
            (sale_date, sales_amount)
        )

        mydb.commit()

    finally:
        cursor.close()
        mydb.close()

    return redirect(url_for("upload_page") + "#sales-records")
@app.route("/analyze-file", methods=["POST"])
def analyze_file():
    uploaded_file = request.files.get("sales_file")

    if not uploaded_file or not uploaded_file.filename:
        return "Please select a CSV or Excel file.", 400

    filename = secure_filename(uploaded_file.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in ("csv", "xlsx"):
        return "Only CSV and XLSX files are supported.", 400

    try:
        if extension == "csv":
            df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
        else:
            df = pd.read_excel(uploaded_file, engine="openpyxl")

        # Remove extra spaces from column names
        df.columns = df.columns.astype(str).str.strip()

        # Accept Date/Sales regardless of capitalization
        columns = {column.lower(): column for column in df.columns}

        if "date" not in columns or "sales" not in columns:
            return "Your file must contain Date and Sales columns.", 400

        df = df.rename(columns={
            columns["date"]: "Date",
            columns["sales"]: "Sales"
        })

        # Convert dates and sales amounts
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Sales"] = pd.to_numeric(df["Sales"], errors="coerce")

        # Remove invalid records
        df = df.dropna(subset=["Date", "Sales"])
        df = df[df["Sales"] >= 0]

        if df.empty:
            return "No valid sales records were found.", 400

        # Calculate summary
        total_sales = float(df["Sales"].sum())
        total_records = len(df)

        # Aggregate sales by month
        df["Month"] = df["Date"].dt.to_period("M").astype(str)

        monthly_sales = (
            df.groupby("Month")["Sales"]
            .sum()
            .sort_index()
        )

        months = monthly_sales.index.tolist()
        sales_values = [round(float(value), 2) for value in monthly_sales]

        return render_template(
            "file_results.html",
            filename=filename,
            total_sales=total_sales,
            total_records=total_records,
            months=months,
            sales_values=sales_values
        )

    except Exception:
        app.logger.exception("Failed to analyze uploaded file")
        return "Unable to read this file. Check its format and contents.", 400
@app.route("/delete-sale/<int:sale_id>", methods=["POST"])
def delete_sale(sale_id):
    mydb = get_db_connection()
    cursor = mydb.cursor()

    try:
        cursor.execute(
            "DELETE FROM user_sales WHERE id = %s",
            (sale_id,)
        )

        mydb.commit()

    finally:
        cursor.close()
        mydb.close()

    return redirect(url_for("upload_page") + "#sales-records")
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)