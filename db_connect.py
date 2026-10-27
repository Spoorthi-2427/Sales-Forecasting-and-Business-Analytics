
import mysql.connector
from getpass import getpass

password = getpass("Enter MySQL password: ")

try:
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password=password,
        database="sales_forecasting"
    )
   

    if mydb.is_connected():
        print("Successfully connected to MySQL!")

    mydb.close()

except mysql.connector.Error as error:
    print("Connection failed:", error)
