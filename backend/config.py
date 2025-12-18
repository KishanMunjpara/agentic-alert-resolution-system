import os
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import List

# Get the directory where this config file is located
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file in the backend directory
# override=True ensures .env file values take precedence over system env vars
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path, override=True)

class Config:
    """Application Configuration"""
    
    # Neo4j Configuration
    NEO4J_URI: str = os.getenv("NEO4J_URI", "neo4j://localhost:7687").strip()
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j").strip()
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password").strip()
    NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j").strip()
    NEO4J_MAX_POOL_SIZE: int = int(os.getenv("NEO4J_MAX_POOL_SIZE", 20))
    NEO4J_CONNECTION_TIMEOUT: int = int(os.getenv("NEO4J_CONNECTION_TIMEOUT", 30))
    
    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", 24))
    JWT_REFRESH_EXPIRATION_DAYS: int = int(os.getenv("JWT_REFRESH_EXPIRATION_DAYS", 7))
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", 8000))
    API_DEBUG: bool = os.getenv("API_DEBUG", "true").lower() == "true"
    API_RELOAD: bool = os.getenv("API_RELOAD", "true").lower() == "true"
    
    # CORS Configuration - Parse from env or use defaults
    _cors_origins_env = os.getenv("CORS_ORIGINS", "")
    if _cors_origins_env:
        try:
            # Try to parse as JSON array
            _parsed_origins = json.loads(_cors_origins_env)
        except json.JSONDecodeError:
            # Fallback to comma-separated string
            _parsed_origins = [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]
    else:
        _parsed_origins = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173"
        ]
    
    CORS_ORIGINS: List[str] = _parsed_origins
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/agentic_alerts.log")
    
    # Investigation Timeout
    INVESTIGATION_TIMEOUT_SECONDS: int = int(os.getenv("INVESTIGATION_TIMEOUT_SECONDS", 30))
    
    # Agents Configuration
    AGENT_TIMEOUT_SECONDS: int = int(os.getenv("AGENT_TIMEOUT_SECONDS", 15))
    AGENT_ENABLE_LOGGING: bool = os.getenv("AGENT_ENABLE_LOGGING", "true").lower() == "true"
    
    @classmethod
    def from_env(cls):
        """Create config from environment"""
        return cls()


# Global config instance
config = Config.from_env()

