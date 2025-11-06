import json, os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.utils.config import settings
from typing import Dict

# current sessionmakers
SESSIONS = {}

def build_sessions_from_dict(db_urls: Dict[str, str]):
    sessions = {}
    for name, url in db_urls.items():
        try:
            engine = create_engine(url)
            sessions[name] = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        except Exception as ex:
            print(f"[⚠️] Failed to create engine for {name}: {ex}")
    return sessions

# Initialize using settings
DATABASES = build_sessions_from_dict(settings.all_databases())

def refresh_databases():
    """Reload databases from environment (settings) at runtime."""
    global DATABASES
    try:
        # reload settings (pydantic uses env vars) — create new Settings if needed
        # easiest: call settings.all_databases() since settings reads env_file at init
        new_urls = settings.all_databases()
        new_sessions = build_sessions_from_dict(new_urls)
        # merge/replace
        DATABASES.update(new_sessions)
        print(f"[🔄] Databases refreshed. Active: {list(DATABASES.keys())}")
    except Exception as ex:
        print(f"[⚠️] refresh_databases failed: {ex}")
    return DATABASES

def get_db_session(db_name: str):
    """Session generator (yield) for a specified database."""
    if db_name not in DATABASES:
        raise ValueError(f"Database '{db_name}' not configured.")
    db = DATABASES[db_name]()
    try:
        yield db
    finally:
        db.close()
