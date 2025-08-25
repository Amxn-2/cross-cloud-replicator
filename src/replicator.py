import time
import logging
import io
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError, NotFound
from google.api_core import retry

from .config import Config
from .exceptions import S3DownloadError, GCSUploadError, ReplicationError
from .utils import retry_with_backoff, sanitize_gcs_object_name

logger = logging.getLogger(__name__)

class CrossCloudReplicator:
    """Event-driven storage replicator for AWS S3 to Google Cloud Storage."""
    
    def __init__(self, config: Config):
        self.config = config
        self._s3_client = None
        self._gcs_client = None
        self._target_bucket = None
    
    @property
    def s3_client(self):
        """Lazy initialization of S3 client."""
        if self._s3_client is None:
            try:
                self._s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.config.aws_access_key_id,
                    aws_secret_access_key=self.config.aws_secret_access_key,
                    region_name=self.config.aws_region
                )
            except NoCredentialsError as e:
                raise ReplicationError(f"AWS credentials not configured: {e}")
        return self._s3_client
    
    @property
    def gcs_client(self):
        """Lazy initialization of GCS client."""
        if self._gcs_client is None:
            try:
                self._gcs_client = storage.Client(project=self.config.gcp_project_id)
            except Exception as e:
                raise ReplicationError(f"GCS client initialization failed: {e}")
        return self._gcs_client
    
    @property
    def target_bucket(self):
        """Get target GCS bucket."""
        if self._target_bucket is None:
            try:
                self._target_bucket = self.gcs_client.bucket(self.config.target_gcs_bucket)
            except Exception as e:
                raise ReplicationError(f"Failed to access target GCS bucket: {e}")
        return self._target_bucket
    
    def _check_file_exists_in_gcs(self, object_name: str) -> bool:
        """Check if file already exists in GCS for idempotency."""
        try:
            blob = self.target_bucket.blob(object_name)
            return blob.exists()
        except GoogleCloudError as e:
            logger.warning(f"Error checking file existence in GCS: {e}")
            return False
    
    @retry_with_backoff(max_retries=3, delay=1.0, backoff=2.0)
    def _download_from_s3(self, bucket: str, key: str) -> io.BytesIO:
        """Download file from S3 with streaming and retry logic."""
        try:
            logger.info(f"Downloading s3://{bucket}/{key}")
            
            # Get object metadata first
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            file_size = response['ContentLength']
            
            # Stream download
            s3_object = self.s3_client.get_object(Bucket=bucket, Key=key)
            stream = io.BytesIO()
            
            # Read in chunks to manage memory
            body = s3_object['Body']
            while True:
                chunk = body.read(self.config.chunk_size)
                if not chunk:
                    break
                stream.write(chunk)
            
            stream.seek(0)
            logger.info(f"Successfully downloaded {file_size} bytes from S3")
            return stream
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise S3DownloadError(f"File not found: s3://{bucket}/{key}")
            elif error_code == 'NoSuchBucket':
                raise S3DownloadError(f"Bucket not found: {bucket}")
            else:
                raise S3DownloadError(f"S3 download failed: {e}")
        except Exception as e:
            raise S3DownloadError(f"Unexpected error during S3 download: {e}")
    
    @retry_with_backoff(max_retries=3, delay=1.0, backoff=2.0)
    def _upload_to_gcs(self, stream: io.BytesIO, object_name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Upload file to GCS with retry logic."""
        try:
            logger.info(f"Uploading to gs://{self.config.target_gcs_bucket}/{object_name}")
            
            blob = self.target_bucket.blob(object_name)
            
            # Set metadata if provided
            if metadata:
                blob.metadata = metadata
            
            # Upload with retry built into the client
            stream.seek(0)
            blob.upload_from_file(
                stream,
                retry=retry.Retry(deadline=300)  # 5 minute timeout
            )
            
            logger.info(f"Successfully uploaded to GCS: {object_name}")
            
        except GoogleCloudError as e:
            raise GCSUploadError(f"GCS upload failed: {e}")
        except Exception as e:
            raise GCSUploadError(f"Unexpected error during GCS upload: {e}")
    
    def replicate(self, s3_bucket: str, s3_key: str) -> Dict[str, Any]:
        """
        Replicate a file from S3 to GCS.
        
        Args:
            s3_bucket: Source S3 bucket name
            s3_key: Source S3 object key
            
        Returns:
            Dict containing replication status and metadata
        """
        start_time = time.time()
        object_name = sanitize_gcs_object_name(s3_key)
        
        try:
            # Check idempotency - if file exists, skip replication
            if self._check_file_exists_in_gcs(object_name):
                logger.info(f"File already exists in GCS: {object_name}. Skipping replication.")
                return {
                    "status": "skipped",
                    "reason": "file_already_exists",
                    "source": f"s3://{s3_bucket}/{s3_key}",
                    "destination": f"gs://{self.config.target_gcs_bucket}/{object_name}",
                    "duration_seconds": time.time() - start_time
                }
            
            # Download from S3
            stream = self._download_from_s3(s3_bucket, s3_key)
            
            # Prepare metadata
            metadata = {
                "source_bucket": s3_bucket,
                "source_key": s3_key,
                "replication_timestamp": str(int(time.time())),
                "replicator_version": "1.0.0"
            }
            
            # Upload to GCS
            self._upload_to_gcs(stream, object_name, metadata)
            
            duration = time.time() - start_time
            
            return {
                "status": "success",
                "source": f"s3://{s3_bucket}/{s3_key}",
                "destination": f"gs://{self.config.target_gcs_bucket}/{object_name}",
                "duration_seconds": duration,
                "size_bytes": stream.getbuffer().nbytes
            }
            
        except (S3DownloadError, GCSUploadError) as e:
            logger.error(f"Replication failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "source": f"s3://{s3_bucket}/{s3_key}",
                "destination": f"gs://{self.config.target_gcs_bucket}/{object_name}",
                "duration_seconds": time.time() - start_time
            }
        except Exception as e:
            logger.error(f"Unexpected replication error: {e}")
            return {
                "status": "failed",
                "error": f"Unexpected error: {e}",
                "source": f"s3://{s3_bucket}/{s3_key}",
                "destination": f"gs://{self.config.target_gcs_bucket}/{object_name}",
                "duration_seconds": time.time() - start_time
            }
