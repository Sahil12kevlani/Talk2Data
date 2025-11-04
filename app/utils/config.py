from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    food_db_url:str
    groq_api_key: str  #

    class Config:
        env_file = ".env"

settings = Settings()
