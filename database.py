# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# PostgreSQL連線字串
defaultDB="Mid_Project"
dbUser="postgres"
dbPassword="pw940418"
dbHost="localhost"
dbPort=5432

SQLALCHEMY_DATABASE_URL = f"postgresql://{dbUser}:{dbPassword}@{dbHost}:{dbPort}/{defaultDB}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
