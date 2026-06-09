import psycopg2
import os

try:
    connection = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "wazigov_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "Govan@2003"),
        port=os.getenv("DB_PORT", "5444")
    )
    cursor = connection.cursor()
    cursor.execute("SELECT version();")
    print("Successfully connected to PostgreSQL database. Version:", cursor.fetchone()[0])
    cursor.close()
    connection.close()
except Exception as error:
    print("Database connection failed:", error)
