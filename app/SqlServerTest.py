import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=(localdb)\MSSQLLocalDB;"  # e.g. localhost\SQLEXPRESS
    "DATABASE=Talk2Data;"
    "Trusted_Connection=yes;"
)

cursor = conn.cursor()
cursor.execute("SELECT @@VERSION;")
print(cursor.fetchone())
conn.close()
