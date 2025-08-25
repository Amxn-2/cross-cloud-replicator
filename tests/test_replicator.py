import pytest
import io
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from google.cloud.exceptions import NotFound

from src.config import Config
from src.replicator import CrossCloudReplicator
from src.exceptions import S3DownloadError, GCSUploadError

@pytest.fixture
def config():
    return Config(
        aws_access_key_id="test_key",
        aws_secret_access_key="test_secret",
        target_gcs_bucket="test-bucket"
    )

@pytest.fixture
def replicator(config):
    return CrossCloudReplicator(config)

class TestCrossCloudReplicator:
    
    @patch('src.replicator.boto3.client')
    def test_s3_client_initialization(self, mock_boto3, replicator):
        """Test S3 client lazy initialization."""
        mock_client = Mock()
        mock_boto3.return_value = mock_client
        
        assert replicator.s3_client == mock_client
        mock_boto3.assert_called_once_with(
            's3',
            aws_access_key_id="test_key",
            aws_secret_access_key="test_secret",
            region_name="us-east-1"
        )
    
    @patch('src.replicator.storage.Client')
    def test_gcs_client_initialization(self, mock_storage, replicator):
        """Test GCS client lazy initialization."""
        mock_client = Mock()
        mock_storage.return_value = mock_client
        
        assert replicator.gcs_client == mock_client
    
    def test_check_file_exists_in_gcs_true(self, replicator):
        """Test file existence check returns True."""
        mock_blob = Mock()
        mock_blob.exists.return_value = True
        
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        replicator._target_bucket = mock_bucket
        
        assert replicator._check_file_exists_in_gcs("test.csv") is True
        mock_bucket.blob.assert_called_once_with("test.csv")
        mock_blob.exists.assert_called_once()
    
    def test_download_from_s3_success(self, replicator):
        """Test successful S3 download."""
        mock_s3 = Mock()
        mock_s3.head_object.return_value = {'ContentLength': 1000}
        
        mock_body = Mock()
        mock_body.read.side_effect = [b"test data", b""]
        mock_s3.get_object.return_value = {'Body': mock_body}
        
        replicator._s3_client = mock_s3
        
        result = replicator._download_from_s3("bucket", "key")
        
        assert isinstance(result, io.BytesIO)
        assert result.read() == b"test data"
    
    def test_download_from_s3_not_found(self, replicator):
        """Test S3 download with file not found."""
        mock_s3 = Mock()
        error_response = {'Error': {'Code': 'NoSuchKey'}}
        mock_s3.head_object.side_effect = ClientError(error_response, 'HeadObject')
        
        replicator._s3_client = mock_s3
        
        with pytest.raises(S3DownloadError, match="File not found"):
            replicator._download_from_s3("bucket", "key")
    
    def test_upload_to_gcs_success(self, replicator):
        """Test successful GCS upload."""
        mock_blob = Mock()
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        replicator._target_bucket = mock_bucket
        
        stream = io.BytesIO(b"test data")
        replicator._upload_to_gcs(stream, "test.csv")
        
        mock_bucket.blob.assert_called_once_with("test.csv")
        mock_blob.upload_from_file.assert_called_once()
    
    def test_replicate_success(self, replicator):
        """Test successful replication."""
        # Mock file doesn't exist
        replicator._check_file_exists_in_gcs = Mock(return_value=False)
        
        # Mock successful download
        stream = io.BytesIO(b"test data")
        replicator._download_from_s3 = Mock(return_value=stream)
        
        # Mock successful upload
        replicator._upload_to_gcs = Mock()
        
        result = replicator.replicate("test-bucket", "test.csv")
        
        assert result["status"] == "success"
        assert "test-bucket" in result["source"]
        assert "test.csv" in result["source"]
    
    def test_replicate_idempotent_skip(self, replicator):
        """Test replication skips existing files."""
        replicator._check_file_exists_in_gcs = Mock(return_value=True)
        
        result = replicator.replicate("test-bucket", "test.csv")
        
        assert result["status"] == "skipped"
        assert result["reason"] == "file_already_exists"
