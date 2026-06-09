import os
import urllib.parse
from sqlalchemy import create_engine, text

# 1. Grab the password you pass in the terminal
raw_password = os.getenv("DB_PASSWORD")

# 2. Safely URL-encode the special characters (like {, }, and &)
safe_password = urllib.parse.quote_plus(raw_password)

# 3. Build the connection string using the proxy port 5444
SQLALCHEMY_DATABASE_URL = f"postgresql://postgres:{safe_password}@127.0.0.1:5444/wazigov_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 4. Connect and enable PostGIS
with engine.connect() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    connection.commit()
    print("✅ PostGIS successfully enabled on Cloud SQL!")