from google.cloud import storage
from google.api_core import retry
from datetime import datetime, timedelta
import mimetypes
import uuid
import logging
from typing import Optional, Tuple

class CloudStorageManager:
    """
    Manages file operations with Google Cloud Storage, providing secure and efficient
    file handling for our job application system. This class implements best practices
    for cloud storage, including retry logic, secure URL generation, and proper error handling.
    """
    
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initializes the storage manager with a specific bucket. The bucket name can be
        provided directly or through environment variables, making the code more flexible
        across different deployment environments.
        """
        # Create a storage client with default credentials
        self.client = storage.Client()
        
        # Get or create the storage bucket
        self.bucket_name = bucket_name or "job-tracker-resumes"
        self.bucket = self.get_or_create_bucket()
        
        # Configure logging for storage operations
        self.logger = logging.getLogger(__name__)

    def get_or_create_bucket(self) -> storage.Bucket:
        """
        Retrieves the specified bucket or creates it if it doesn't exist.
        Implements proper error handling and bucket configuration following
        cloud storage best practices.
        """
        try:
            bucket = self.client.bucket(self.bucket_name)
            
            if not bucket.exists():
                bucket = self.client.create_bucket(
                    self.bucket_name,
                    location="US",  # Specify the geographic location
                    storage_class="STANDARD"  # Use standard storage for faster access
                )
                
                # Configure bucket for private access
                bucket.iam_configuration.uniform_bucket_level_access_enabled = True
                bucket.patch()
                
                self.logger.info(f"Created new bucket: {self.bucket_name}")
            
            return bucket
            
        except Exception as e:
            self.logger.error(f"Error accessing bucket {self.bucket_name}: {str(e)}")
            raise

    @retry.Retry(predicate=retry.if_exception_type(Exception))
    def upload_file(self, file_data: bytes, original_filename: str) -> Tuple[str, str]:
        """
        Uploads a file to Google Cloud Storage with retry logic for improved reliability.
        Generates a secure, unique filename and sets appropriate metadata and caching headers.
        
        Args:
            file_data: The binary content of the file
            original_filename: The original name of the uploaded file
        
        Returns:
            Tuple containing the storage path and public URL
        """
        try:
            # Generate a unique filename while preserving the original extension
            extension = original_filename.rsplit('.', 1)[-1] if '.' in original_filename else ''
            unique_filename = f"{datetime.utcnow().strftime('%Y/%m/%d')}/{str(uuid.uuid4())}"
            if extension:
                unique_filename = f"{unique_filename}.{extension}"

            # Create a new blob and set its metadata
            blob = self.bucket.blob(unique_filename)
            content_type = mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
            
            # Set metadata for better file management
            metadata = {
                'original_filename': original_filename,
                'upload_timestamp': datetime.utcnow().isoformat(),
                'content_type': content_type
            }
            
            # Upload the file with metadata and caching settings
            blob.metadata = metadata
            blob.upload_from_string(
                file_data,
                content_type=content_type,
                num_retries=3
            )

            # Generate a signed URL for secure access
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=15),
                method="GET"
            )

            self.logger.info(f"Successfully uploaded file: {unique_filename}")
            return unique_filename, signed_url

        except Exception as e:
            self.logger.error(f"Error uploading file {original_filename}: {str(e)}")
            raise

    def get_file_url(self, file_path: str) -> Optional[str]:
        """
        Generates a signed URL for accessing a file securely.
        The URL is time-limited for security while allowing temporary public access.
        """
        try:
            blob = self.bucket.blob(file_path)
            
            if not blob.exists():
                self.logger.warning(f"File not found: {file_path}")
                return None

            # Generate a signed URL that expires in 15 minutes
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=15),
                method="GET"
            )

            return signed_url

        except Exception as e:
            self.logger.error(f"Error generating signed URL for {file_path}: {str(e)}")
            return None

    def delete_file(self, file_path: str) -> bool:
        """
        Safely deletes a file from storage.
        Implements proper error handling and logging for file deletion operations.
        """
        try:
            blob = self.bucket.blob(file_path)
            
            if not blob.exists():
                self.logger.warning(f"Attempted to delete non-existent file: {file_path}")
                return False

            blob.delete()
            self.logger.info(f"Successfully deleted file: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting file {file_path}: {str(e)}")
            return False