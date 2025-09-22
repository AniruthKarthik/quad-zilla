import json
import os
import re
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from supabase import create_client, Client
from pydantic import BaseModel, EmailStr, Field, validator
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

class Settings:
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Database Settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
    
    # Email Settings (for password reset)
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    EMAIL_USER: str = os.getenv("EMAIL_USER", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
    
    # Application Settings
    APP_NAME: str = "Enhanced Auth System"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Password Reset Settings
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", "1"))
    
    # Security Settings
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOCKOUT_DURATION_MINUTES: int = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))

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

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, description="Username (3-30 characters, letters, numbers, underscore only)")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, and underscores')
        if v.startswith('_') or v.endswith('_'):
            raise ValueError('Username cannot start or end with underscore')
        return v

class LoginRequest(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")

class ResetPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address for password reset")

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ValidationErrorResponse(BaseModel):
    valid: bool
    errors: list[str]

class MessageResponse(BaseModel):
    message: str

# =============================================================================
# AUTHENTICATION FUNCTIONS
# =============================================================================

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(password, hashed)

def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength
    Returns: dict with 'valid' boolean and 'errors' list
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number")
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character")
    
    return {"valid": len(errors) == 0, "errors": errors}

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_username(username: str) -> Dict[str, Any]:
    """
    Validate username
    Returns: dict with 'valid' boolean and 'errors' list
    """
    errors = []
    
    if len(username) < 3:
        errors.append("Username must be at least 3 characters long")
    
    if len(username) > 30:
        errors.append("Username must be no more than 30 characters long")
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        errors.append("Username can only contain letters, numbers, and underscores")
    
    if username.startswith('_') or username.endswith('_'):
        errors.append("Username cannot start or end with underscore")
    
    return {"valid": len(errors) == 0, "errors": errors}

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token verification failed: {str(e)}")
        return None

def register_user(username: str, email: str, password: str) -> Dict[str, Any]:
    """Register a new user with comprehensive validation"""
    try:
        # Validate input
        if not username or not email or not password:
            return {"error": "All fields are required"}
        
        # Validate email format
        if not validate_email(email):
            return {"error": "Invalid email format"}
        
        # Validate username
        username_validation = validate_username(username)
        if not username_validation["valid"]:
            return {"error": "; ".join(username_validation["errors"])}
        
        # Validate password strength
        password_validation = validate_password_strength(password)
        if not password_validation["valid"]:
            return {"error": "; ".join(password_validation["errors"])}
        
        # Check if username exists
        existing_username = supabase.table("users").select("id").eq("username", username).execute()
        if existing_username.data:
            return {"error": "Username already exists"}
        
        # Check if email exists
        existing_email = supabase.table("users").select("id").eq("email", email).execute()
        if existing_email.data:
            return {"error": "Email already exists"}
        
        # Hash password and create user
        hashed_password = hash_password(password)
        
        user_data = {
            "username": username,
            "email": email.lower(),
            "password_hash": hashed_password,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("users").insert(user_data).execute()
        
        if result.data:
            logger.info(f"User {username} registered successfully")
            return {"id": result.data[0]["id"], "message": "User registered successfully"}
        else:
            return {"error": "Failed to create user"}
            
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return {"error": "Registration failed due to server error"}

def authenticate_user(identifier: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate user with username or email and password
    Args:
        identifier: username or email
        password: plain text password
    Returns: user data if authentication successful, None otherwise
    """
    try:
        # Try to find user by username or email
        if validate_email(identifier):
            user_result = supabase.table("users").select("*").eq("email", identifier.lower()).single().execute()
        else:
            user_result = supabase.table("users").select("*").eq("username", identifier).single().execute()
        
        if not user_result.data:
            logger.warning(f"User not found: {identifier}")
            return None
        
        user = user_result.data
        
        # Check if user is active
        if not user.get("is_active", True):
            logger.warning(f"Inactive user login attempt: {identifier}")
            return None
        
        # Verify password
        if verify_password(password, user["password_hash"]):
            # Update last login
            supabase.table("users").update({
                "last_login": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", user["id"]).execute()
            
            return user
        
        logger.warning(f"Invalid password for user: {identifier}")
        return None
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return None

def get_current_user(token: str) -> Optional[Dict[str, Any]]:
    """Get current user from JWT token"""
    try:
        payload = verify_token(token)
        if payload is None:
            return None
        
        user_id = payload.get("sub")
        if user_id is None:
            return None
        
        user_result = supabase.table("users").select("*").eq("id", user_id).single().execute()
        
        if not user_result.data:
            return None
        
        user = user_result.data
        
        # Check if user is still active
        if not user.get("is_active", True):
            return None
        
        return user
        
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        return None

def change_user_password(user_id: str, current_password: str, new_password: str) -> Dict[str, Any]:
    """Change user password"""
    try:
        # Get user
        user_result = supabase.table("users").select("password_hash").eq("id", user_id).single().execute()
        
        if not user_result.data:
            return {"error": "User not found"}
        
        # Verify current password
        if not verify_password(current_password, user_result.data["password_hash"]):
            return {"error": "Current password is incorrect"}
        
        # Validate new password
        password_validation = validate_password_strength(new_password)
        if not password_validation["valid"]:
            return {"error": "; ".join(password_validation["errors"])}
        
        # Hash new password and update
        new_hashed_password = hash_password(new_password)
        
        result = supabase.table("users").update({
            "password_hash": new_hashed_password,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
        if result.data:
            return {"message": "Password changed successfully"}
        else:
            return {"error": "Failed to update password"}
            
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        return {"error": "Password change failed"}

def generate_reset_token() -> str:
    """Generate secure reset token"""
    return secrets.token_urlsafe(32)

def initiate_password_reset(email: str) -> Dict[str, Any]:
    """Initiate password reset process"""
    try:
        # Find user by email
        user_result = supabase.table("users").select("id, email, username").eq("email", email.lower()).single().execute()
        
        if not user_result.data:
            # Don't reveal if email exists
            logger.warning(f"Password reset attempted for non-existent email: {email}")
            return {"message": "Reset email sent if account exists"}
        
        user = user_result.data
        
        # Generate reset token
        reset_token = generate_reset_token()
        reset_token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
        expires_at = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
        
        # Store reset token
        supabase.table("password_resets").insert({
            "user_id": user["id"],
            "token_hash": reset_token_hash,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        
        # Here you would typically send an email with the reset link
        # For now, we'll just log it (remove in production)
        logger.info(f"Password reset token for {email}: {reset_token}")
        
        return {"message": "Reset email sent", "token": reset_token}  # Remove token from response in production
        
    except Exception as e:
        logger.error(f"Password reset initiation error: {str(e)}")
        return {"error": "Password reset failed"}

def reset_password_with_token(token: str, new_password: str) -> Dict[str, Any]:
    """Reset password using reset token"""
    try:
        # Validate new password
        password_validation = validate_password_strength(new_password)
        if not password_validation["valid"]:
            return {"error": "; ".join(password_validation["errors"])}
        
        # Hash the token to compare with stored hash
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Find valid reset token
        reset_result = supabase.table("password_resets").select("*").eq("token_hash", token_hash).gte("expires_at", datetime.utcnow().isoformat()).single().execute()
        
        if not reset_result.data:
            return {"error": "Invalid or expired reset token"}
        
        reset_record = reset_result.data
        user_id = reset_record["user_id"]
        
        # Hash new password and update user
        new_hashed_password = hash_password(new_password)
        
        result = supabase.table("users").update({
            "password_hash": new_hashed_password,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
        if result.data:
            # Delete used reset token
            supabase.table("password_resets").delete().eq("id", reset_record["id"]).execute()
            return {"message": "Password reset successfully"}
        else:
            return {"error": "Failed to reset password"}
            
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        return {"error": "Password reset failed"}

def deactivate_user(user_id: str) -> Dict[str, Any]:
    """Deactivate user account"""
    try:
        result = supabase.table("users").update({
            "is_active": False,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
        if result.data:
            return {"message": "Account deactivated successfully"}
        else:
            return {"error": "Failed to deactivate account"}
            
    except Exception as e:
        logger.error(f"Account deactivation error: {str(e)}")
        return {"error": "Account deactivation failed"}

def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user profile by ID"""
    try:
        user_result = supabase.table("users").select("id, username, email, is_active, created_at, updated_at, last_login").eq("id", user_id).single().execute()
        
        if user_result.data:
            return user_result.data
        else:
            return None
            
    except Exception as e:
        logger.error(f"Get user profile error: {str(e)}")
        return None

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="Enhanced Authentication API",
    description="A comprehensive authentication system with JWT tokens",
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

async def get_current_user_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current user from JWT token"""
    user = get_current_user(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or user not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.post("/auth/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    """Register a new user"""
    try:
        result = register_user(req.username, req.email, req.password)
        if "error" in result:
            if "already exists" in result["error"].lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=result["error"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result["error"]
                )
        
        logger.info(f"User {req.username} registered successfully")
        return {
            "message": "User registered successfully",
            "user_id": result["id"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )

@app.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Authenticate user and return JWT token"""
    try:
        user = authenticate_user(req.username, req.password)
        if not user:
            logger.warning(f"Failed login attempt for username: {req.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        access_token = create_access_token(data={"sub": str(user["id"])})
        logger.info(f"User {user['username']} logged in successfully")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                is_active=user.get("is_active", True),
                created_at=user.get("created_at")
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user_dependency)):
    """Get current user profile"""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        is_active=current_user.get("is_active", True),
        created_at=current_user.get("created_at")
    )

@app.post("/auth/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user_dependency)
):
    """Change user password"""
    try:
        result = change_user_password(
            current_user["id"],
            req.current_password,
            req.new_password
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        logger.info(f"Password changed for user {current_user['username']}")
        return {"message": "Password changed successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during password change"
        )

@app.post("/auth/forgot-password")
async def forgot_password(req: ResetPasswordRequest):
    """Initiate password reset process"""
    try:
        result = initiate_password_reset(req.email)
        # Always return success to prevent email enumeration
        return {"message": "If the email exists, a reset link has been sent"}
    
    except Exception as e:
        logger.error(f"Password reset initiation error: {str(e)}")
        return {"message": "If the email exists, a reset link has been sent"}

@app.post("/auth/reset-password/{token}")
async def reset_password(token: str, new_password: str):
    """Reset password using token"""
    try:
        result = reset_password_with_token(token, new_password)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return {"message": "Password reset successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during password reset"
        )

@app.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_user_dependency)):
    """Logout user (client should discard token)"""
    logger.info(f"User {current_user['username']} logged out")
    return {"message": "Logged out successfully"}

@app.delete("/auth/deactivate")
async def deactivate_account(current_user: dict = Depends(get_current_user_dependency)):
    """Deactivate user account"""
    try:
        result = deactivate_user(current_user["id"])
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        logger.info(f"Account deactivated for user {current_user['username']}")
        return {"message": "Account deactivated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account deactivation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during account deactivation"
        )

@app.get("/auth/validate-token")
async def validate_token(current_user: dict = Depends(get_current_user_dependency)):
    """Validate JWT token"""
    return {"valid": True, "user_id": current_user["id"]}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# =============================================================================
# DATABASE SETUP HELPER FUNCTIONS
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
    
    try:
        # Note: In production, you should run these via Supabase SQL editor
        # or use proper migration tools. This is for development/testing only.
        logger.info("Database tables schema defined. Run via Supabase SQL editor.")
        return {
            "users_table": users_table_sql,
            "password_resets_table": password_resets_table_sql,
        }
    except Exception as e:
        logger.error(f"Error with database schema: {str(e)}")
        raise

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

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("login:app", host="0.0.0.0", port=8000, reload=True)