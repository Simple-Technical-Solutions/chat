from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from commons.config import DATABASE

DATABASE = "sqlite:///./chain.db"
engine = create_engine(
    DATABASE, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
print("Database opened successfully")