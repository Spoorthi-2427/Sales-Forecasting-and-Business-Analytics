import mysql.connector
from getpass import getpass

password = getpass("Enter MySQL password: ")

try:
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password=password,
        database="sales_forecasting",
        port=3306
    )

    print("SUCCESS: Python connected to MySQL!")

    connection.close()

except mysql.connector.Error as error:
    print("FAILED:", error)