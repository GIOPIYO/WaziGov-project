import os
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Grab the raw password from the environment variable
raw_password = os.getenv("DB_PASSWORD")

# 2. Safely URL-encode the special characters 
safe_password = urllib.parse.quote_plus(raw_password)

# 3. Build the connection string
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:%7BO%7DbZy%26EQkVk0Lka@127.0.0.1:5444/wazigov_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()