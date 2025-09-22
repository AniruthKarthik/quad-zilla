import re
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from .db import supabase
from .config import settings
import logging

logger = logging.getLogger(__name__)

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