"""
Supabase Storage and PostgreSQL Access Control Manager
Provides file upload, download, deletion, and permission management functionality.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self):
        """Initialize Supabase client with environment variables."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("Supabase client initialized successfully")
    
    def create_storage_bucket(self, bucket_name: str, public: bool = False) -> bool:
        """
        Create a storage bucket if it doesn't exist.
        
        Args:
            bucket_name (str): Name of the bucket to create
            public (bool): Whether the bucket should be public
            
        Returns:
            bool: True if bucket was created or already exists, False otherwise
        """
        try:
            # Check if bucket already exists
            buckets = self.supabase.storage.list_buckets()
            existing_buckets = [bucket.name for bucket in buckets]
            
            if bucket_name in existing_buckets:
                logger.info(f"Bucket '{bucket_name}' already exists")
                return True
            
            # Create the bucket
            result = self.supabase.storage.create_bucket(bucket_name, {'public': public})
            logger.info(f"Successfully created bucket '{bucket_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error creating bucket '{bucket_name}': {str(e)}")
            return False
    
    def upload_file(self, user_id: str, local_path: str, bucket_name: str, 
                   remote_filename: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Upload a file to Supabase storage and record metadata in database.
        
        Args:
            user_id (str): UUID of the user uploading the file
            local_path (str): Path to the local file
            bucket_name (str): Name of the storage bucket
            remote_filename (str, optional): Custom filename for storage
            
        Returns:
            Dict[str, Any]: File metadata if successful, None otherwise
        """
        try:
            # Validate local file exists
            if not os.path.exists(local_path):
                logger.error(f"Local file does not exist: {local_path}")
                return None
            
            # Get file info
            file_path = Path(local_path)
            filename = remote_filename or file_path.name
            file_size = file_path.stat().st_size
            
            # Determine content type
            content_type = self._get_content_type(filename)
            
            # Create unique filepath to avoid collisions
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            storage_path = f"{user_id}/{timestamp}_{filename}"
            
            # Upload file to Supabase storage
            with open(local_path, 'rb') as file:
                result = self.supabase.storage.from_(bucket_name).upload(
                    storage_path, 
                    file,
                    file_options={"content-type": content_type}
                )
            
            # Insert file metadata into database
            file_data = {
                'user_id': user_id,
                'filename': filename,
                'filepath': storage_path,
                'file_size': file_size,
                'content_type': content_type
            }
            
            db_result = self.supabase.table('files').insert(file_data).execute()
            
            if not db_result.data:
                logger.error("Failed to insert file metadata into database")
                return None
            
            file_record = db_result.data[0]
            file_id = file_record['id']
            
            # Grant owner permissions to the uploader
            permission_data = {
                'file_id': file_id,
                'user_id': user_id,
                'access_level': 'owner',
                'granted_by': user_id
            }
            
            perm_result = self.supabase.table('file_permissions').insert(permission_data).execute()
            
            if not perm_result.data:
                logger.error("Failed to grant owner permissions")
                return None
            
            logger.info(f"Successfully uploaded file '{filename}' with ID: {file_id}")
            return file_record
            
        except Exception as e:
            logger.error(f"Error uploading file '{local_path}': {str(e)}")
            return None
    
    def fetch_file(self, user_id: str, file_id: str, bucket_name: str) -> Optional[str]:
        """
        Fetch file download URL if user has read access or higher.
        
        Args:
            user_id (str): UUID of the user requesting the file
            file_id (str): UUID of the file
            bucket_name (str): Name of the storage bucket
            
        Returns:
            str: Signed download URL if successful, None otherwise
        """
        try:
            # Check user access
            access_level = self.check_access(user_id, file_id)
            if not access_level:
                logger.warning(f"User {user_id} has no access to file {file_id}")
                return None
            
            # Get file metadata
            file_result = self.supabase.table('files').select('*').eq('id', file_id).execute()
            
            if not file_result.data:
                logger.error(f"File {file_id} not found")
                return None
            
            file_record = file_result.data[0]
            filepath = file_record['filepath']
            
            # Generate signed URL (valid for 1 hour)
            signed_url = self.supabase.storage.from_(bucket_name).create_signed_url(
                filepath, 3600  # 1 hour expiry
            )
            
            logger.info(f"Generated download URL for file {file_id}")
            return signed_url['signedURL']
            
        except Exception as e:
            logger.error(f"Error fetching file {file_id}: {str(e)}")
            return None
    
    def delete_file(self, user_id: str, file_id: str, bucket_name: str) -> bool:
        """
        Delete a file from storage and database (owner access required).
        
        Args:
            user_id (str): UUID of the user requesting deletion
            file_id (str): UUID of the file to delete
            bucket_name (str): Name of the storage bucket
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if user is owner
            access_level = self.check_access(user_id, file_id)
            if access_level != 'owner':
                logger.warning(f"User {user_id} is not owner of file {file_id}")
                return False
            
            # Get file metadata
            file_result = self.supabase.table('files').select('*').eq('id', file_id).execute()
            
            if not file_result.data:
                logger.error(f"File {file_id} not found")
                return False
            
            file_record = file_result.data[0]
            filepath = file_record['filepath']
            
            # Delete file from storage
            storage_result = self.supabase.storage.from_(bucket_name).remove([filepath])
            
            # Delete file permissions (will cascade delete due to foreign key)
            perm_result = self.supabase.table('file_permissions').delete().eq('file_id', file_id).execute()
            
            # Delete file record
            file_delete_result = self.supabase.table('files').delete().eq('id', file_id).execute()
            
            logger.info(f"Successfully deleted file {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            return False
    
    def check_access(self, user_id: str, file_id: str) -> Optional[str]:
        """
        Check user's access level for a specific file.
        
        Args:
            user_id (str): UUID of the user
            file_id (str): UUID of the file
            
        Returns:
            str: Access level ('read', 'write', 'owner') or None if no access
        """
        try:
            result = self.supabase.table('file_permissions').select('access_level').eq(
                'user_id', user_id
            ).eq('file_id', file_id).execute()
            
            if result.data:
                access_level = result.data[0]['access_level']
                logger.info(f"User {user_id} has '{access_level}' access to file {file_id}")
                return access_level
            else:
                logger.info(f"User {user_id} has no access to file {file_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error checking access for user {user_id}, file {file_id}: {str(e)}")
            return None
    
    def grant_access(self, owner_user_id: str, file_id: str, target_user_id: str, 
                    access_level: str) -> bool:
        """
        Grant access to a file (owner only).
        
        Args:
            owner_user_id (str): UUID of the file owner
            file_id (str): UUID of the file
            target_user_id (str): UUID of the user to grant access to
            access_level (str): Access level to grant ('read', 'write')
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if granter is owner
            granter_access = self.check_access(owner_user_id, file_id)
            if granter_access != 'owner':
                logger.warning(f"User {owner_user_id} is not owner of file {file_id}")
                return False
            
            # Validate access level
            if access_level not in ['read', 'write']:
                logger.error(f"Invalid access level: {access_level}")
                return False
            
            # Insert or update permission
            permission_data = {
                'file_id': file_id,
                'user_id': target_user_id,
                'access_level': access_level,
                'granted_by': owner_user_id
            }
            
            result = self.supabase.table('file_permissions').upsert(permission_data).execute()
            
            if result.data:
                logger.info(f"Granted '{access_level}' access to user {target_user_id} for file {file_id}")
                return True
            else:
                logger.error("Failed to grant access")
                return False
                
        except Exception as e:
            logger.error(f"Error granting access: {str(e)}")
            return False
    
    def list_user_files(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all files accessible to a user.
        
        Args:
            user_id (str): UUID of the user
            
        Returns:
            List[Dict[str, Any]]: List of accessible files with metadata
        """
        try:
            result = self.supabase.table('files').select(
                'id, filename, file_size, content_type, created_at, '
                'file_permissions!inner(access_level)'
            ).eq('file_permissions.user_id', user_id).execute()
            
            files = []
            for file_record in result.data:
                file_info = {
                    'id': file_record['id'],
                    'filename': file_record['filename'],
                    'file_size': file_record['file_size'],
                    'content_type': file_record['content_type'],
                    'created_at': file_record['created_at'],
                    'access_level': file_record['file_permissions'][0]['access_level']
                }
                files.append(file_info)
            
            logger.info(f"Found {len(files)} accessible files for user {user_id}")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files for user {user_id}: {str(e)}")
            return []
    
    def _get_content_type(self, filename: str) -> str:
        """Determine content type based on file extension."""
        extension = Path(filename).suffix.lower()
        content_types = {
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }
        return content_types.get(extension, 'application/octet-stream')