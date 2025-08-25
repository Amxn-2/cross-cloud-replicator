import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    # AWS Configuration
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    
    # GCP Configuration
    gcp_credentials_path: Optional[str] = None
    gcp_project_id: str = ""
    target_gcs_bucket: str = ""
    
    # Service Configuration
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    
    # Retry Configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    
    # Streaming Configuration
    chunk_size: int = 8192  # 8KB chunks
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables."""
        return cls(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            gcp_credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            gcp_project_id=os.getenv("GCP_PROJECT_ID", ""),
            target_gcs_bucket=os.getenv("TARGET_GCS_BUCKET", ""),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8080")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("RETRY_DELAY", "1.0")),
            retry_backoff=float(os.getenv("RETRY_BACKOFF", "2.0")),
            chunk_size=int(os.getenv("CHUNK_SIZE", "8192"))
        )
    
    def validate(self) -> None:
        """Validate required configuration."""
        required_fields = [
            ("aws_access_key_id", self.aws_access_key_id),
            ("aws_secret_access_key", self.aws_secret_access_key),
            ("target_gcs_bucket", self.target_gcs_bucket)
        ]
        
        missing_fields = [name for name, value in required_fields if not value]
        if missing_fields:
            raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")
