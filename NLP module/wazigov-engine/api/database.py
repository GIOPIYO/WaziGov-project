import os
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Check if running in the cloud or locally
if os.getenv("K_SERVICE"):
    # PRODUCTION CONNECTION (Cloud Run uses native Unix Sockets)
    DB_USER = "postgres"
    DB_PASS = os.getenv("DB_PASSWORD", "{O}bZy&EQkVk0Lka")
    DB_NAME = "wazigov_db"
    INSTANCE_CONNECTION = "wazigov:us-central1:govan"
    
    safe_password = urllib.parse.quote_plus(DB_PASS)
    # Cloud Run natively maps databases to the /cloudsql directory
    SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{safe_password}@/{DB_NAME}?host=/cloudsql/{INSTANCE_CONNECTION}"
else:
    # LOCAL DEVELOPMENT CONNECTION (Your local proxy tunnel setup)
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