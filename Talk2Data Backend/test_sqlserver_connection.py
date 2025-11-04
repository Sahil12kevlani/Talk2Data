from sqlalchemy import create_engine, text

# Your SQL Server connection URL
DATABASE_URL = "mssql+pyodbc://(localdb)\\MSSQLLocalDB/Talk2Data?driver=ODBC+Driver+17+for+SQL+Server"

# Create synchronous SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=True)

# Test the connection
try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT @@VERSION;"))
        print("✅ Connected successfully!")
        for row in result:
            print(row)
except Exception as e:
    print("❌ Connection failed:")
    print(e)
