class ReplicationError(Exception):
    """Base exception for replication errors."""
    pass

class S3DownloadError(ReplicationError):
    """Raised when S3 download fails."""
    pass

class GCSUploadError(ReplicationError):
    """Raised when GCS upload fails."""
    pass

class ValidationError(ReplicationError):
    """Raised when input validation fails."""
    pass

class ConfigurationError(ReplicationError):
    """Raised when configuration is invalid."""
    pass
