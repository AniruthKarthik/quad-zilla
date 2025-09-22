"""
Combined Storage Management System for Supabase
Provides complete file storage, database management, and access control functionality.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "YOUR_SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "YOUR_SUPABASE_KEY")
    
    # File upload settings
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set = {
        '.txt', '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', 
        '.mp3', '.wav', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.csv'
    }
    
    # Default bucket names
    DEFAULT_BUCKET: str = "user-files"
    PUBLIC_BUCKET: str = "public-files"

settings = Settings()

# =============================================================================
# DATABASE CONNECTION
# =============================================================================

# Initialize Supabase client
try:
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    logger.info("Successfully connected to Supabase")
except Exception as e:
    logger.error(f"Failed to connect to Supabase: {str(e)}")
    raise

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class FileUploadResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    content_type: str
    filepath: str
    created_at: str

class FileListResponse(BaseModel):
    files: List[Dict[str, Any]]
    total_count: int
    page: int
    per_page: int
    total_pages: int

class AccessGrantRequest(BaseModel):
    target_user_id: str = Field(..., description="User ID to grant access to")
    access_level: str = Field(..., description="Access level: 'read' or 'write'")

class FilePermissionResponse(BaseModel):
    file_id: str
    user_id: str
    access_level: str
    granted_by: str
    created_at: str

class BucketCreateRequest(BaseModel):
    bucket_name: str = Field(..., description="Name of the bucket to create")
    public: bool = Field(default=False, description="Whether the bucket should be public")

# =============================================================================
# DATABASE SCHEMA SETUP
# =============================================================================

def create_tables():
    """
    Create necessary tables if they don't exist
    Note: This should ideally be done through Supabase SQL editor or migrations
    """
    
    # Users table schema
    users_table_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
        username VARCHAR(30) UNIQUE NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        last_login TIMESTAMP WITH TIME ZONE
    );
    
    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
    """
    
    # Files table schema
    files_table_sql = """
    CREATE TABLE IF NOT EXISTS files (
        id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        filename VARCHAR(255) NOT NULL,
        filepath TEXT NOT NULL UNIQUE,
        file_size BIGINT NOT NULL,
        content_type VARCHAR(100),
        bucket_name VARCHAR(100) DEFAULT 'user-files',
        is_public BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id);
    CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at);
    CREATE INDEX IF NOT EXISTS idx_files_bucket ON files(bucket_name);
    CREATE INDEX IF NOT EXISTS idx_files_public ON files(is_public);
    """
    
    # File permissions table schema
    file_permissions_table_sql = """
    CREATE TABLE IF NOT EXISTS file_permissions (
        id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
        file_id UUID REFERENCES files(id) ON DELETE CASCADE,
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        access_level VARCHAR(20) NOT NULL CHECK (access_level IN ('read', 'write', 'owner')),
        granted_by UUID REFERENCES users(id) ON DELETE SET NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        
        -- Ensure unique permission per user per file
        UNIQUE(file_id, user_id)
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_file_permissions_file_id ON file_permissions(file_id);
    CREATE INDEX IF NOT EXISTS idx_file_permissions_user_id ON file_permissions(user_id);
    CREATE INDEX IF NOT EXISTS idx_file_permissions_access_level ON file_permissions(access_level);
    """
    
    # File access logs table
    file_access_logs_table_sql = """
    CREATE TABLE IF NOT EXISTS file_access_logs (
        id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
        file_id UUID REFERENCES files(id) ON DELETE CASCADE,
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        action VARCHAR(50) NOT NULL,
        ip_address INET,
        user_agent TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_file_access_logs_file_id ON file_access_logs(file_id);
    CREATE INDEX IF NOT EXISTS idx_file_access_logs_user_id ON file_access_logs(user_id);
    CREATE INDEX IF NOT EXISTS idx_file_access_logs_created_at ON file_access_logs(created_at);
    CREATE INDEX IF NOT EXISTS idx_file_access_logs_action ON file_access_logs(action);
    """
    
    try:
        logger.info("Database tables schema defined. Run via Supabase SQL editor.")
        return {
            "users_table": users_table_sql,
            "files_table": files_table_sql,
            "file_permissions_table": file_permissions_table_sql,
            "file_access_logs_table": file_access_logs_table_sql
        }
    except Exception as e:
        logger.error(f"Error with database schema: {str(e)}")
        raise

# =============================================================================
# STORAGE MANAGER CLASS
# =============================================================================

class StorageManager:
    def __init__(self):
        """Initialize Storage Manager with Supabase client."""
        self.supabase = supabase
        logger.info("Storage Manager initialized successfully")
    
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
    
    def upload_file(self, user_id: str, file_content: bytes, filename: str, 
                   bucket_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Upload a file to Supabase storage and record metadata in database.
        
        Args:
            user_id (str): UUID of the user uploading the file
            file_content (bytes): File content as bytes
            filename (str): Original filename
            bucket_name (str, optional): Name of the storage bucket
            
        Returns:
            Dict[str, Any]: File metadata if successful, None otherwise
        """
        try:
            bucket_name = bucket_name or settings.DEFAULT_BUCKET
            
            # Validate file extension
            file_path = Path(filename)
            if file_path.suffix.lower() not in settings.ALLOWED_EXTENSIONS:
                logger.error(f"File extension not allowed: {file_path.suffix}")
                return None
            
            # Validate file size
            file_size = len(file_content)
            if file_size > settings.MAX_FILE_SIZE:
                logger.error(f"File size exceeds limit: {file_size} bytes")
                return None
            
            # Determine content type
            content_type = self._get_content_type(filename)
            
            # Create unique filepath to avoid collisions
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            storage_path = f"{user_id}/{timestamp}_{filename}"
            
            # Upload file to Supabase storage
            result = self.supabase.storage.from_(bucket_name).upload(
                storage_path, 
                file_content,
                file_options={"content-type": content_type}
            )
            
            # Insert file metadata into database
            file_data = {
                'user_id': user_id,
                'filename': filename,
                'filepath': storage_path,
                'file_size': file_size,
                'content_type': content_type,
                'bucket_name': bucket_name
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
            
            # Log the upload action
            self._log_file_access(file_id, user_id, 'upload')
            
            logger.info(f"Successfully uploaded file '{filename}' with ID: {file_id}")
            return file_record
            
        except Exception as e:
            logger.error(f"Error uploading file '{filename}': {str(e)}")
            return None
    
    def fetch_file(self, user_id: str, file_id: str) -> Optional[str]:
        """
        Fetch file download URL if user has read access or higher.
        
        Args:
            user_id (str): UUID of the user requesting the file
            file_id (str): UUID of the file
            
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
            bucket_name = file_record['bucket_name']
            
            # Generate signed URL (valid for 1 hour)
            signed_url = self.supabase.storage.from_(bucket_name).create_signed_url(
                filepath, 3600  # 1 hour expiry
            )
            
            # Log the download action
            self._log_file_access(file_id, user_id, 'download')
            
            logger.info(f"Generated download URL for file {file_id}")
            return signed_url['signedURL']
            
        except Exception as e:
            logger.error(f"Error fetching file {file_id}: {str(e)}")
            return None
    
    def delete_file(self, user_id: str, file_id: str) -> bool:
        """
        Delete a file from storage and database (owner access required).
        
        Args:
            user_id (str): UUID of the user requesting deletion
            file_id (str): UUID of the file to delete
            
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
            bucket_name = file_record['bucket_name']
            
            # Delete file from storage
            storage_result = self.supabase.storage.from_(bucket_name).remove([filepath])
            
            # Log the delete action
            self._log_file_access(file_id, user_id, 'delete')
            
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
                # Log the share action
                self._log_file_access(file_id, owner_user_id, 'share')
                logger.info(f"Granted '{access_level}' access to user {target_user_id} for file {file_id}")
                return True
            else:
                logger.error("Failed to grant access")
                return False
                
        except Exception as e:
            logger.error(f"Error granting access: {str(e)}")
            return False
    
    def list_user_files(self, user_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        List all files accessible to a user with pagination.
        
        Args:
            user_id (str): UUID of the user
            page (int): Page number (starts from 1)
            per_page (int): Number of files per page
            
        Returns:
            Dict[str, Any]: Dictionary containing files list and pagination info
        """
        try:
            offset = (page - 1) * per_page
            
            result = self.supabase.table('files').select(
                'id, filename, file_size, content_type, created_at, bucket_name, '
                'file_permissions!inner(access_level)'
            ).eq('file_permissions.user_id', user_id).range(offset, offset + per_page - 1).execute()
            
            # Get total count
            count_result = self.supabase.table('files').select(
                'id', count='exact'
            ).eq('file_permissions.user_id', user_id).execute()
            
            total_count = count_result.count if count_result.count else 0
            
            files = []
            for file_record in result.data:
                file_info = {
                    'id': file_record['id'],
                    'filename': file_record['filename'],
                    'file_size': file_record['file_size'],
                    'content_type': file_record['content_type'],
                    'created_at': file_record['created_at'],
                    'bucket_name': file_record['bucket_name'],
                    'access_level': file_record['file_permissions'][0]['access_level']
                }
                files.append(file_info)
            
            logger.info(f"Found {len(files)} files on page {page} for user {user_id}")
            return {
                'files': files,
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': (total_count + per_page - 1) // per_page
            }
            
        except Exception as e:
            logger.error(f"Error listing files for user {user_id}: {str(e)}")
            return {'files': [], 'total_count': 0, 'page': page, 'per_page': per_page, 'total_pages': 0}
    
    def get_file_info(self, user_id: str, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific file.
        
        Args:
            user_id (str): UUID of the user requesting info
            file_id (str): UUID of the file
            
        Returns:
            Dict[str, Any]: File information if accessible, None otherwise
        """
        try:
            # Check user access
            access_level = self.check_access(user_id, file_id)
            if not access_level:
                logger.warning(f"User {user_id} has no access to file {file_id}")
                return None
            
            # Get file details with permissions
            result = self.supabase.table('files').select(
                'id, filename, file_size, content_type, created_at, updated_at, bucket_name, '
                'file_permissions(access_level, granted_by, created_at, users(username))'
            ).eq('id', file_id).execute()
            
            if not result.data:
                logger.error(f"File {file_id} not found")
                return None
            
            file_record = result.data[0]
            
            return {
                'id': file_record['id'],
                'filename': file_record['filename'],
                'file_size': file_record['file_size'],
                'content_type': file_record['content_type'],
                'created_at': file_record['created_at'],
                'updated_at': file_record['updated_at'],
                'bucket_name': file_record['bucket_name'],
                'user_access_level': access_level,
                'permissions': file_record['file_permissions']
            }
            
        except Exception as e:
            logger.error(f"Error getting file info for {file_id}: {str(e)}")
            return None
    
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
            '.csv': 'text/csv',
            '.zip': 'application/zip'
        }
        return content_types.get(extension, 'application/octet-stream')
    
    def _log_file_access(self, file_id: str, user_id: str, action: str, ip_address: str = None, user_agent: str = None):
        """Log file access for auditing purposes."""
        try:
            log_data = {
                'file_id': file_id,
                'user_id': user_id,
                'action': action,
                'ip_address': ip_address,
                'user_agent': user_agent
            }
            
            self.supabase.table('file_access_logs').insert(log_data).execute()
            logger.info(f"Logged file access: {action} for file {file_id} by user {user_id}")
        except Exception as e:
            logger.error(f"Error logging file access: {str(e)}")

# =============================================================================
# DATABASE HELPER FUNCTIONS
# =============================================================================

def check_database_connection():
    """Check if database connection is working"""
    try:
        result = supabase.table("users").select("count").execute()
        logger.info("Database connection verified")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False

def cleanup_expired_tokens():
    """Clean up expired password reset tokens"""
    try:
        current_time = datetime.utcnow().isoformat()
        
        result = supabase.table("password_resets").delete().lt("expires_at", current_time).execute()
        logger.info(f"Cleaned up expired password reset tokens")
        return result
    except Exception as e:
        logger.error(f"Error cleaning up expired tokens: {str(e)}")
        return None

def cleanup_old_login_attempts():
    """Clean up old login attempts (older than 24 hours)"""
    try:
        cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        
        result = supabase.table("login_attempts").delete().lt("attempt_time", cutoff_time).execute()
        logger.info("Cleaned up old login attempts")
        return result
    except Exception as e:
        logger.error(f"Error cleaning up old login attempts: {str(e)}")
        return None

def cleanup_old_access_logs():
    """Clean up old file access logs (older than 90 days)"""
    try:
        cutoff_time = (datetime.utcnow() - timedelta(days=90)).isoformat()
        
        result = supabase.table("file_access_logs").delete().lt("created_at", cutoff_time).execute()
        logger.info("Cleaned up old file access logs")
        return result
    except Exception as e:
        logger.error(f"Error cleaning up old access logs: {str(e)}")
        return None

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

# Initialize storage manager
storage_manager = StorageManager()

app = FastAPI(
    title="File Storage Management API",
    description="Complete file storage system with access control",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency to get current user ID from JWT token
    Note: This assumes you have an auth system that validates JWT tokens
    You'll need to implement token validation logic here
    """
    # Placeholder - implement actual JWT validation
    try:
        # In production, decode and validate JWT token here
        # For example, using PyJWT:
        # import jwt
        # decoded = jwt.decode(credentials.credentials, verify=True)
        # return decoded['user_id']
        return "user-123-456-789"  # Replace with actual JWT validation
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.post("/storage/create-bucket", response_model=dict)
async def create_bucket(request: BucketCreateRequest, current_user_id: str = Depends(get_current_user_id)):
    """Create a new storage bucket"""
    try:
        result = storage_manager.create_storage_bucket(request.bucket_name, request.public)
        
        if result:
            return {"message": f"Bucket '{request.bucket_name}' created successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create bucket"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bucket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/storage/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    bucket_name: str = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """Upload a file to storage"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Validate file size
        if len(file_content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum limit of {settings.MAX_FILE_SIZE} bytes"
            )
        
        # Validate file extension
        file_path = Path(file.filename)
        if file_path.suffix.lower() not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed extensions: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        # Upload file
        result = storage_manager.upload_file(
            current_user_id, 
            file_content, 
            file.filename, 
            bucket_name
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file"
            )
        
        return FileUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file upload"
        )

@app.get("/storage/download/{file_id}", response_model=dict)
async def download_file(file_id: str, current_user_id: str = Depends(get_current_user_id)):
    """Get download URL for a file"""
    try:
        download_url = storage_manager.fetch_file(current_user_id, file_id)
        
        if not download_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied"
            )
        
        return {"download_url": download_url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating download URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.delete("/storage/delete/{file_id}", response_model=dict)
async def delete_file(file_id: str, current_user_id: str = Depends(get_current_user_id)):
    """Delete a file"""
    try:
        result = storage_manager.delete_file(current_user_id, file_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="File not found or insufficient permissions"
            )
        
        return {"message": f"File {file_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file deletion"
        )

@app.post("/storage/grant-access/{file_id}", response_model=dict)
async def grant_file_access(
    file_id: str,
    request: AccessGrantRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """Grant access to a file for another user"""
    try:
        result = storage_manager.grant_access(
            current_user_id,
            file_id,
            request.target_user_id,
            request.access_level
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Failed to grant access: insufficient permissions or invalid request"
            )
        
        return {"message": f"Access granted to user {request.target_user_id} for file {file_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting access for file {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/storage/files", response_model=FileListResponse)
async def list_files(
    page: int = 1,
    per_page: int = 20,
    current_user_id: str = Depends(get_current_user_id)
):
    """List all files accessible to the user"""
    try:
        result = storage_manager.list_user_files(current_user_id, page, per_page)
        return FileListResponse(**result)
        
    except Exception as e:
        logger.error(f"Error listing files for user {current_user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/storage/file-info/{file_id}", response_model=dict)
async def get_file_info(file_id: str, current_user_id: str = Depends(get_current_user_id)):
    """Get detailed information about a specific file"""
    try:
        file_info = storage_manager.get_file_info(current_user_id, file_id)
        
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied"
            )
        
        return file_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info for {file_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
