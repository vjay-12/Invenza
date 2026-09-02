import os
from typing import List
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Automatically load .env from current dir or parent dir
backend_env = Path(__file__).resolve().parent.parent.parent / ".env"
root_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if backend_env.exists():
    load_dotenv(dotenv_path=backend_env)
elif root_env.exists():
    load_dotenv(dotenv_path=root_env)
else:
    load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Invenza API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "invenza-super-secret-key-production-change-this-2026")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # PostgreSQL async database URI
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgrespassword2026")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "invenza_db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5434")
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis Cache & Background Tasks
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6380/0")

    # Qdrant Vector Search
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))

    # MinIO / S3 Object Storage
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9002")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ROOT_USER", "invenza_minio_admin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_ROOT_PASSWORD", "invenza_minio_secret_password")
    
    # CORS origins (allow development across localhost, 127.0.0.1, and LAN IPs like 192.168.x.x)
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]
    
    # AI & LLM settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    class Config:
        case_sensitive = True

settings = Settings()
