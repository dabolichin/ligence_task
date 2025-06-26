from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


def get_project_root() -> Path:
    current_path = Path(__file__).parent
    while current_path != current_path.parent:
        if (current_path / "pyproject.toml").exists():
            return current_path
        current_path = current_path.parent
    return Path(".")


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = Field(default="Verification Service")
    DEBUG: bool = Field(default=False)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8002)

    # CORS Settings
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    # DB Settings
    DATABASE_URL: str = Field(default="sqlite:///./storage/databases/verification.db")

    # Storage Settings
    TEMP_DIR: str = Field(default="./storage/temp/verification")
    LOGS_DIR: str = Field(default="./storage/logs")
    ORIGINAL_IMAGES_DIR: str = Field(default="./storage/images/original")
    MODIFIED_IMAGES_DIR: str = Field(default="./storage/images/modified")

    # Inter-service Communication
    IMAGE_PROCESSING_SERVICE_URL: str = Field(default="http://localhost:8001")

    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default="./storage/logs/verification.log")

    # Verification Settings
    VERIFICATION_TIMEOUT: int = Field(default=60)  # 1 minute per verification
    CONCURRENT_VERIFICATION_LIMIT: int = Field(default=3)
    POLLING_INTERVAL: int = Field(default=5)  # seconds
    MAX_RETRY_ATTEMPTS: int = Field(default=3)

    # Image Processing Settings (for verification)
    MAX_FILE_SIZE: int = Field(default=100 * 1024 * 1024)  # 100MB
    ALLOWED_IMAGE_FORMATS: list[str] = Field(default=["jpeg", "png", "bmp"])

    model_config = {
        "env_file": get_project_root() / ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }

    @property
    def absolute_database_url(self) -> str:
        """Get absolute database URL based on project root."""
        if self.DATABASE_URL.startswith("sqlite:///./"):
            relative_path = self.DATABASE_URL.replace("sqlite:///./", "")
            absolute_path = get_project_root() / relative_path
            return f"sqlite:///{absolute_path}"
        return self.DATABASE_URL

    @property
    def absolute_temp_dir(self) -> str:
        """Get absolute path for temp directory."""
        return str(get_project_root() / self.TEMP_DIR)

    @property
    def absolute_logs_dir(self) -> str:
        """Get absolute path for logs directory."""
        return str(get_project_root() / self.LOGS_DIR)

    @property
    def absolute_original_images_dir(self) -> str:
        """Get absolute path for original images directory."""
        return str(get_project_root() / self.ORIGINAL_IMAGES_DIR)

    @property
    def absolute_modified_images_dir(self) -> str:
        """Get absolute path for modified images directory."""
        return str(get_project_root() / self.MODIFIED_IMAGES_DIR)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
