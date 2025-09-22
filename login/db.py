from supabase import create_client, Client
from .config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase client
try:
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    logger.info("Successfully connected to Supabase")
except Exception as e:
    logger.error(f"Failed to connect to Supabase: {str(e)}")
    raise

# Database schema setup (run this once to create tables)
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
    
    # Password resets table schema
    password_resets_table_sql = """
    CREATE TABLE IF NOT EXISTS password_resets (
        id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        token_hash TEXT NOT NULL,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        used_at TIMESTAMP WITH TIME ZONE
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_password_resets_token ON password_resets(token_hash);
    CREATE INDEX IF NOT EXISTS idx_password_resets_user ON password_resets(user_id);
    CREATE INDEX IF NOT EXISTS idx_password_resets_expires ON password_resets(expires_at);
    """
    
    # Login attempts table for rate limiting (optional)
    login_attempts_table_sql = """
    CREATE TABLE IF NOT EXISTS login_attempts (
        id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
        identifier VARCHAR(255) NOT NULL,  -- username or email
        ip_address INET,
        attempt_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        success BOOLEAN NOT NULL
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_login_attempts_identifier ON login_attempts(identifier);
    CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip_address);
    CREATE INDEX IF NOT EXISTS idx_login_attempts_time ON login_attempts(attempt_time);
    """
    
    # User sessions table for token blacklisting (optional)
    user_sessions_table_sql = """
    CREATE TABLE IF NOT EXISTS user_sessions (
        id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        token_hash TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        revoked_at TIMESTAMP WITH TIME ZONE
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);
    CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token_hash);
    CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);
    """
    
    try:
        # Note: In production, you should run these via Supabase SQL editor
        # or use proper migration tools. This is for development/testing only.
        logger.info("Database tables schema defined. Run via Supabase SQL editor.")
        return {
            "users_table": users_table_sql,
            "password_resets_table": password_resets_table_sql,
            "login_attempts_table": login_attempts_table_sql,
            "user_sessions_table": user_sessions_table_sql
        }
    except Exception as e:
        logger.error(f"Error with database schema: {str(e)}")
        raise

# Helper functions for database operations
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
        from datetime import datetime
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
        from datetime import datetime, timedelta
        cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        
        result = supabase.table("login_attempts").delete().lt("attempt_time", cutoff_time).execute()
        logger.info("Cleaned up old login attempts")
        return result
    except Exception as e:
        logger.error(f"Error cleaning up old login attempts: {str(e)}")
        return None