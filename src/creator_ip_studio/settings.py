from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CREATOR_IP_", env_file=".env", extra="ignore")

    workspace: Path = Path("workspace")
    artifact_root: Path = Path("workspace/projects")
    database_url: str = "sqlite:///./creator-ip-studio.db"
    api_url: str = "http://127.0.0.1:8080"
    worker_token: str = "local-development"
    worker_capabilities: str = "cpu,ffmpeg"
    lease_seconds: int = 300


settings = Settings()

