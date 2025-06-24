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
    APP_NAME: str = Field(default="Image Processing Service")
    DEBUG: bool = Field(default=False)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8001)

    # CORS Settings
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    # DB Settings
    DATABASE_URL: str = Field(
        default="sqlite:///./storage/databases/image_processing.db"
    )

    # Storage Settings
    ORIGINAL_IMAGES_DIR: str = Field(default="./storage/images/original")
    MODIFIED_IMAGES_DIR: str = Field(default="./storage/images/modified")
    TEMP_DIR: str = Field(default="./storage/temp")

    # Image Processing Settings
    MAX_FILE_SIZE: int = Field(default=100 * 1024 * 1024)  # 100MB
    ALLOWED_IMAGE_FORMATS: list[str] = Field(default=["jpeg", "png", "bmp"])
    VARIANTS_COUNT: int = Field(default=100)
    MIN_MODIFICATIONS_PER_VARIANT: int = Field(default=100)

    # Inter-service Communication
    VERIFICATION_SERVICE_URL: str = Field(default="http://localhost:8002")

    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default="./logs/image_processing.log")

    # Processing Settings
    PROCESSING_TIMEOUT: int = Field(default=300)  # 5 minutes
    CONCURRENT_PROCESSING_LIMIT: int = Field(default=5)

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
    def absolute_original_images_dir(self) -> str:
        """Get absolute path for original images directory."""
        return str(get_project_root() / self.ORIGINAL_IMAGES_DIR)

    @property
    def absolute_modified_images_dir(self) -> str:
        """Get absolute path for modified images directory."""
        return str(get_project_root() / self.MODIFIED_IMAGES_DIR)

    @property
    def absolute_temp_dir(self) -> str:
        """Get absolute path for temp directory."""
        return str(get_project_root() / self.TEMP_DIR)

    def model_post_init(self, __context) -> None:
        self._ensure_directories()

    def _ensure_directories(self):
        project_root = get_project_root()
        directories = [
            project_root / self.ORIGINAL_IMAGES_DIR,
            project_root / self.MODIFIED_IMAGES_DIR,
            project_root / self.TEMP_DIR,
            project_root / Path(self.LOG_FILE).parent,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
