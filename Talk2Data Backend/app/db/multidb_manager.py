from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.utils.config import settings

# Define multiple database engines

DATABASES = {
    "talk2data": settings.database_url,
}

if settings.food_db_url:
    DATABASES["fooddb"] = settings.food_db_url

# Create session factories for each
ENGINES = {name: create_engine(url) for name, url in DATABASES.items()}
SESSIONS = {name: sessionmaker(autocommit=False, autoflush=False, bind=engine) for name, engine in ENGINES.items()}

def get_db_session(db_name: str):
    """Get a SQLAlchemy session for a specific database."""
    if db_name not in SESSIONS:
        raise ValueError(f"Unknown database: {db_name}")
    db = SESSIONS[db_name]()
    try:
        yield db
    finally:
        db.close()
