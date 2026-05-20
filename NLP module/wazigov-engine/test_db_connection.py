import psycopg2

try:
    connection = psycopg2.connect(
        host="localhost",
        database="wazigov_db",
        user="postgres",
        password="Govan@2003",
        port="5433"
    )
    cursor = connection.cursor()
    cursor.execute("SELECT PostGIS_Version();")
    print("Successfully connected to Docker PostGIS. Version:", cursor.fetchone()[0])
    cursor.close()
    connection.close()
except Exception as error:
    print("Database connection failed:", error)
