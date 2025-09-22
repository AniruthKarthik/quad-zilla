# storage.py

"""
Supabase Storage and PostgreSQL Access Control Manager
Provides file upload, download, deletion, and permission management functionality.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

# -------------------------
# Setup & Configuration
# -------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class Settings:
    SUPABASE_URL = os.getenv("SUPABASE_URL", "YOUR_SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "YOUR_SUPABASE_KEY")

settings = Settings()

# Initialize Supabase client
try:
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    logger.info("Successfully connected to Supabase")
except Exception as e:
    logger.error(f"Failed to connect to Supabase: {str(e)}")
    raise

# -------------------------
# Database schema setup (for reference)
# -------------------------
def create_tables():
    """Return SQL statements for tables (run once in Supabase SQL editor)."""
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
    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
    """
    password_resets_table_sql = """
    CREATE TABLE IF NOT EXISTS password_resets (
        id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        token_hash TEXT NOT NULL,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        used_at TIMESTAMP WITH TIME ZONE
    );
    CREATE INDEX IF NOT EXISTS idx_password_resets_token ON password_resets(token_hash);
    CREATE INDEX IF NOT EXISTS idx_password_resets_user ON password_resets(user_id);
    CREATE INDEX IF NOT EXISTS idx_password_resets_expires ON password_resets(expires_at);
    """
    login_attempts_table_sql = """
    CREATE TABLE IF NOT EXISTS login_attempts (
        id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
        identifier VARCHAR(255) NOT NULL,
        ip_address INET,
        attempt_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        success BOOLEAN NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_login_attempts_identifier ON login_attempts(identifier);
    CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip_address);
    CREATE INDEX IF NOT EXISTS idx_login_attempts_time ON login_attempts(attempt_time);
    """
    user_sessions_table_sql = """
    CREATE TABLE IF NOT EXISTS user_sessions (
        id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        token_hash TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        revoked_at TIMESTAMP WITH TIME ZONE
    );
    CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);
    CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token_hash);
    CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);
    """
    return {
        "users_table": users_table_sql,
        "password_resets_table": password_resets_table_sql,
        "login_attempts_table": login_attempts_table_sql,
        "user_sessions_table": user_sessions_table_sql,
    }

def check_database_connection():
    """Check if database connection is working."""
    try:
        supabase.table("users").select("count").execute()
        logger.info("Database connection verified")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False

def cleanup_expired_tokens():
    """Delete expired password reset tokens."""
    try:
        current_time = datetime.utcnow().isoformat()
        result = supabase.table("password_resets").delete().lt("expires_at", current_time).execute()
        logger.info("Cleaned up expired password reset tokens")
        return result
    except Exception as e:
        logger.error(f"Error cleaning expired tokens: {str(e)}")
        return None

def cleanup_old_login_attempts():
    """Delete login attempts older than 24h."""
    try:
        cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        result = supabase.table("login_attempts").delete().lt("attempt_time", cutoff_time).execute()
        logger.info("Cleaned up old login attempts")
        return result
    except Exception as e:
        logger.error(f"Error cleaning login attempts: {str(e)}")
        return None

# -------------------------
# Storage Manager
# -------------------------
class StorageManager:
    def __init__(self):
        self.supabase = supabase

    def create_storage_bucket(self, bucket_name: str, public: bool = False) -> bool:
        try:
            buckets = self.supabase.storage.list_buckets()
            existing = [b.name for b in buckets]
            if bucket_name in existing:
                logger.info(f"Bucket '{bucket_name}' already exists")
                return True
            self.supabase.storage.create_bucket(bucket_name, {"public": public})
            logger.info(f"Created bucket '{bucket_name}'")
            return True
        except Exception as e:
            logger.error(f"Error creating bucket {bucket_name}: {str(e)}")
            return False

    def upload_file(self, user_id: str, local_path: str, bucket: str, remote_filename: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            if not os.path.exists(local_path):
                logger.error(f"File does not exist: {local_path}")
                return None
            file_path = Path(local_path)
            filename = remote_filename or file_path.name
            file_size = file_path.stat().st_size
            content_type = self._get_content_type(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            storage_path = f"{user_id}/{timestamp}_{filename}"
            with open(local_path, "rb") as f:
                self.supabase.storage.from_(bucket).upload(storage_path, f, file_options={"content-type": content_type})
            file_data = {
                "user_id": user_id,
                "filename": filename,
                "filepath": storage_path,
                "file_size": file_size,
                "content_type": content_type,
            }
            db_result = self.supabase.table("files").insert(file_data).execute()
            if not db_result.data:
                return None
            file_record = db_result.data[0]
            perm_data = {"file_id": file_record["id"], "user_id": user_id, "access_level": "owner", "granted_by": user_id}
            self.supabase.table("file_permissions").insert(perm_data).execute()
            logger.info(f"Uploaded file '{filename}' with ID {file_record['id']}")
            return file_record
        except Exception as e:
            logger.error(f"Error uploading file {local_path}: {str(e)}")
            return None

    def fetch_file(self, user_id: str, file_id: str, bucket: str) -> Optional[str]:
        try:
            access = self.check_access(user_id, file_id)
            if not access:
                return None
            result = self.supabase.table("files").select("*").eq("id", file_id).execute()
            if not result.data:
                return None
            filepath = result.data[0]["filepath"]
            signed_url = self.supabase.storage.from_(bucket).create_signed_url(filepath, 3600)
            return signed_url["signedURL"]
        except Exception as e:
            logger.error(f"Error fetching file {file_id}: {str(e)}")
            return None

    def delete_file(self, user_id: str, file_id: str, bucket: str) -> bool:
        try:
            if self.check_access(user_id, file_id) != "owner":
                return False
            result = self.supabase.table("files").select("*").eq("id", file_id).execute()
            if not result.data:
                return False
            filepath = result.data[0]["filepath"]
            self.supabase.storage.from_(bucket).remove([filepath])
            self.supabase.table("file_permissions").delete().eq("file_id", file_id).execute()
            self.supabase.table("files").delete().eq("id", file_id).execute()
            logger.info(f"Deleted file {file_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            return False

    def check_access(self, user_id: str, file_id: str) -> Optional[str]:
        try:
            result = self.supabase.table("file_permissions").select("access_level").eq("user_id", user_id).eq("file_id", file_id).execute()
            if result.data:
                return result.data[0]["access_level"]
            return None
        except Exception as e:
            logger.error(f"Error checking access for {user_id}/{file_id}: {str(e)}")
            return None

    def grant_access(self, owner_id: str, file_id: str, target_id: str, access_level: str) -> bool:
        try:
            if self.check_access(owner_id, file_id) != "owner":
                return False
            if access_level not in ["read", "write"]:
                return False
            perm_data = {"file_id": file_id, "user_id": target_id, "access_level": access_level, "granted_by": owner_id}
            self.supabase.table("file_permissions").upsert(perm_data).execute()
            return True
        except Exception as e:
            logger.error(f"Error granting access: {str(e)}")
            return False

    def list_user_files(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            result = self.supabase.table("files").select(
                "id, filename, file_size, content_type, created_at, file_permissions!inner(access_level)"
            ).eq("file_permissions.user_id", user_id).execute()
            files = []
            for f in result.data:
                files.append({
                    "id": f["id"],
                    "filename": f["filename"],
                    "file_size": f["file_size"],
                    "content_type": f["content_type"],
                    "created_at": f["created_at"],
                    "access_level": f["file_permissions"][0]["access_level"],
                })
            return files
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []

    def _get_content_type(self, filename: str) -> str:
        ext = Path(filename).suffix.lower()
        return {
            ".txt": "text/plain",
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }.get(ext, "application/octet-stream")

